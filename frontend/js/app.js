/**
 * Rally Safety App - Main Application Controller
 * Coordinates all app functionality after login
 */

const App = {
    user: null,
    messageCount: 0,
    activeCommsTab: 'chat',
    reauthScheduled: false,
    stateStorageLimits: {
        chat: 180,
        info: 140,
        incidents: 40,
    },
    persistedState: {
        chat: [],
        info: [],
        incidents: [],
    },
    knownUsers: new Set(),
    knownStations: new Set(),
    tagSuggestion: {
        active: false,
        type: null,
        query: '',
        start: -1,
        end: -1,
        selectedIndex: 0,
        candidates: [],
    },
    incidentGateActive: false,
    gateMissingStations: [],
    gateRefreshTimer: null,
    gateRefreshQueued: false,
    rzState: 'running',
    rzName: 'Nezadaná RZ',
    communicationResetVersion: 0,
    adminStations: [],
    adminPeople: [],
    selectedAdminStationId: null,
    currentScreen: 'dashboard',
    lastOfflineStations: [],

    /**
     * Initialize application
     */
    init() {
        console.log('Initializing app...');
        
        // Get current user
        this.user = window.Auth.getCurrentUser();
        if (!this.user) {
            console.error('No user found - redirecting to login');
            window.location.reload();
            return;
        }

        // Setup UI based on role
        this.setupUI();
        this.rzName = this.user.rz_name || this.rzName;
        this.applyRzName(this.rzName);

        this.loadPersistedState();
        this.restorePersistedUiState();
        this.loadRzState();
        this.applyRzStateUi();
        this.refreshRzContext().catch((error) => {
            console.error('RZ context refresh failed:', error);
        });

        if (window.SetupAdminModule?.applyStoredMapConfig) {
            window.SetupAdminModule.applyStoredMapConfig(this);
        }

        this.startGateStatusRefresh();

        this.knownUsers.add(this.user.name);
        if (this.user.station_id) {
            this.knownStations.add(this.user.station_id);
        }
        
        // Connect WebSocket
        this.connectWebSocket();
        
        // Setup event listeners
        this.setupEventListeners();

        this.initializeMapModule();
        
        console.log('App initialized for user:', this.user.name);
    },

    /**
     * Initialize map module after app layout is painted.
     * A deferred start avoids race conditions right after screen switch.
     */
    initializeMapModule() {
        if (!window.MapModule || typeof window.MapModule.init !== 'function') {
            return;
        }

        requestAnimationFrame(() => {
            window.MapModule.init()
                .then(() => {
                    if (!window.MapModule.isInitialized) {
                        return window.MapModule.init();
                    }
                    return null;
                })
                .catch((error) => {
                    console.error('Map initialization failed:', error);
                });
        });
    },

    /**
     * Setup UI based on user role
     */
    setupUI() {
        // Update header
        document.getElementById('user-name').textContent = this.user.name;
        
        const roleBadge = document.getElementById('user-role-badge');
        roleBadge.textContent = this.getRoleLabel(this.user.role);
        
        // Show/hide admin panel (only for vedeni roles)
        const isVedeni = this.user.role === 'vedouci' || this.user.role === 'zastupce';
        const adminPanel = document.getElementById('admin-panel');
        const quickActions = document.getElementById('quick-actions');
        const appScreen = document.getElementById('app-screen');

        if (appScreen) {
            appScreen.classList.remove('role-vedeni', 'role-komisar');
            appScreen.classList.add(isVedeni ? 'role-vedeni' : 'role-komisar');
        }
        
        if (isVedeni) {
            adminPanel.classList.remove('hidden');
            quickActions.classList.add('hidden');
            const setupButton = document.getElementById('open-setup-btn');
            if (setupButton) {
                setupButton.classList.remove('hidden');
            }

            const panelHeader = adminPanel.querySelector('.panel-header');
            const panelContent = adminPanel.querySelector('.panel-content');
            if (panelHeader) {
                panelHeader.classList.remove('collapsed');
            }
            if (panelContent) {
                panelContent.style.display = '';
            }
        } else {
            adminPanel.classList.add('hidden');
            quickActions.classList.remove('hidden');
            const setupButton = document.getElementById('open-setup-btn');
            if (setupButton) {
                setupButton.classList.add('hidden');
            }
        }

        this.updateVedeniContact();
        this.updateKomisarStationLabel();
    },

    /**
     * Update quick-action label with current komisař station.
     */
    updateKomisarStationLabel() {
        const label = document.getElementById('komisar-station-label');
        if (!label) {
            return;
        }

        const stationId = String(this.user?.station_id || '').trim();
        label.textContent = stationId || 'Neurčeno';
    },

    /**
     * Apply RZ name in header and browser title.
     * @param {string} rzName
     */
    applyRzName(rzName) {
        const normalized = String(rzName || '').trim() || 'Nezadaná RZ';
        this.rzName = normalized;

        const badge = document.getElementById('rz-name-display');
        if (badge) {
            badge.textContent = `RZ: ${normalized}`;
        }

        document.title = `Rally Safety - ${normalized}`;

        if (this.user) {
            this.user.rz_name = normalized;
            window.Auth.saveUser(this.user);
        }
    },

    /**
     * Fetch latest RZ context from backend and apply it locally.
     * @returns {Promise<void>}
     */
    async refreshRzContext() {
        const response = await fetch('http://localhost:8000/api/stations/rz-context');
        if (!response.ok) {
            return;
        }

        const payload = await response.json();
        this.applyRzName(payload.rz_name || this.rzName);
        this.applyCommunicationResetVersion(payload.communication_reset_version || 0, false);
    },

    /**
     * Apply global communication reset version and clear persisted history when it changes.
     * @param {number} version
     * @param {boolean} announce
     */
    applyCommunicationResetVersion(version, announce = true) {
        const incoming = Number(version || 0);
        if (!Number.isFinite(incoming) || incoming < 0) {
            return;
        }

        const key = 'rally_comm_reset_version';
        const stored = Number(localStorage.getItem(key) || 0);

        if (incoming > stored) {
            this.clearPersistedCommunicationHistory();
            if (announce) {
                this.showToast('Historie komunikace byla resetována pro novou RZ', 'info');
            }
        }

        localStorage.setItem(key, String(Math.max(stored, incoming)));
        this.communicationResetVersion = Math.max(stored, incoming);
    },

    /**
     * Clear all locally persisted communication history and reset UI feeds.
     */
    clearPersistedCommunicationHistory() {
        Object.keys(localStorage).forEach((storageKey) => {
            if (storageKey.startsWith('rally_state_')) {
                localStorage.removeItem(storageKey);
            }
        });

        this.persistedState.chat = [];
        this.persistedState.info = [];
        this.persistedState.incidents = [];
        this.lastOfflineStations = [];

        const messages = document.getElementById('messages');
        if (messages) {
            messages.innerHTML = '<div class="welcome-message"><p>Připraveno k příjmu zpráv...</p></div>';
        }

        const infoFeed = document.getElementById('info-feed');
        if (infoFeed) {
            infoFeed.innerHTML = '<div class="welcome-message"><p>Zatím žádná systémová nebo incident zpráva.</p></div>';
        }

        const incidentFeed = document.getElementById('incident-feed');
        if (incidentFeed) {
            incidentFeed.innerHTML = '<p class="incident-empty">Zatím žádný aktivní incident.</p>';
        }
    },

    /**
     * Get user-friendly role label
     * @param {string} role
     * @returns {string}
     */
    getRoleLabel(role) {
        const labels = {
            'vedouci': 'Vedoucí',
            'zastupce': 'Zástupce',
            'komisar_trat': 'Komisař tratě',
            'casomer': 'Časomíra',
            'parkovani': 'Parkování',
            'zdravotnik': 'Zdravotník',
            'start': 'Start',
            'cil': 'Cíl',
            'bezpecnost': 'Bezpečnost',
        };
        return labels[role] || role;
    },

    /**
     * Connect to WebSocket server
     */
    connectWebSocket() {
        const authIdentifier = window.Auth.getAuthIdentifier();
        
        if (!authIdentifier) {
            console.error('No auth identifier - cannot connect WebSocket');
            this.showToast('Chyba připojení', 'error');
            return;
        }

        // Register event handlers
        window.wsClient.on('onMessage', (message) => this.handleMessage(message));
        window.wsClient.on('onStatusChange', (status) => window.AppUiCommonModule.handleStatusChange(this, status));
        window.wsClient.on('onError', (error) => window.AppUiCommonModule.handleError(this, error));
        
        // Connect
        window.wsClient.connect(authIdentifier);
    },

    /**
     * Setup event listeners for UI elements
     */
    setupEventListeners() {
        this.bindCoreEventListeners();
        this.bindSetupAdminEventListeners();
        this.bindMessageAndTagEventListeners();
        this.bindStationStatusEventListeners();
    },

    /**
     * Bind shared dashboard/header controls.
     */
    bindCoreEventListeners() {
        // Message form
        document.getElementById('message-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendChatMessage();
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });

        const openCommsBtn = document.getElementById('open-comms-btn');
        if (openCommsBtn) {
            openCommsBtn.addEventListener('click', () => window.AppMessagingModule.openCommsPanel());
        }

        const openSetupBtn = document.getElementById('open-setup-btn');
        if (openSetupBtn) {
            openSetupBtn.addEventListener('click', () => {
                window.SetupAdminModule.openSetupScreen(this);
            });
        }

        const backToDashboardBtn = document.getElementById('back-to-dashboard-btn');
        if (backToDashboardBtn) {
            backToDashboardBtn.addEventListener('click', () => {
                window.SetupAdminModule.openDashboardScreen(this);
            });
        }

        const closeCommsBtn = document.getElementById('close-comms-btn');
        if (closeCommsBtn) {
            closeCommsBtn.addEventListener('click', () => window.AppMessagingModule.closeCommsPanel());
        }

        const commsOverlay = document.getElementById('comms-overlay');
        if (commsOverlay) {
            commsOverlay.addEventListener('click', () => window.AppMessagingModule.closeCommsPanel());
        }

        document.querySelectorAll('.comms-tab').forEach((tabBtn) => {
            tabBtn.addEventListener('click', () => {
                window.AppMessagingModule.switchCommsTab(this, tabBtn.dataset.tab || 'chat');
            });
        });

        // Admin panel collapse
        const panelHeader = document.querySelector('.panel-header');
        if (panelHeader) {
            panelHeader.addEventListener('click', () => {
                this.toggleAdminPanel();
            });
        }

        // Broadcast button
        const broadcastBtn = document.getElementById('btn-broadcast');
        if (broadcastBtn) {
            broadcastBtn.addEventListener('click', () => {
                this.sendBroadcast();
            });
        }

        document.querySelectorAll('.btn-alert').forEach((btn) => {
            btn.addEventListener('click', () => {
                this.sendAlertPreset(btn.dataset.alert).catch((error) => {
                    console.error('Alert preset failed:', error);
                    this.showToast('Operační hlášení se nepodařilo odeslat', 'error');
                });
            });
        });

        const setupLogoutBtn = document.getElementById('logout-setup-btn');
        if (setupLogoutBtn) {
            setupLogoutBtn.addEventListener('click', () => {
                this.handleLogout();
            });
        }

        // Quick action buttons
        document.querySelectorAll('.btn-quick').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.handleQuickAction(action);
            });
        });
    },

    /**
     * Bind setup/admin screen controls.
     */
    bindSetupAdminEventListeners() {

        const refreshStationsBtn = document.getElementById('btn-refresh-stations');
        if (refreshStationsBtn) {
            refreshStationsBtn.addEventListener('click', () => {
                window.SetupAdminModule.loadAdminStations(this, true).catch((error) => {
                    console.error('Admin station refresh failed:', error);
                    this.showToast('Seznam pozic se nepodařilo obnovit', 'error');
                });
            });
        }

        const bulkGeneratePinsBtn = document.getElementById('btn-bulk-generate-pins');
        if (bulkGeneratePinsBtn) {
            bulkGeneratePinsBtn.addEventListener('click', () => {
                window.SetupAdminModule.bulkGeneratePinsFromMap(this).catch((error) => {
                    console.error('Bulk PIN generation failed:', error);
                    this.showToast('Hromadné generování PINů selhalo', 'error');
                });
            });
        }

        const refreshPeopleBtn = document.getElementById('btn-refresh-people');
        if (refreshPeopleBtn) {
            refreshPeopleBtn.addEventListener('click', () => {
                window.SetupAdminModule.loadAdminPeople(this, true).catch((error) => {
                    console.error('Admin people refresh failed:', error);
                    this.showToast('Katalog osob se nepodařilo načíst', 'error');
                });
            });
        }

        const peopleSelect = document.getElementById('admin-person-catalog');
        if (peopleSelect) {
            peopleSelect.addEventListener('change', () => {
                window.SetupAdminModule.applySelectedCatalogPerson(this);
            });
        }

        const stationForm = document.getElementById('station-admin-form');
        if (stationForm) {
            stationForm.addEventListener('submit', (event) => {
                event.preventDefault();
                window.SetupAdminModule.submitAdminStationAssignment(this);
            });
        }

        const releaseBtn = document.getElementById('btn-release-station');
        if (releaseBtn) {
            releaseBtn.addEventListener('click', () => {
                window.SetupAdminModule.releaseAdminStation(this);
            });
        }

        const regeneratePinBtn = document.getElementById('btn-regenerate-station-pin');
        if (regeneratePinBtn) {
            regeneratePinBtn.addEventListener('click', () => {
                window.SetupAdminModule.regenerateSelectedStationPin(this).catch((error) => {
                    console.error('Station PIN regeneration failed:', error);
                    this.showToast('Regenerace PINu selhala', 'error');
                });
            });
        }

        const closeBulkSummaryBtn = document.getElementById('btn-close-pin-bulk-summary');
        if (closeBulkSummaryBtn) {
            closeBulkSummaryBtn.addEventListener('click', () => {
                window.SetupAdminModule.hideBulkPinSummaryModal();
            });
        }

        const bulkSummaryModal = document.getElementById('pin-bulk-summary-modal');
        if (bulkSummaryModal) {
            bulkSummaryModal.addEventListener('click', (event) => {
                if (event.target === bulkSummaryModal) {
                    window.SetupAdminModule.hideBulkPinSummaryModal();
                }
            });
        }

        const applyTrackBtn = document.getElementById('btn-map-track-apply');
        if (applyTrackBtn) {
            applyTrackBtn.addEventListener('click', () => {
                window.SetupAdminModule.applySetupTrackSource(this).catch((error) => {
                    console.error('Track source apply failed:', error);
                    this.showToast('Podklad trati se nepodařilo použít', 'error');
                });
            });
        }

        const saveRzNameBtn = document.getElementById('btn-save-rz-name');
        if (saveRzNameBtn) {
            saveRzNameBtn.addEventListener('click', () => {
                window.SetupAdminModule.saveRzConfig(this).catch((error) => {
                    console.error('RZ config save failed:', error);
                    this.showToast('Název RZ se nepodařilo uložit', 'error');
                });
            });
        }

        const resetHistoryBtn = document.getElementById('btn-reset-communication-history');
        if (resetHistoryBtn) {
            resetHistoryBtn.addEventListener('click', () => {
                window.SetupAdminModule.resetCommunicationHistory(this).catch((error) => {
                    console.error('Communication reset failed:', error);
                    this.showToast('Reset komunikace selhal', 'error');
                });
            });
        }

        const loadCoordsBtn = document.getElementById('btn-map-station-load');
        if (loadCoordsBtn) {
            loadCoordsBtn.addEventListener('click', () => {
                window.SetupAdminModule.loadSelectedSetupStationCoordinate(this);
            });
        }

        const saveCoordsBtn = document.getElementById('btn-map-station-save');
        if (saveCoordsBtn) {
            saveCoordsBtn.addEventListener('click', () => {
                window.SetupAdminModule.saveSelectedSetupStationCoordinate(this).catch((error) => {
                    console.error('Station coordinate save failed:', error);
                    this.showToast('Souřadnice se nepodařilo uložit', 'error');
                });
            });
        }

        const resetMapConfigBtn = document.getElementById('btn-map-config-reset');
        if (resetMapConfigBtn) {
            resetMapConfigBtn.addEventListener('click', () => {
                window.SetupAdminModule.resetSetupMapConfig(this).catch((error) => {
                    console.error('Map config reset failed:', error);
                    this.showToast('Reset map config se nepodařil', 'error');
                });
            });
        }
    },

    /**
     * Bind message list, tagging and input handlers.
     */
    bindMessageAndTagEventListeners() {
        const messages = document.getElementById('messages');
        if (messages) {
            messages.addEventListener('click', (event) => this.handleTagClick(event));
        }

        const infoFeed = document.getElementById('info-feed');
        if (infoFeed) {
            infoFeed.addEventListener('click', (event) => this.handleTagClick(event));
        }

        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('input', (event) => this.onMessageInputChanged(event));
            messageInput.addEventListener('keydown', (event) => this.onMessageInputKeyDown(event));
            messageInput.addEventListener('blur', () => {
                setTimeout(() => this.hideTagSuggestions(), 120);
            });
        }
    },

    /**
     * Bind station status update events from map/status modules.
     */
    bindStationStatusEventListeners() {
        window.addEventListener('stations:update', (event) => {
            const stations = event.detail?.stations || [];
            this.lastOfflineStations = stations
                .filter((station) => station && station.online === false)
                .map((station) => station.station_id)
                .filter(Boolean);
            this.updateStationTags(stations);
        });

        window.addEventListener('stations:went-offline', (event) => {
            this.handleStationsWentOffline(event.detail?.stations || []);
        });
    },

    /**
     * Send chat message
     */
    sendChatMessage() {
        return window.AppMessagingModule.sendChatMessage(this);
    },

    /**
     * Handle incoming WebSocket message
     * @param {Object} message
     */
    handleMessage(message) {
        return window.AppMessagingModule.handleMessage(this, message);
    },

    /**
     * Update map station alert visuals based on incoming message semantics.
     * @param {Object} message
     */
    applyMarkerAlertFromMessage(message) {
        return window.AppMessagingModule.applyMarkerAlertFromMessage(message);
    },

    /**
     * Normalize raw incoming message payloads to common shape.
     * @param {Object} message
     * @returns {Object|null}
     */
    normalizeIncomingMessage(message) {
        return window.AppMessagingModule.normalizeIncomingMessage(message);
    },

    /**
     * Display message in chat area
     * @param {Object} message
     */
    displayMessage(message, persist = true) {
        return window.AppMessagingModule.displayMessage(this, message, persist);
    },

    /**
     * Determine whether message belongs in info channel.
     * @param {Object} message
     * @returns {boolean}
     */
    isInfoChannelMessage(message) {
        return window.AppMessagingModule.isInfoChannelMessage(message);
    },

    /**
     * Display message in dedicated info feed.
     * @param {Object} message
     */
    displayInfoMessage(message, persist = true) {
        return window.AppMessagingModule.displayInfoMessage(this, message, persist);
    },

    /**
     * Redirect to login after communication/auth failures.
     * @param {string} reason
     */
    scheduleReauthentication(reason) {
        return window.AppUiCommonModule.scheduleReauthentication(this, reason);
    },

    /**
     * Toggle admin panel collapse
     */
    toggleAdminPanel() {
        return window.AppOperationsRzModule.toggleAdminPanel();
    },

    /**
     * Send broadcast message (admin only)
     */
    async sendBroadcast() {
        return window.AppOperationsIncidentsModule.sendBroadcast(this);
    },

    /**
     * Send predefined operational alert from vedeni panel.
     * @param {string} alertKey
     */
    sendAlertPreset(alertKey) {
        return window.AppOperationsIncidentsModule.sendAlertPreset(this, alertKey);
    },

    /**
     * Storage key for persistent RZ state in local browser.
     * @returns {string}
     */
    getRzStateStorageKey() {
        return window.AppUiCommonModule.getRzStateStorageKey();
    },

    /**
     * Load persisted RZ state and fallback to running.
     */
    loadRzState() {
        return window.AppUiCommonModule.loadRzState(this);
    },

    /**
     * Persist and apply RZ operation state.
     * @param {'running'|'paused'|'stopped'} state
     */
    setRzState(state) {
        return window.AppUiCommonModule.setRzState(this, state);
    },

    /**
     * Update top badge + map border according to current RZ state.
     */
    applyRzStateUi() {
        return window.AppOperationsRzModule.applyRzStateUi(this);
    },

    /**
     * Apply RZ state based on operation command.
     * @param {string} command
     */
    applyRzStateFromCommand(command) {
        return window.AppOperationsRzModule.applyRzStateFromCommand(this, command);
    },

    /**
     * Inspect message payload and update RZ state when command/state text indicates change.
     * @param {Object} message
     */
    applyRzStateFromMessage(message) {
        return window.AppOperationsRzModule.applyRzStateFromMessage(this, message);
    },

    /**
     * Handle quick action button click
     * @param {string} action
     */
    handleQuickAction(action) {
        return window.AppOperationsIncidentsModule.handleQuickAction(this, action);
    },

    /**
     * Refresh readiness gate state from backend for admin dashboard.
     */
    startGateStatusRefresh() {
        return window.AppOperationsRzModule.startGateStatusRefresh(this);
    },

    /**
     * Load readiness snapshot and update gate indicator in admin board.
     * @returns {Promise<void>}
     */
    async refreshGateStatus() {
        return window.AppOperationsRzModule.refreshGateStatus(this);
    },

    /**
     * Queue immediate gate refresh (debounced) for event-driven updates.
     */
    requestGateStatusRefresh() {
        return window.AppOperationsRzModule.requestGateStatusRefresh(this);
    },

    /**
     * Return true when current user is vedeni role.
     * @returns {boolean}
     */
    isVedeniUser() {
        return window.AppOperationsRzModule.isVedeniUser(this);
    },

    /**
     * Determine if message should appear in incident warning board.
     * @param {Object} message
     * @returns {boolean}
     */
    isIncidentForDashboard(message) {
        return window.AppOperationsIncidentsModule.isIncidentForDashboard(message);
    },

    /**
     * Add newest incident to warning board for vedeni.
     * @param {Object} message
     */
    addIncidentWarning(message, persist = true) {
        return window.AppOperationsIncidentsModule.addIncidentWarning(this, message, persist);
    },

    /**
     * Get local storage key for per-user persisted UI state.
     * @param {string} bucket
     * @returns {string}
     */
    getStateStorageKey(bucket) {
        return window.AppUiCommonModule.getStateStorageKey(this, bucket);
    },

    /**
     * Load persisted state arrays for current user.
     */
    loadPersistedState() {
        return window.AppUiCommonModule.loadPersistedState(this);
    },

    /**
     * Persist one UI record into local storage with bounded history.
     * @param {'chat'|'info'|'incidents'} bucket
     * @param {Object} payload
     */
    persistStateItem(bucket, payload) {
        return window.AppUiCommonModule.persistStateItem(this, bucket, payload);
    },

    /**
     * Restore persisted chat/info/incident messages into current UI.
     */
    restorePersistedUiState() {
        return window.AppUiCommonModule.restorePersistedUiState(this);
    },

    /**
     * Set vedeni contact link for komisar quick actions.
     */
    updateVedeniContact() {
        return window.AppUiCommonModule.updateVedeniContact(this);
    },

    /**
     * Warn vedeni when station stops communicating during running RZ.
     * @param {Array<Object>} stations
     */
    handleStationsWentOffline(stations) {
        if (!this.isVedeniUser() || this.rzState !== 'running' || !Array.isArray(stations) || !stations.length) {
            return;
        }

        stations.forEach((station, index) => {
            const stationId = station?.station_id || 'N/A';
            const phone = station?.phone || 'neuvedeno';
            const email = station?.email || 'neuvedeno';
            const content = `⚠️ Pozice ${stationId} přestala komunikovat. Kontakt: ${phone} / ${email}`;
            const timestamp = new Date(Date.now() + index).toISOString();
            const warningMessage = {
                message_id: `offline_warn_${stationId}_${Date.now()}_${index}`,
                sender: {
                    user_id: 'system',
                    name: 'Systém',
                    role: 'system',
                    phone,
                    email,
                },
                message_type: 'system',
                priority: 'high',
                content,
                created_at: timestamp,
            };

            this.displayMessage(warningMessage);
            this.displayInfoMessage(warningMessage);
            this.showToast(content, 'error');
            this.logUiAction('station_went_offline_warning', {
                station_id: stationId,
                phone,
                email,
                rz_state: this.rzState,
            });
        });
    },

    /**
     * Send frontend action audit log to backend.
     * @param {string} action
     * @param {Object} details
     */
    async logUiAction(action, details = {}) {
        if (!action) {
            return;
        }

        const authIdentifier = window.Auth.getAuthIdentifier();
        if (!authIdentifier) {
            return;
        }

        const headers = {
            'Content-Type': 'application/json',
            'X-Auth-Identifier': authIdentifier,
        };

        if (this.user?.session_token) {
            headers['X-Session-Token'] = this.user.session_token;
        }

        try {
            await fetch('http://localhost:8000/api/audit/frontend-event', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    action,
                    source: 'frontend_app',
                    details,
                }),
            });
        } catch (error) {
            console.error('UI audit log failed:', error);
        }
    },

    /**
     * Track known users and stations for tag suggestions.
     * @param {Object} message
     */
    registerSenderForTagging(message) {
        return window.AppTaggingModule.registerSenderForTagging(this, message);
    },

    /**
     * Update known station tags from status API payload.
     * @param {Array<Object>} stations
     */
    updateStationTags(stations) {
        return window.AppTaggingModule.updateStationTags(this, stations);
    },

    /**
     * Handle click on station tag and focus marker on map.
     * @param {MouseEvent} event
     */
    handleTagClick(event) {
        return window.AppTaggingModule.handleTagClick(this, event);
    },

    /**
     * Resolve known tag item in case-insensitive mode.
     * @param {Set<string>} collection
     * @param {string} value
     * @returns {string|null}
     */
    resolveKnownItem(collection, value) {
        return window.AppTaggingModule.resolveKnownItem(collection, value);
    },

    /**
     * Process message input and show tag suggestions.
     * @param {InputEvent} event
     */
    onMessageInputChanged(event) {
        return window.AppTaggingModule.onMessageInputChanged(this, event);
    },

    /**
     * Find active tag context near caret position.
     * @param {string} text
     * @param {number} caret
     * @returns {Object|null}
     */
    findTagContext(text, caret) {
        return window.AppTaggingModule.findTagContext(text, caret);
    },

    /**
     * Render suggestion dropdown under message input.
     */
    renderTagSuggestions() {
        return window.AppTaggingModule.renderTagSuggestions(this);
    },

    /**
     * Apply selected tag into message input.
     * @param {string} tag
     */
    applyTagSuggestion(tag) {
        return window.AppTaggingModule.applyTagSuggestion(this, tag);
    },

    /**
     * Keyboard support for suggestion dropdown.
     * @param {KeyboardEvent} event
     */
    onMessageInputKeyDown(event) {
        return window.AppTaggingModule.onMessageInputKeyDown(this, event);
    },

    /**
     * Hide and reset tag suggestion UI.
     */
    hideTagSuggestions() {
        return window.AppTaggingModule.hideTagSuggestions(this);
    },

    /**
     * Render message content with highlighted @user and #station tags.
     * @param {string} text
     * @returns {string}
     */
    renderTaggedContent(text) {
        return window.AppTaggingModule.renderTaggedContent(this, text);
    },

    /**
     * Handle logout
     */
    handleLogout() {
        return window.AppUiCommonModule.handleLogout();
    },

    /**
     * Show toast notification
     * @param {string} message
     * @param {string} type - 'success', 'error', 'info'
     */
    showToast(message, type = 'info') {
        return window.AppUiCommonModule.showToast(message, type);
    },

    /**
     * Format timestamp to HH:MM
     * @param {string} isoString
     * @returns {string}
     */
    formatTime(isoString) {
        return window.AppUiCommonModule.formatTime(isoString);
    },

    /**
     * Format timestamp to locale date and time.
     * @param {string} isoString
     * @returns {string}
     */
    formatDateTime(isoString) {
        return window.AppUiCommonModule.formatDateTime(isoString);
    },

    /**
     * Escape HTML to prevent XSS
     * @param {string} text
     * @returns {string}
     */
    escapeHtml(text) {
        return window.AppUiCommonModule.escapeHtml(text);
    },
};

// Export to global scope
window.App = App;
