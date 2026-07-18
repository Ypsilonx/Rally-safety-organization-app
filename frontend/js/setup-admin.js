/**
 * Rally Safety App - Setup/Admin screen module.
 * Handles pre-start configuration of positions, assignments and related UI.
 */

const SetupAdminModule = {
    RESERVED_VEDENI_STATION_IDS: new Set(['VRZ', 'ZVRZ', 'VBRZ', 'ZVBRZ']),

    /**
     * Return true when station id is one of leadership positions.
     * @param {string} stationId
     * @returns {boolean}
     */
    isVedeniStation(stationId) {
        return this.RESERVED_VEDENI_STATION_IDS.has(String(stationId || '').trim().toUpperCase());
    },

    /**
     * Return local storage key for setup map configuration.
     * @returns {string}
     */
    getMapConfigStorageKey() {
        return 'rally_setup_map_config_v1';
    },

    /**
     * Read map config from local storage.
     * @returns {{trackGeoJsonUrl: string, stationCoordinates: Object<string, Array<number>>}}
     */
    readStoredMapConfig() {
        try {
            const raw = localStorage.getItem(this.getMapConfigStorageKey());
            if (!raw) {
                return { trackGeoJsonUrl: '', stationCoordinates: {} };
            }
            const parsed = JSON.parse(raw);
            return {
                trackGeoJsonUrl: String(parsed.trackGeoJsonUrl || ''),
                stationCoordinates: parsed.stationCoordinates && typeof parsed.stationCoordinates === 'object'
                    ? parsed.stationCoordinates
                    : {},
            };
        } catch (_error) {
            return { trackGeoJsonUrl: '', stationCoordinates: {} };
        }
    },

    /**
     * Persist map config to local storage.
     * @param {Object} payload
     */
    storeMapConfig(payload) {
        localStorage.setItem(this.getMapConfigStorageKey(), JSON.stringify(payload));
    },

    /**
     * Merge map runtime config with storage and apply on startup/setup open.
     * @param {Object} app
     */
    applyStoredMapConfig(app) {
        if (!window.MapModule) {
            return;
        }

        const stored = this.readStoredMapConfig();
        const runtime = window.MapModule.getRuntimeConfig
            ? window.MapModule.getRuntimeConfig()
            : { trackGeoJsonUrl: '', stationCoordinates: {} };

        const mergedCoordinates = {
            ...(runtime.stationCoordinates || {}),
            ...(stored.stationCoordinates || {}),
        };

        window.MapModule.setTrackSource(stored.trackGeoJsonUrl || runtime.trackGeoJsonUrl || '');
        window.MapModule.setStationCoordinates(mergedCoordinates);
        this.storeMapConfig({
            trackGeoJsonUrl: String(stored.trackGeoJsonUrl || runtime.trackGeoJsonUrl || ''),
            stationCoordinates: mergedCoordinates,
        });
        this.syncMapConfigForm(app);
    },

    /**
     * Fill setup map config form with current values.
     * @param {Object} app
     */
    syncMapConfigForm(app) {
        const trackInput = document.getElementById('map-track-path');
        if (trackInput && window.MapModule) {
            trackInput.value = window.MapModule.config.trackGeoJsonUrl || '';
        }
        this.loadSelectedSetupStationCoordinate(app);
    },

    /**
     * Return default role suggested by station type.
     * @param {string} stationType
     * @returns {string}
     */
    getDefaultRoleForStation(stationType) {
        const mapping = {
            track_point: 'komisar_trat',
            corner: 'komisar_zatacka',
            timing: 'casomer',
            parking: 'parkovani',
            medical: 'zdravotnik',
            technical: 'technik',
            service: 'technik',
            start_finish: 'komisar_trat',
            other: 'komisar_trat',
        };
        return mapping[stationType] || 'komisar_trat';
    },

    /**
     * Return default role suggested by station id and station type.
     * @param {string} stationId
     * @param {string} stationType
     * @returns {string}
     */
    getDefaultRoleForStationSelection(stationId, stationType) {
        const normalized = String(stationId || '').trim().toUpperCase();
        if (normalized === 'VRZ' || normalized === 'VBRZ') {
            return 'vedouci';
        }
        if (normalized === 'ZVRZ' || normalized === 'ZVBRZ') {
            return 'zastupce';
        }
        return this.getDefaultRoleForStation(stationType);
    },

    /**
     * Return headers for admin API requests.
     * @param {Object} app
     * @returns {Object}
     */
    getAdminHeaders(app) {
        const token = app.user?.session_token;
        return token
            ? {
                'Content-Type': 'application/json',
                'X-Session-Token': token,
            }
            : {
                'Content-Type': 'application/json',
            };
    },

    /**
     * Execute setup/admin API request with shared auth handling.
     * @param {Object} app
     * @param {string} url
     * @param {Object} options
     * @returns {Promise<Response|null>}
     */
    async adminFetch(app, url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...this.getAdminHeaders(app),
                ...(options.headers || {}),
            },
        });

        if (response.status === 401) {
            window.Auth.handleUnauthorized();
            return null;
        }

        return response;
    },

    /**
     * Switch to dedicated setup screen for positions and map configuration.
     * @param {Object} app
     */
    openSetupScreen(app) {
        if (!app.isVedeniUser()) {
            return;
        }

        const appScreen = document.getElementById('app-screen');
        const setupScreen = document.getElementById('setup-screen');
        if (!appScreen || !setupScreen) {
            return;
        }

        appScreen.classList.remove('active');
        appScreen.classList.add('hidden');
        setupScreen.classList.remove('hidden');
        setupScreen.classList.add('active');
        app.currentScreen = 'setup';
        app.logUiAction('open_setup_screen', {});

        this.applyStoredMapConfig(app);

        Promise.all([
            this.loadAdminStations(app),
            this.loadAdminPeople(app),
            this.loadRzConfig(app),
        ]).catch((error) => {
            console.error('Setup load failed:', error);
            app.showToast('Setup data se nepodařilo načíst', 'error');
        });
    },

    /**
     * Load current RZ config for setup controls.
     * @param {Object} app
     * @param {boolean} announceRefresh
     * @returns {Promise<void>}
     */
    async loadRzConfig(app, announceRefresh = false) {
        if (!app.isVedeniUser()) {
            return;
        }

        const response = await this.adminFetch(app, 'http://localhost:8000/api/admin/rz-config');
        if (!response) {
            return;
        }

        if (!response.ok) {
            throw new Error('RZ config load failed');
        }

        const payload = await response.json();
        const input = document.getElementById('rz-name-input');
        if (input) {
            input.value = String(payload.rz_name || app.rzName || '');
        }

        app.applyRzName(payload.rz_name || app.rzName);
        app.applyCommunicationResetVersion(payload.communication_reset_version || 0, false);

        if (announceRefresh) {
            app.showToast('Konfigurace RZ načtena', 'success');
        }
    },

    /**
     * Save RZ name from setup controls and sync active clients.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async saveRzConfig(app) {
        if (!app.isVedeniUser()) {
            return;
        }

        const input = document.getElementById('rz-name-input');
        const rzName = String(input?.value || '').trim();
        if (!rzName) {
            app.showToast('Zadej název RZ', 'info');
            return;
        }

        const response = await this.adminFetch(app, 'http://localhost:8000/api/admin/rz-config', {
            method: 'POST',
            body: JSON.stringify({ rz_name: rzName }),
        });

        if (!response) {
            return;
        }

        if (!response.ok) {
            app.showToast('Název RZ se nepodařilo uložit', 'error');
            return;
        }

        const payload = await response.json();
        app.applyRzName(payload.rz_name || rzName);
        app.logUiAction('setup_rz_name_updated', {
            rz_name: payload.rz_name || rzName,
            notified_connections: Number(payload.notified_connections || 0),
        });
        app.showToast('Název RZ uložen', 'success');
    },

    /**
     * Request global communication history reset for next RZ.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async resetCommunicationHistory(app) {
        if (!app.isVedeniUser()) {
            return;
        }

        const confirmed = confirm(
            'Resetovat historii komunikace pro všechny klienty?\nPoužij před další RZ, aby se neukazovaly staré zprávy.',
        );
        if (!confirmed) {
            return;
        }

        const response = await this.adminFetch(app, 'http://localhost:8000/api/admin/reset-communication-history', {
            method: 'POST',
        });

        if (!response) {
            return;
        }

        if (!response.ok) {
            app.showToast('Reset komunikace se nepodařil', 'error');
            return;
        }

        const payload = await response.json();
        app.applyCommunicationResetVersion(payload.communication_reset_version || 0, true);
        app.logUiAction('setup_reset_communication_history', {
            communication_reset_version: Number(payload.communication_reset_version || 0),
            notified_connections: Number(payload.notified_connections || 0),
        });
        app.showToast('Historie komunikace resetována', 'success');
    },

    /**
     * Load people catalog for setup dropdown.
     * @param {Object} app
     * @param {boolean} announceRefresh
     * @returns {Promise<void>}
     */
    async loadAdminPeople(app, announceRefresh = false) {
        if (!app.isVedeniUser()) {
            return;
        }

        const response = await this.adminFetch(app, 'http://localhost:8000/api/admin/people');
        if (!response) {
            return;
        }

        if (!response.ok) {
            throw new Error('Admin people load failed');
        }

        const payload = await response.json();
        app.adminPeople = Array.isArray(payload.people) ? payload.people : [];
        this.renderAdminPeopleOptions(app);

        if (announceRefresh) {
            app.showToast('Katalog osob obnoven', 'success');
        }
    },

    /**
     * Render people dropdown options in setup assignment form.
     * @param {Object} app
     * @param {string} preferredName
     */
    renderAdminPeopleOptions(app, preferredName = '') {
        const select = document.getElementById('admin-person-catalog');
        if (!select) {
            return;
        }

        const normalizeName = (value) => String(value || '').trim().replace(/\s+/g, ' ').toLowerCase();
        const preferredKey = normalizeName(preferredName);
        const assignedNames = new Set(
            (app.adminStations || [])
                .map((station) => station?.current_user?.name)
                .filter(Boolean)
                .map(normalizeName)
                .filter((nameKey) => nameKey && nameKey !== preferredKey),
        );

        select.innerHTML = '<option value="">Ruční zadání</option>';
        app.adminPeople.forEach((person) => {
            const displayName = [person.first_name, person.last_name].filter(Boolean).join(' ').trim() || 'Neznámá osoba';
            if (assignedNames.has(normalizeName(displayName))) {
                return;
            }

            const option = document.createElement('option');
            option.value = displayName;
            const pieces = [displayName];
            if (person.phone) {
                pieces.push(person.phone);
            }
            if (person.email) {
                pieces.push(person.email);
            }
            if (person.group) {
                pieces.push(`SKUPINA: ${person.group}`);
            }
            option.textContent = pieces.join(' · ');
            select.appendChild(option);
        });

        if (preferredName && app.adminPeople.some((person) => [person.first_name, person.last_name].filter(Boolean).join(' ').trim() === preferredName)) {
            select.value = preferredName;
        } else {
            select.value = '';
        }
    },

    /**
     * Prefill assignment form from selected person in catalog.
     * @param {Object} app
     */
    applySelectedCatalogPerson(app) {
        const select = document.getElementById('admin-person-catalog');
        if (!select) {
            return;
        }

        const selectedName = select.value;
        if (!selectedName) {
            return;
        }

        const person = app.adminPeople.find((item) => [item.first_name, item.last_name].filter(Boolean).join(' ').trim() === selectedName);
        if (!person) {
            return;
        }

        const nameField = document.getElementById('admin-person-name');
        const phoneField = document.getElementById('admin-person-phone');
        const emailField = document.getElementById('admin-person-email');
        const addressField = document.getElementById('admin-person-address');
        const groupField = document.getElementById('admin-person-group');

        if (nameField) {
            nameField.value = [person.first_name, person.last_name].filter(Boolean).join(' ').trim();
        }
        if (phoneField) {
            phoneField.value = person.phone || '';
        }
        if (emailField) {
            emailField.value = person.email || '';
        }
        if (addressField) {
            addressField.value = person.address || '';
        }
        if (groupField) {
            groupField.value = person.group || '';
        }
    },

    /**
     * Return from setup screen back to live dashboard.
     * @param {Object} app
     */
    openDashboardScreen(app) {
        const appScreen = document.getElementById('app-screen');
        const setupScreen = document.getElementById('setup-screen');
        if (!appScreen || !setupScreen) {
            return;
        }

        setupScreen.classList.remove('active');
        setupScreen.classList.add('hidden');
        appScreen.classList.remove('hidden');
        appScreen.classList.add('active');
        app.currentScreen = 'dashboard';
        app.logUiAction('return_to_dashboard', {});

        if (window.MapModule?.map) {
            setTimeout(() => window.MapModule.map.invalidateSize(), 120);
        }
    },

    /**
     * Refresh station markers when map is initialized.
     * @returns {Promise<void>}
     */
    async refreshMapStationsSafe() {
        if (!window.MapModule?.isInitialized) {
            return;
        }

        try {
            await window.MapModule.refreshStationMarkers();
        } catch (error) {
            console.error('Map refresh after station update failed:', error);
        }
    },

    /**
     * Broadcast station directory update side effects to the app.
     * @param {Object} app
     * @param {string} stationId
     */
    notifyStationDirectoryChanged(app, stationId) {
        window.dispatchEvent(new CustomEvent('admin:station-directory-updated', {
            detail: { stationId },
        }));
        app.requestGateStatusRefresh();
    },

    /**
     * Load station directory for setup screen.
     * @param {Object} app
     * @param {boolean} announceRefresh
     * @returns {Promise<void>}
     */
    async loadAdminStations(app, announceRefresh = false) {
        if (!app.isVedeniUser()) {
            return;
        }

        const response = await this.adminFetch(app, 'http://localhost:8000/api/admin/stations');
        if (!response) {
            return;
        }

        if (!response.ok) {
            throw new Error('Admin station load failed');
        }

        const payload = await response.json();
        app.adminStations = Array.isArray(payload.stations) ? payload.stations : [];

        if (!app.selectedAdminStationId || !app.adminStations.some((station) => station.station_id === app.selectedAdminStationId)) {
            app.selectedAdminStationId = app.adminStations[0]?.station_id || null;
        }

        this.renderAdminStationList(app);
        this.renderSelectedAdminStation(app);

        if (announceRefresh) {
            app.showToast('Seznam pozic obnoven', 'success');
        }
    },

    /**
     * Render station selector list in setup screen.
     * @param {Object} app
     */
    renderAdminStationList(app) {
        const list = document.getElementById('station-admin-list');
        if (!list) {
            return;
        }

        if (!app.adminStations.length) {
            list.innerHTML = '<p class="station-admin-empty">Zatím nejsou dostupné žádné pozice.</p>';
            return;
        }

        list.innerHTML = app.adminStations.map((station) => {
            const active = station.station_id === app.selectedAdminStationId ? 'active' : '';
            const currentName = station.current_user?.name || 'Neobsazeno';
            const statusLabel = station.current_user ? 'Obsazeno' : 'Volné';
            return `
                <button type="button" class="station-admin-item ${active}" data-station-id="${app.escapeHtml(station.station_id)}">
                    <div class="station-admin-item-title">
                        <span>${app.escapeHtml(station.station_id)} · ${app.escapeHtml(station.station_name || station.station_id)}</span>
                        <span class="station-status-badge ${station.current_user ? 'active' : 'inactive'}">${statusLabel}</span>
                    </div>
                    <div class="station-admin-item-meta">PIN ${app.escapeHtml(station.pin_code)} · ${app.escapeHtml(station.station_type || 'other')}</div>
                    <div class="station-admin-item-user">${app.escapeHtml(currentName)}</div>
                </button>
            `;
        }).join('');

        list.querySelectorAll('.station-admin-item').forEach((button) => {
            button.addEventListener('click', () => {
                app.selectedAdminStationId = button.dataset.stationId || null;
                this.renderAdminStationList(app);
                this.renderSelectedAdminStation(app);
            });
        });
    },

    /**
     * Find selected station record in loaded setup directory.
     * @param {Object} app
     * @returns {Object|null}
     */
    getSelectedAdminStation(app) {
        if (!app.selectedAdminStationId) {
            return null;
        }
        return app.adminStations.find((station) => station.station_id === app.selectedAdminStationId) || null;
    },

    /**
     * Render detail, form and history for selected station.
     * @param {Object} app
     */
    renderSelectedAdminStation(app) {
        const detail = document.getElementById('station-admin-detail');
        const history = document.getElementById('station-admin-history');
        const form = document.getElementById('station-admin-form');
        const station = this.getSelectedAdminStation(app);

        if (!detail || !history || !form) {
            return;
        }

        if (!station) {
            detail.innerHTML = '<p class="station-admin-empty">Vyber pozici pro detail.</p>';
            history.innerHTML = '<p class="station-admin-empty">Historie se zobrazí po výběru pozice.</p>';
            form.classList.add('hidden');
            return;
        }

        const currentName = station.current_user?.name || 'Neobsazeno';
        const currentRole = station.current_user?.role || '-';
        const currentPhone = station.current_user?.phone || 'neuvedeno';
        const currentEmail = station.current_user?.email || 'neuvedeno';
        const currentAddress = station.current_user?.address || 'neuvedeno';
        const currentGroup = station.current_user?.group || 'neuvedeno';
        detail.innerHTML = `
            <h5>${app.escapeHtml(station.station_id)} · ${app.escapeHtml(station.station_name || station.station_id)}</h5>
            <div class="station-detail-grid">
                <div class="station-detail-meta"><strong>PIN:</strong> <span class="station-pin-badge">${app.escapeHtml(station.pin_code)}</span></div>
                <div class="station-detail-meta"><strong>Typ:</strong> ${app.escapeHtml(station.station_type || 'other')}</div>
                <div class="station-detail-meta"><strong>Kapacita:</strong> ${app.escapeHtml(String(station.capacity || 1))}</div>
                <div class="station-detail-meta"><strong>Obsazení:</strong> <span class="station-status-badge ${station.current_user ? 'active' : 'inactive'}">${station.current_user ? 'aktivní' : 'volná'}</span></div>
                <div class="station-detail-meta"><strong>Osoba:</strong> ${app.escapeHtml(currentName)}</div>
                <div class="station-detail-meta"><strong>Role:</strong> ${app.escapeHtml(currentRole)}</div>
                <div class="station-detail-meta"><strong>Telefon:</strong> ${app.escapeHtml(currentPhone)}</div>
                <div class="station-detail-meta"><strong>E-mail:</strong> ${app.escapeHtml(currentEmail)}</div>
                <div class="station-detail-meta"><strong>Bydliště:</strong> ${app.escapeHtml(currentAddress)}</div>
                <div class="station-detail-meta"><strong>SKUPINA:</strong> ${app.escapeHtml(currentGroup)}</div>
                <div class="station-detail-meta"><strong>Poznámka:</strong> ${app.escapeHtml(station.description || '-')}</div>
            </div>
        `;

        document.getElementById('admin-station-id').value = station.station_id || '';
        document.getElementById('admin-person-name').value = station.current_user?.name || '';
        document.getElementById('admin-person-role').value = station.current_user?.role
            || this.getDefaultRoleForStationSelection(station.station_id, station.station_type);
        document.getElementById('admin-person-phone').value = station.current_user?.phone || '';
        document.getElementById('admin-person-email').value = station.current_user?.email || '';
        document.getElementById('admin-person-address').value = station.current_user?.address || '';
        document.getElementById('admin-person-group').value = station.current_user?.group || '';
        document.getElementById('admin-person-note').value = '';
        this.renderAdminPeopleOptions(app, station.current_user?.name || '');
        form.classList.remove('hidden');

        this.renderAdminHistory(app, station.assigned_users || []);
        this.loadSelectedSetupStationCoordinate(app);
    },

    /**
     * Apply custom track source from setup form.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async applySetupTrackSource(app) {
        const trackInput = document.getElementById('map-track-path');
        if (!trackInput || !window.MapModule) {
            return;
        }

        const trackGeoJsonUrl = String(trackInput.value || '').trim();
        window.MapModule.setTrackSource(trackGeoJsonUrl);

        const stored = this.readStoredMapConfig();
        this.storeMapConfig({
            trackGeoJsonUrl,
            stationCoordinates: stored.stationCoordinates || {},
        });
        app.logUiAction('setup_track_source_updated', {
            track_geojson_url: trackGeoJsonUrl || 'default',
        });

        if (window.MapModule.isInitialized) {
            await window.MapModule.refreshTrack();
        }

        app.showToast('Podklad trati aktualizován', 'success');
    },

    /**
     * Load selected station coordinates into setup form fields.
     * @param {Object} app
     */
    loadSelectedSetupStationCoordinate(app) {
        const latInput = document.getElementById('map-station-lat');
        const lonInput = document.getElementById('map-station-lon');
        if (!latInput || !lonInput) {
            return;
        }

        const stationId = app.selectedAdminStationId;
        if (!stationId || !window.MapModule) {
            latInput.value = '';
            lonInput.value = '';
            return;
        }

        const coordinates = window.MapModule.stationCoordinates[stationId];
        if (!Array.isArray(coordinates) || coordinates.length !== 2) {
            latInput.value = '';
            lonInput.value = '';
            return;
        }

        latInput.value = String(coordinates[0]);
        lonInput.value = String(coordinates[1]);
    },

    /**
     * Save selected station coordinates from setup form.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async saveSelectedSetupStationCoordinate(app) {
        const stationId = app.selectedAdminStationId;
        if (!stationId || !window.MapModule) {
            app.showToast('Nejprve vyber pozici ze seznamu', 'info');
            return;
        }

        const latInput = document.getElementById('map-station-lat');
        const lonInput = document.getElementById('map-station-lon');
        const latitude = Number(latInput?.value);
        const longitude = Number(lonInput?.value);

        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
            app.showToast('Zadej platné souřadnice lat/lon', 'error');
            return;
        }

        if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
            app.showToast('Souřadnice jsou mimo povolený rozsah', 'error');
            return;
        }

        const mergedCoordinates = {
            ...window.MapModule.stationCoordinates,
            [stationId]: [latitude, longitude],
        };

        window.MapModule.setStationCoordinates(mergedCoordinates);

        const stored = this.readStoredMapConfig();
        this.storeMapConfig({
            trackGeoJsonUrl: String(window.MapModule.config.trackGeoJsonUrl || stored.trackGeoJsonUrl || ''),
            stationCoordinates: mergedCoordinates,
        });
        app.logUiAction('setup_station_coordinates_saved', {
            station_id: stationId,
            latitude,
            longitude,
        });

        if (window.MapModule.isInitialized) {
            await window.MapModule.refreshStationMarkers();
        }

        app.showToast(`Souřadnice ${stationId} uloženy`, 'success');
    },

    /**
     * Reset setup map configuration to defaults.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async resetSetupMapConfig(app) {
        if (!window.MapModule) {
            return;
        }

        localStorage.removeItem(this.getMapConfigStorageKey());
        window.MapModule.resetRuntimeConfig();

        this.applyStoredMapConfig(app);
        app.logUiAction('setup_map_config_reset', {});

        if (window.MapModule.isInitialized) {
            await window.MapModule.refreshTrack();
            await window.MapModule.refreshStationMarkers();
        }

        app.showToast('Map config vrácen na výchozí hodnoty', 'success');
    },

    /**
     * Render assignment history for selected station.
     * @param {Object} app
     * @param {Array<Object>} entries
     */
    renderAdminHistory(app, entries) {
        const history = document.getElementById('station-admin-history');
        if (!history) {
            return;
        }

        if (!entries.length) {
            history.innerHTML = '<p class="station-admin-empty">Pro vybranou pozici zatím není historie.</p>';
            return;
        }

        history.innerHTML = entries.slice().reverse().map((entry) => {
            const stateClass = entry.is_active ? 'active' : '';
            const stateLabel = entry.is_active ? 'Aktuální' : 'Historie';
            const until = entry.assigned_until ? `do ${app.formatDateTime(entry.assigned_until)}` : 'dosud';
            return `
                <div class="station-history-item ${stateClass}">
                    <strong>${app.escapeHtml(entry.name || 'Neznámý')}</strong> · ${app.escapeHtml(entry.role || '-')}
                    <div>${stateLabel}: od ${app.formatDateTime(entry.assigned_at)} ${until}</div>
                    <div>Telefon: ${app.escapeHtml(entry.phone || 'neuvedeno')}</div>
                    <div>E-mail: ${app.escapeHtml(entry.email || 'neuvedeno')}</div>
                    <div>Bydliště: ${app.escapeHtml(entry.address || 'neuvedeno')}</div>
                    <div>SKUPINA: ${app.escapeHtml(entry.group || 'neuvedeno')}</div>
                    <div>Poznámka: ${app.escapeHtml(entry.note || '-')}</div>
                </div>
            `;
        }).join('');
    },

    /**
     * Submit assign/reassign form for selected station.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async submitAdminStationAssignment(app) {
        const stationId = document.getElementById('admin-station-id')?.value;
        const name = document.getElementById('admin-person-name')?.value.trim();
        const role = document.getElementById('admin-person-role')?.value;
        const phone = document.getElementById('admin-person-phone')?.value.trim() || null;
        const email = document.getElementById('admin-person-email')?.value.trim() || null;
        const address = document.getElementById('admin-person-address')?.value.trim() || null;
        const group = document.getElementById('admin-person-group')?.value.trim() || null;
        const note = document.getElementById('admin-person-note')?.value.trim() || null;

        if (!stationId || !name || !role) {
            app.showToast('Vyplň stanici, jméno a roli', 'info');
            return;
        }

        if (this.isVedeniStation(stationId) && role !== 'vedouci' && role !== 'zastupce') {
            app.showToast('Pozice VRZ/ZVRZ/VBRZ/ZVBRZ musí mít roli vedení RZ', 'error');
            return;
        }

        const response = await this.adminFetch(
            app,
            `http://localhost:8000/api/admin/station/${encodeURIComponent(stationId)}/reassign-user`,
            {
                method: 'POST',
                body: JSON.stringify({ name, role, phone, email, address, group, note }),
            },
        );

        if (!response) {
            return;
        }

        if (!response.ok) {
            app.showToast('Přiřazení se nepodařilo uložit', 'error');
            return;
        }

        await this.loadAdminStations(app);
        await this.refreshMapStationsSafe();
        this.notifyStationDirectoryChanged(app, stationId);
        app.logUiAction('setup_assignment_saved', {
            station_id: stationId,
            name,
            role,
            phone,
            email,
            address,
            group,
        });
        app.showToast(`Pozice ${stationId} aktualizována`, 'success');
    },

    /**
     * Release currently assigned person from selected station.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async releaseAdminStation(app) {
        const stationId = document.getElementById('admin-station-id')?.value;
        const station = this.getSelectedAdminStation(app);
        const note = document.getElementById('admin-person-note')?.value.trim() || 'Uvolnění pozice';

        if (!stationId || !station?.current_user) {
            app.showToast('Vybraná pozice už je volná', 'info');
            return;
        }

        const confirmed = confirm(`Uvolnit pozici ${stationId} (${station.current_user.name})?`);
        if (!confirmed) {
            return;
        }

        const response = await this.adminFetch(
            app,
            `http://localhost:8000/api/admin/station/${encodeURIComponent(stationId)}/release-user`,
            {
                method: 'POST',
                body: JSON.stringify({ note }),
            },
        );

        if (!response) {
            return;
        }

        if (!response.ok) {
            app.showToast('Pozici se nepodařilo uvolnit', 'error');
            return;
        }

        await this.loadAdminStations(app);
        await this.refreshMapStationsSafe();
        this.notifyStationDirectoryChanged(app, stationId);
        app.logUiAction('setup_assignment_released', {
            station_id: stationId,
            note,
        });
        app.showToast(`Pozice ${stationId} uvolněna`, 'success');
    },

    /**
     * Generate missing station PINs from map station templates in bulk.
     *
     * Args:
     *     app: Main app instance.
     *
     * Returns:
     *     Promise that resolves when refresh is complete.
     */
    async bulkGeneratePinsFromMap(app) {
        if (!app.isVedeniUser()) {
            return;
        }

        const regenerateExisting = Boolean(
            document.getElementById('bulk-regenerate-existing-pins')?.checked,
        );

        const confirmText = [
            'Vygenerovat PINy pro pozice z mapových podkladů?',
            regenerateExisting
                ? 'Pozor: existující PINy budou také regenerované.'
                : 'Existující pozice zůstanou beze změny.',
        ].join('\n');

        if (!confirm(confirmText)) {
            return;
        }

        const response = await this.adminFetch(app, 'http://localhost:8000/api/admin/station/bulk-generate-pins', {
            method: 'POST',
            body: JSON.stringify({ regenerate_existing: regenerateExisting }),
        });

        if (!response) {
            return;
        }

        if (!response.ok) {
            app.showToast('Hromadné generování PINů selhalo', 'error');
            return;
        }

        const payload = await response.json();
        const summary = payload.summary || {};
        await this.loadAdminStations(app);
        app.requestGateStatusRefresh();
        app.logUiAction('setup_bulk_generate_pins', {
            created: Number(summary.created || 0),
            regenerated: Number(summary.regenerated || 0),
            skipped: Number(summary.skipped || 0),
            templates_total: Number(summary.templates_total || 0),
            regenerate_existing: regenerateExisting,
        });
        this.showBulkPinSummaryModal(summary, regenerateExisting);
    },

    /**
     * Show summary modal for bulk PIN generation outcome.
     *
     * Args:
     *     summary: API summary object.
     *     regenerateExisting: Whether existing PINs were included.
     */
    showBulkPinSummaryModal(summary, regenerateExisting) {
        const modal = document.getElementById('pin-bulk-summary-modal');
        const content = document.getElementById('pin-bulk-summary-content');
        if (!modal || !content) {
            return;
        }

        const templatesTotal = Number(summary.templates_total || 0);
        const created = Number(summary.created || 0);
        const regenerated = Number(summary.regenerated || 0);
        const skipped = Number(summary.skipped || 0);
        const mode = regenerateExisting ? 'včetně regenerace existujících PINů' : 'pouze nové pozice';

        content.innerHTML = [
            `<p><strong>Režim:</strong> ${mode}</p>`,
            `<p><strong>Mapové šablony:</strong> ${templatesTotal}</p>`,
            `<p><strong>Vytvořeno:</strong> ${created}</p>`,
            `<p><strong>Regenerováno:</strong> ${regenerated}</p>`,
            `<p><strong>Přeskočeno:</strong> ${skipped}</p>`,
        ].join('');

        modal.classList.remove('hidden');
    },

    /**
     * Hide bulk PIN summary modal.
     */
    hideBulkPinSummaryModal() {
        const modal = document.getElementById('pin-bulk-summary-modal');
        if (!modal) {
            return;
        }
        modal.classList.add('hidden');
    },

    /**
     * Regenerate PIN for currently selected station.
     *
     * Args:
     *     app: Main app instance.
     *
     * Returns:
     *     Promise that resolves when station list is refreshed.
     */
    async regenerateSelectedStationPin(app) {
        const station = this.getSelectedAdminStation(app);
        const stationId = station?.station_id;
        if (!stationId) {
            app.showToast('Nejprve vyber pozici', 'info');
            return;
        }

        const confirmed = confirm(
            `Regenerovat PIN pro pozici ${stationId}?\nStarý PIN bude okamžitě neplatný.`,
        );
        if (!confirmed) {
            return;
        }

        const response = await this.adminFetch(
            app,
            `http://localhost:8000/api/admin/station/${encodeURIComponent(stationId)}/regenerate-pin`,
            {
                method: 'POST',
            },
        );

        if (!response) {
            return;
        }

        if (!response.ok) {
            app.showToast('Regenerace PINu selhala', 'error');
            return;
        }

        const payload = await response.json();
        await this.loadAdminStations(app);
        app.requestGateStatusRefresh();
        app.logUiAction('setup_regenerate_station_pin', {
            station_id: stationId,
            old_pin_code: payload.old_pin_code || null,
            new_pin_code: payload.station?.pin_code || null,
        });
        app.showToast(`PIN pro ${stationId} byl regenerován`, 'success');
    },
};

window.SetupAdminModule = SetupAdminModule;