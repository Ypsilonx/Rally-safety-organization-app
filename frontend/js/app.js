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
    rzState: 'running',

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

        this.loadPersistedState();
        this.restorePersistedUiState();
        this.loadRzState();
        this.applyRzStateUi();

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
        }

        this.updateVedeniContact();
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
        window.wsClient.on('onStatusChange', (status) => this.handleStatusChange(status));
        window.wsClient.on('onError', (error) => this.handleError(error));
        
        // Connect
        window.wsClient.connect(authIdentifier);
    },

    /**
     * Setup event listeners for UI elements
     */
    setupEventListeners() {
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
            openCommsBtn.addEventListener('click', () => this.openCommsPanel());
        }

        const closeCommsBtn = document.getElementById('close-comms-btn');
        if (closeCommsBtn) {
            closeCommsBtn.addEventListener('click', () => this.closeCommsPanel());
        }

        const commsOverlay = document.getElementById('comms-overlay');
        if (commsOverlay) {
            commsOverlay.addEventListener('click', () => this.closeCommsPanel());
        }

        document.querySelectorAll('.comms-tab').forEach((tabBtn) => {
            tabBtn.addEventListener('click', () => {
                this.switchCommsTab(tabBtn.dataset.tab || 'chat');
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
                this.sendAlertPreset(btn.dataset.alert);
            });
        });

        // Quick action buttons
        document.querySelectorAll('.btn-quick').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.handleQuickAction(action);
            });
        });

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

        window.addEventListener('stations:update', (event) => {
            const stations = event.detail?.stations || [];
            this.updateStationTags(stations);
        });
    },

    /**
     * Send chat message
     */
    sendChatMessage() {
        const input = document.getElementById('message-input');
        const content = input.value.trim();
        
        if (!content) return;
        
        // Optimistic update - show own message immediately
        const ownMessage = {
            message_id: `temp_${Date.now()}`,
            sender: {
                user_id: this.user.user_id,
                name: this.user.name,
                role: this.user.role,
                station_id: this.user.station_id || null,
            },
            message_type: 'chat',
            content: content,
            created_at: new Date().toISOString()
        };
        
        // Display immediately (as own message)
        this.displayMessage(ownMessage);
        
        // Send via WebSocket
        window.wsClient.sendChatMessage(content);
        
        // Clear input
        input.value = '';
        this.hideTagSuggestions();
        input.focus();
    },

    /**
     * Handle incoming WebSocket message
     * @param {Object} message
     */
    handleMessage(message) {
        console.log('Handling message:', message);

        const normalized = this.normalizeIncomingMessage(message);

        if (!normalized) {
            return;
        }

        if (normalized?.type === 'error') {
            const missing = Array.isArray(normalized?.details?.missing_stations)
                ? normalized.details.missing_stations.join(', ')
                : '';
            const detailText = missing ? ` Chybí: ${missing}` : '';
            this.showToast(`${normalized.message || 'Chyba komunikace'}${detailText}`, 'error');
            return;
        }

        this.applyRzStateFromMessage(normalized);
        this.applyMarkerAlertFromMessage(normalized);
        this.registerSenderForTagging(normalized);
        
        // Display message in communication channels
        this.displayMessage(normalized);

        if (this.isInfoChannelMessage(normalized)) {
            this.displayInfoMessage(normalized);
        }

        if (this.isVedeniUser() && this.isIncidentForDashboard(normalized)) {
            this.addIncidentWarning(normalized);
        }
        
        // Show notification for certain message types
        if (normalized.message_type === 'incident' || normalized.message_type === 'broadcast') {
            this.showToast(normalized.content, 'error');
        }
    },

    /**
     * Update map station alert visuals based on incoming message semantics.
     * @param {Object} message
     */
    applyMarkerAlertFromMessage(message) {
        const stationId = message?.sender?.station_id;
        if (!stationId) {
            if (message?.operation_command === 'rz_resume') {
                window.dispatchEvent(new CustomEvent('station:clear-all-alerts'));
            }
            return;
        }

        if (message.message_type === 'incident') {
            window.dispatchEvent(new CustomEvent('station:alert', {
                detail: {
                    stationId,
                },
            }));
            return;
        }

        if (message.readiness_state === 'ready') {
            window.dispatchEvent(new CustomEvent('station:clear-alert', {
                detail: {
                    stationId,
                },
            }));
        }
    },

    /**
     * Normalize raw incoming message payloads to common shape.
     * @param {Object} message
     * @returns {Object|null}
     */
    normalizeIncomingMessage(message) {
        if (!message) {
            return null;
        }

        if (message.type === 'error') {
            return message;
        }

        if (message.message_type) {
            const content = String(message.content || '').trim();
            if (!content && message.message_type !== 'heartbeat') {
                return null;
            }
            return message;
        }

        if (message.type === 'system') {
            const content = String(message.message || '').trim();
            if (!content) {
                return null;
            }
            return {
                message_id: `sys_${Date.now()}`,
                sender: {
                    user_id: 'system',
                    name: 'Systém',
                    role: 'system',
                },
                message_type: 'system',
                priority: 'normal',
                content,
                created_at: message.timestamp || new Date().toISOString(),
            };
        }

        return null;
    },

    /**
     * Display message in chat area
     * @param {Object} message
     */
    displayMessage(message, persist = true) {
        const messagesArea = document.getElementById('messages');
        
        // Remove welcome message if present
        const welcomeMsg = messagesArea.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        // Create message element
        const messageEl = document.createElement('div');
        messageEl.className = 'message';
        
        // Check if own message
        const isOwnMessage = message.sender?.user_id === this.user.user_id;
        if (isOwnMessage) {
            messageEl.classList.add('own');
        }
        
        // System/broadcast messages
        if (message.message_type === 'system' || message.message_type === 'broadcast') {
            messageEl.classList.add('system');
        }
        
        // Build message HTML
        const senderName = message.sender?.name || 'Systém';
        const timestamp = this.formatTime(message.created_at);
        
        messageEl.innerHTML = `
            <div class="message-header">
                <span class="message-sender">${senderName}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-content">${this.renderTaggedContent(message.content)}</div>
        `;
        
        // Add to DOM
        messagesArea.appendChild(messageEl);

        if (persist) {
            this.persistStateItem('chat', message);
        }
        
        // Scroll to bottom
        messagesArea.scrollTop = messagesArea.scrollHeight;
    },

    /**
     * Determine whether message belongs in info channel.
     * @param {Object} message
     * @returns {boolean}
     */
    isInfoChannelMessage(message) {
        const type = message.message_type;
        return type === 'broadcast' || type === 'incident' || type === 'status_update' || type === 'system';
    },

    /**
     * Display message in dedicated info feed.
     * @param {Object} message
     */
    displayInfoMessage(message, persist = true) {
        const infoFeed = document.getElementById('info-feed');
        if (!infoFeed) {
            return;
        }

        const welcomeMsg = infoFeed.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        const item = document.createElement('div');
        item.className = 'message system';

        const senderName = message.sender?.name || 'Systém';
        const timestamp = this.formatTime(message.created_at);
        item.innerHTML = `
            <div class="message-header">
                <span class="message-sender">${this.escapeHtml(senderName)}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-content">${this.renderTaggedContent(message.content || '')}</div>
        `;

        infoFeed.appendChild(item);
        infoFeed.scrollTop = infoFeed.scrollHeight;

        if (persist) {
            this.persistStateItem('info', message);
        }
    },

    /**
     * Switch between chat and info tabs in communication panel.
     * @param {string} tabName
     */
    switchCommsTab(tabName) {
        this.activeCommsTab = tabName === 'info' ? 'info' : 'chat';

        document.querySelectorAll('.comms-tab').forEach((btn) => {
            const isActive = btn.dataset.tab === this.activeCommsTab;
            btn.classList.toggle('active', isActive);
            btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });

        const chatPane = document.getElementById('chat-pane');
        const infoPane = document.getElementById('info-pane');
        if (chatPane) {
            chatPane.classList.toggle('active', this.activeCommsTab === 'chat');
        }
        if (infoPane) {
            infoPane.classList.toggle('active', this.activeCommsTab === 'info');
        }
    },

    /**
     * Open communication drawer on mobile.
     */
    openCommsPanel() {
        const panel = document.getElementById('comms-panel');
        const overlay = document.getElementById('comms-overlay');
        if (panel) {
            panel.classList.add('open');
        }
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    },

    /**
     * Close communication drawer on mobile.
     */
    closeCommsPanel() {
        const panel = document.getElementById('comms-panel');
        const overlay = document.getElementById('comms-overlay');
        if (panel) {
            panel.classList.remove('open');
        }
        if (overlay) {
            overlay.classList.add('hidden');
        }
    },

    /**
     * Handle connection status change
     * @param {string} status - 'online', 'offline', 'reconnecting', 'failed'
     */
    handleStatusChange(status) {
        console.log('Status changed:', status);
        
        const indicator = document.getElementById('connection-status');
        
        // Update indicator
        indicator.className = 'status-indicator';
        
        switch (status) {
            case 'online':
                indicator.classList.add('online');
                indicator.title = 'Připojeno';
                this.showToast('Připojeno k serveru', 'success');
                break;
                
            case 'offline':
                indicator.classList.add('offline');
                indicator.title = 'Odpojeno';
                break;
                
            case 'reconnecting':
                indicator.classList.add('offline');
                indicator.title = 'Připojování...';
                break;
                
            case 'failed':
                indicator.classList.add('offline');
                indicator.title = 'Spojení selhalo';
                this.showToast('Spojení se serverem selhalo', 'error');
                this.scheduleReauthentication('Spojení selhalo. Přihlaste se znovu.');
                break;

            case 'auth_failed':
                indicator.classList.add('offline');
                indicator.title = 'Neplatné přihlášení';
                this.showToast('Relace vypršela. Přihlaste se znovu.', 'error');
                this.scheduleReauthentication('Relace vypršela. Přihlaste se znovu.');
                break;
        }
    },

    /**
     * Redirect to login after communication/auth failures.
     * @param {string} reason
     */
    scheduleReauthentication(reason) {
        if (this.reauthScheduled) {
            return;
        }

        this.reauthScheduled = true;
        setTimeout(() => {
            if (reason) {
                console.warn(reason);
            }
            window.Auth.logout();
        }, 1200);
    },

    /**
     * Handle WebSocket error
     * @param {Error} error
     */
    handleError(error) {
        console.error('App error:', error);
        this.showToast('Chyba komunikace', 'error');
    },

    /**
     * Update admin stats
     */
    updateStats() {
        // Message count intentionally hidden from dashboard for better signal/noise ratio.
    },

    /**
     * Toggle admin panel collapse
     */
    toggleAdminPanel() {
        const header = document.querySelector('.panel-header');
        const content = document.querySelector('.panel-content');
        
        if (header.classList.contains('collapsed')) {
            header.classList.remove('collapsed');
            content.style.display = '';
        } else {
            header.classList.add('collapsed');
            content.style.display = 'none';
        }

        if (window.MapModule && window.MapModule.map) {
            setTimeout(() => window.MapModule.map.invalidateSize(), 150);
        }
    },

    /**
     * Send broadcast message (admin only)
     */
    async sendBroadcast() {
        const content = prompt('Hromadná zpráva všem stanicím:');
        if (!content || !content.trim()) return;
        
        // Get current online count from stats
        let onlineCount = '-';
        try {
            const statsResponse = await fetch('http://localhost:8000/api/stats');
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                onlineCount = stats.active_connections || 0;
            }
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
        
        // Show broadcast message immediately in own UI
        const broadcastMessage = {
            message_id: `broadcast_${Date.now()}`,
            sender: {
                user_id: this.user.user_id,
                name: this.user.name,
                role: this.user.role
            },
            message_type: 'broadcast',
            content: `📢 HROMADNÁ ZPRÁVA VŠEM\n\n${content.trim()}\n\n→ Odesláno ${onlineCount} online stanicím`,
            created_at: new Date().toISOString()
        };
        
        this.displayMessage(broadcastMessage);
        
        // Send via WebSocket
        window.wsClient.sendSystemMessage('broadcast', content.trim());
        
        this.showToast(`Hromadná zpráva odeslána ${onlineCount} stanicím`, 'success');
    },

    /**
     * Send predefined operational alert from vedeni panel.
     * @param {string} alertKey
     */
    sendAlertPreset(alertKey) {
        const presets = {
            rz_stop: { text: '🛑 RZ zastavena - okamžitě zajistit trať.', priority: 'critical' },
            track_problem: { text: '⚠️ Pozor problém na trati - zvýšená opatrnost.', priority: 'high' },
            rz_hold: { text: '⏸️ RZ pozastavena - vyčkejte dalších pokynů.', priority: 'high' },
            rz_resume: { text: '✅ RZ opět v provozu - pokračujte dle standardního režimu.', priority: 'normal' },
        };

        const preset = presets[alertKey];
        if (!preset) {
            return;
        }

        const payload = {
            message_type: 'broadcast',
            priority: preset.priority,
            content: preset.text,
            operation_command: alertKey,
            created_at: new Date().toISOString(),
        };

        const ownMessage = {
            message_id: `preset_${Date.now()}`,
            sender: {
                user_id: this.user.user_id,
                name: this.user.name,
                role: this.user.role,
                station_id: this.user.station_id || null,
            },
            ...payload,
        };

        this.displayMessage(ownMessage);
        this.displayInfoMessage(ownMessage);
        this.applyRzStateFromCommand(alertKey);
        window.wsClient.sendMessage(payload);
        this.showToast('Předdefinované hlášení odesláno', 'success');
    },

    /**
     * Storage key for persistent RZ state in local browser.
     * @returns {string}
     */
    getRzStateStorageKey() {
        return 'rally_rz_state';
    },

    /**
     * Load persisted RZ state and fallback to running.
     */
    loadRzState() {
        const saved = localStorage.getItem(this.getRzStateStorageKey());
        if (saved === 'running' || saved === 'paused' || saved === 'stopped') {
            this.rzState = saved;
            return;
        }
        this.rzState = 'running';
    },

    /**
     * Persist and apply RZ operation state.
     * @param {'running'|'paused'|'stopped'} state
     */
    setRzState(state) {
        this.rzState = state;
        localStorage.setItem(this.getRzStateStorageKey(), state);
        this.applyRzStateUi();
    },

    /**
     * Update top badge + map border according to current RZ state.
     */
    applyRzStateUi() {
        const badge = document.getElementById('rz-live-status');
        const mapPanel = document.querySelector('.map-panel');

        if (badge) {
            badge.classList.remove('running', 'paused', 'stopped');
            badge.classList.add(this.rzState);

            if (this.rzState === 'paused') {
                badge.textContent = 'RZ: Pozastavena';
            } else if (this.rzState === 'stopped') {
                badge.textContent = 'RZ: Zastavena';
            } else {
                badge.textContent = 'RZ: V provozu';
            }
        }

        if (mapPanel) {
            const warning = this.rzState === 'paused' || this.rzState === 'stopped';
            mapPanel.classList.toggle('rz-warning', warning);
        }
    },

    /**
     * Apply RZ state based on operation command.
     * @param {string} command
     */
    applyRzStateFromCommand(command) {
        if (command === 'rz_stop') {
            this.setRzState('stopped');
        } else if (command === 'rz_hold') {
            this.setRzState('paused');
        } else if (command === 'rz_resume') {
            this.setRzState('running');
        }
    },

    /**
     * Inspect message payload and update RZ state when command/state text indicates change.
     * @param {Object} message
     */
    applyRzStateFromMessage(message) {
        if (!message) {
            return;
        }

        if (message.operation_command) {
            this.applyRzStateFromCommand(message.operation_command);
            return;
        }

        const text = String(message.content || '').toLowerCase();
        if (text.includes('rz zastavena')) {
            this.setRzState('stopped');
        } else if (text.includes('rz pozastavena')) {
            this.setRzState('paused');
        } else if (text.includes('rz opět v provozu')) {
            this.setRzState('running');
        }
    },

    /**
     * Handle quick action button click
     * @param {string} action
     */
    handleQuickAction(action) {
        if (action === 'ready') {
            this.incidentGateActive = false;
            if (this.user.station_id) {
                window.dispatchEvent(new CustomEvent('station:clear-alert', {
                    detail: {
                        stationId: this.user.station_id,
                    },
                }));
            }
            window.wsClient.sendMessage({
                message_type: 'status_update',
                readiness_state: 'ready',
                content: '✅ Stanice připravena',
                created_at: new Date().toISOString(),
            });
            this.showToast('Stav odeslán', 'success');
            return;
        }

        if (action === 'issue') {
            const detail = prompt('Popiš stručně problém na stanici:');
            if (!detail || !detail.trim()) {
                this.showToast('Incident nebyl odeslán', 'info');
                return;
            }

            const payload = {
                message_type: 'incident',
                priority: 'high',
                target_roles: ['vedouci', 'zastupce'],
                readiness_state: 'not_ready',
                content: `⚠️ INCIDENT: ${detail.trim()}`,
                created_at: new Date().toISOString(),
            };

            const ownMessage = {
                message_id: `incident_${Date.now()}`,
                sender: {
                    user_id: this.user.user_id,
                    name: this.user.name,
                    role: this.user.role,
                    station_id: this.user.station_id || null,
                },
                ...payload,
            };

            this.displayMessage(ownMessage);
            this.displayInfoMessage(ownMessage);
            this.applyMarkerAlertFromMessage(ownMessage);
            window.wsClient.sendMessage(payload);
            this.incidentGateActive = true;
            this.showToast('Incident odeslán vedení', 'error');
            return;
        }

        if (action === 'emergency') {
            const payload = {
                message_type: 'incident',
                priority: 'critical',
                target_roles: ['vedouci', 'zastupce'],
                readiness_state: 'not_ready',
                operation_command: 'emergency',
                content: '🆘 AKUTNÍ: Okamžitá pomoc na stanici!',
                created_at: new Date().toISOString(),
            };

            const ownMessage = {
                message_id: `emergency_${Date.now()}`,
                sender: {
                    user_id: this.user.user_id,
                    name: this.user.name,
                    role: this.user.role,
                    station_id: this.user.station_id || null,
                },
                ...payload,
            };

            this.displayMessage(ownMessage);
            this.displayInfoMessage(ownMessage);
            this.applyMarkerAlertFromMessage(ownMessage);
            window.wsClient.sendMessage(payload);
            this.incidentGateActive = true;
            this.showToast('Akutní incident odeslán vedení', 'error');
        }
    },

    /**
     * Refresh readiness gate state from backend for admin dashboard.
     */
    startGateStatusRefresh() {
        this.refreshGateStatus().catch((error) => {
            console.error('Gate status refresh failed:', error);
        });

        setInterval(() => {
            this.refreshGateStatus().catch((error) => {
                console.error('Gate status refresh failed:', error);
            });
        }, 12000);
    },

    /**
     * Load readiness snapshot and update gate indicator in admin board.
     * @returns {Promise<void>}
     */
    async refreshGateStatus() {
        const gateLabel = document.getElementById('incident-gate-status');
        const missingLabel = document.getElementById('incident-gate-missing');
        if (!gateLabel || !missingLabel || !this.isVedeniUser()) {
            return;
        }

        const response = await fetch('http://localhost:8000/api/stations/readiness');
        if (!response.ok) {
            gateLabel.textContent = 'Gate: nedostupné';
            gateLabel.classList.remove('gate-open', 'gate-closed');
            missingLabel.textContent = '-';
            return;
        }

        const snapshot = await response.json();
        const incidentActive = Boolean(snapshot.incident_active);
        const total = Number(snapshot.total_stations || 0);
        const ready = Number(snapshot.ready_stations || 0);
        const missingStations = Array.isArray(snapshot.stations)
            ? snapshot.stations
                .filter((station) => station.ready === false)
                .map((station) => station.station_id || 'N/A')
            : [];
        this.incidentGateActive = incidentActive;

        if (!incidentActive) {
            gateLabel.textContent = 'Gate: otevřeno';
            gateLabel.classList.add('gate-open');
            gateLabel.classList.remove('gate-closed');
            missingLabel.textContent = '-';
            return;
        }

        gateLabel.textContent = `Gate: čeká READY ${ready}/${total}`;
        gateLabel.classList.add('gate-closed');
        gateLabel.classList.remove('gate-open');
        missingLabel.textContent = missingStations.length ? missingStations.join(', ') : '-';
    },

    /**
     * Return true when current user is vedeni role.
     * @returns {boolean}
     */
    isVedeniUser() {
        return this.user?.role === 'vedouci' || this.user?.role === 'zastupce';
    },

    /**
     * Determine if message should appear in incident warning board.
     * @param {Object} message
     * @returns {boolean}
     */
    isIncidentForDashboard(message) {
        return message.message_type === 'incident' || message.message_type === 'broadcast';
    },

    /**
     * Add newest incident to warning board for vedeni.
     * @param {Object} message
     */
    addIncidentWarning(message, persist = true) {
        const feed = document.getElementById('incident-feed');
        if (!feed) {
            return;
        }

        const empty = feed.querySelector('.incident-empty');
        if (empty) {
            empty.remove();
        }

        const senderName = this.escapeHtml(message.sender?.name || 'Neznámý');
        const senderPhone = this.escapeHtml(message.sender?.phone || 'neuvedeno');
        const text = this.escapeHtml(message.content || 'Bez obsahu');

        const item = document.createElement('div');
        feed.querySelectorAll('.incident-item.latest').forEach((existing) => {
            existing.classList.remove('latest');
        });

        item.className = 'incident-item latest';
        item.innerHTML = `
            <strong>${senderName}</strong> (${this.formatTime(message.created_at)})<br>
            ${text}<br>
            Kontakt: <a href="tel:${senderPhone}">${senderPhone}</a>
        `;

        feed.prepend(item);
        while (feed.children.length > 20) {
            feed.removeChild(feed.lastChild);
        }

        if (persist) {
            this.persistStateItem('incidents', message);
        }
    },

    /**
     * Get local storage key for per-user persisted UI state.
     * @param {string} bucket
     * @returns {string}
     */
    getStateStorageKey(bucket) {
        return `rally_state_${this.user?.user_id || 'guest'}_${bucket}`;
    },

    /**
     * Load persisted state arrays for current user.
     */
    loadPersistedState() {
        ['chat', 'info', 'incidents'].forEach((bucket) => {
            try {
                const raw = localStorage.getItem(this.getStateStorageKey(bucket));
                const parsed = raw ? JSON.parse(raw) : [];
                this.persistedState[bucket] = Array.isArray(parsed) ? parsed : [];
            } catch (_error) {
                this.persistedState[bucket] = [];
            }
        });
    },

    /**
     * Persist one UI record into local storage with bounded history.
     * @param {'chat'|'info'|'incidents'} bucket
     * @param {Object} payload
     */
    persistStateItem(bucket, payload) {
        if (!this.persistedState[bucket]) {
            return;
        }

        const maxSize = this.stateStorageLimits[bucket] || 100;
        this.persistedState[bucket].push(payload);
        if (this.persistedState[bucket].length > maxSize) {
            this.persistedState[bucket] = this.persistedState[bucket].slice(-maxSize);
        }

        localStorage.setItem(
            this.getStateStorageKey(bucket),
            JSON.stringify(this.persistedState[bucket]),
        );
    },

    /**
     * Restore persisted chat/info/incident messages into current UI.
     */
    restorePersistedUiState() {
        this.persistedState.chat.forEach((message) => this.displayMessage(message, false));
        this.persistedState.info.forEach((message) => this.displayInfoMessage(message, false));
        this.persistedState.incidents.forEach((message) => this.addIncidentWarning(message, false));
    },

    /**
     * Set vedeni contact link for komisar quick actions.
     */
    updateVedeniContact() {
        const link = document.getElementById('vedeni-phone-link');
        if (!link) {
            return;
        }

        const phone = this.user?.vedeni_phone || '+420777123456';
        link.href = `tel:${phone}`;
        link.textContent = phone;
    },

    /**
     * Track known users and stations for tag suggestions.
     * @param {Object} message
     */
    registerSenderForTagging(message) {
        const senderName = message?.sender?.name;
        if (senderName) {
            this.knownUsers.add(senderName);
        }
    },

    /**
     * Update known station tags from status API payload.
     * @param {Array<Object>} stations
     */
    updateStationTags(stations) {
        stations.forEach((station) => {
            if (station.station_id) {
                this.knownStations.add(station.station_id);
            }

            if (station.name) {
                this.knownUsers.add(station.name);
            }
        });
    },

    /**
     * Handle click on station tag and focus marker on map.
     * @param {MouseEvent} event
     */
    handleTagClick(event) {
        const stationTag = event.target.closest('.chat-tag-station[data-station-id]');
        if (!stationTag) {
            return;
        }

        const stationId = stationTag.dataset.stationId;
        if (!stationId || !window.MapModule || typeof window.MapModule.focusStation !== 'function') {
            return;
        }

        const focused = window.MapModule.focusStation(stationId);
        if (!focused) {
            this.showToast(`Stanice ${stationId} zatím není na mapě`, 'info');
        }
    },

    /**
     * Resolve known tag item in case-insensitive mode.
     * @param {Set<string>} collection
     * @param {string} value
     * @returns {string|null}
     */
    resolveKnownItem(collection, value) {
        const normalized = String(value || '').toLowerCase();
        for (const item of collection) {
            if (item.toLowerCase() === normalized) {
                return item;
            }
        }
        return null;
    },

    /**
     * Process message input and show tag suggestions.
     * @param {InputEvent} event
     */
    onMessageInputChanged(event) {
        const input = event.target;
        const value = input.value;
        const caret = input.selectionStart || value.length;
        const context = this.findTagContext(value, caret);

        if (!context) {
            this.hideTagSuggestions();
            return;
        }

        const pool = context.type === '@'
            ? Array.from(this.knownUsers)
            : Array.from(this.knownStations);

        const normalizedQuery = context.query.toLowerCase();
        const candidates = pool
            .filter((item) => item.toLowerCase().startsWith(normalizedQuery))
            .sort((a, b) => a.localeCompare(b, 'cs'))
            .slice(0, 7);

        if (!candidates.length) {
            this.hideTagSuggestions();
            return;
        }

        this.tagSuggestion = {
            active: true,
            type: context.type,
            query: context.query,
            start: context.start,
            end: caret,
            selectedIndex: 0,
            candidates,
        };

        this.renderTagSuggestions();
    },

    /**
     * Find active tag context near caret position.
     * @param {string} text
     * @param {number} caret
     * @returns {Object|null}
     */
    findTagContext(text, caret) {
        const before = text.slice(0, caret);
        const markerIndex = Math.max(before.lastIndexOf('@'), before.lastIndexOf('#'));
        if (markerIndex < 0) {
            return null;
        }

        const marker = before[markerIndex];
        const prefix = before.slice(markerIndex + 1);

        if (markerIndex > 0) {
            const prev = before[markerIndex - 1];
            if (!/\s/.test(prev)) {
                return null;
            }
        }

        if (/\s/.test(prefix)) {
            return null;
        }

        return {
            type: marker,
            query: prefix,
            start: markerIndex,
        };
    },

    /**
     * Render suggestion dropdown under message input.
     */
    renderTagSuggestions() {
        const list = document.getElementById('tag-suggestions');
        if (!list || !this.tagSuggestion.active) {
            return;
        }

        const prefix = this.tagSuggestion.type;
        list.innerHTML = this.tagSuggestion.candidates
            .map((item, index) => {
                const active = index === this.tagSuggestion.selectedIndex ? 'active' : '';
                return `<button type="button" class="tag-suggestion-item ${active}" data-tag="${this.escapeHtml(item)}">${prefix}${this.escapeHtml(item)}</button>`;
            })
            .join('');

        list.classList.remove('hidden');

        list.querySelectorAll('.tag-suggestion-item').forEach((button) => {
            button.addEventListener('mousedown', (event) => {
                event.preventDefault();
                const tag = button.dataset.tag;
                this.applyTagSuggestion(tag);
            });
        });
    },

    /**
     * Apply selected tag into message input.
     * @param {string} tag
     */
    applyTagSuggestion(tag) {
        const input = document.getElementById('message-input');
        if (!input || !this.tagSuggestion.active) {
            return;
        }

        const before = input.value.slice(0, this.tagSuggestion.start);
        const after = input.value.slice(this.tagSuggestion.end);
        const insert = `${this.tagSuggestion.type}${tag} `;
        input.value = `${before}${insert}${after}`;
        const newCaret = (before + insert).length;
        input.setSelectionRange(newCaret, newCaret);
        input.focus();
        this.hideTagSuggestions();
    },

    /**
     * Keyboard support for suggestion dropdown.
     * @param {KeyboardEvent} event
     */
    onMessageInputKeyDown(event) {
        if (!this.tagSuggestion.active) {
            return;
        }

        const total = this.tagSuggestion.candidates.length;
        if (!total) {
            return;
        }

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            this.tagSuggestion.selectedIndex = (this.tagSuggestion.selectedIndex + 1) % total;
            this.renderTagSuggestions();
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            this.tagSuggestion.selectedIndex = (this.tagSuggestion.selectedIndex - 1 + total) % total;
            this.renderTagSuggestions();
        } else if (event.key === 'Enter') {
            event.preventDefault();
            const tag = this.tagSuggestion.candidates[this.tagSuggestion.selectedIndex];
            this.applyTagSuggestion(tag);
        } else if (event.key === 'Escape') {
            event.preventDefault();
            this.hideTagSuggestions();
        }
    },

    /**
     * Hide and reset tag suggestion UI.
     */
    hideTagSuggestions() {
        this.tagSuggestion.active = false;
        this.tagSuggestion.candidates = [];
        this.tagSuggestion.selectedIndex = 0;

        const list = document.getElementById('tag-suggestions');
        if (list) {
            list.classList.add('hidden');
            list.innerHTML = '';
        }
    },

    /**
     * Render message content with highlighted @user and #station tags.
     * @param {string} text
     * @returns {string}
     */
    renderTaggedContent(text) {
        const source = String(text || '');
        const tokenRegex = /([@#][\w-]+)/g;
        const parts = source.split(tokenRegex);

        return parts.map((part) => {
            if (part.startsWith('@')) {
                const rawUser = part.slice(1);
                const knownUser = this.resolveKnownItem(this.knownUsers, rawUser);
                if (!knownUser) {
                    return this.escapeHtml(part);
                }
                return `<span class="chat-tag chat-tag-user">@${this.escapeHtml(knownUser)}</span>`;
            }
            if (part.startsWith('#')) {
                const rawStation = part.slice(1);
                const knownStation = this.resolveKnownItem(this.knownStations, rawStation);
                if (!knownStation) {
                    return this.escapeHtml(part);
                }
                const safeStation = this.escapeHtml(knownStation);
                return `<span class="chat-tag chat-tag-station chat-tag-clickable" data-station-id="${safeStation}" title="Přejít na stanici na mapě">#${safeStation}</span>`;
            }
            return this.escapeHtml(part);
        }).join('');
    },

    /**
     * Handle logout
     */
    handleLogout() {
        if (confirm('Opravdu se chcete odhlásit?')) {
            window.Auth.logout();
        }
    },

    /**
     * Show toast notification
     * @param {string} message
     * @param {string} type - 'success', 'error', 'info'
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /**
     * Format timestamp to HH:MM
     * @param {string} isoString
     * @returns {string}
     */
    formatTime(isoString) {
        if (!isoString) return '';
        
        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString('cs-CZ', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        } catch {
            return '';
        }
    },

    /**
     * Escape HTML to prevent XSS
     * @param {string} text
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

// Export to global scope
window.App = App;
