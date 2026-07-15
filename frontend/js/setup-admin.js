/**
 * Rally Safety App - Setup/Admin screen module.
 * Handles pre-start configuration of positions, assignments and related UI.
 */

const SetupAdminModule = {
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

        Promise.all([
            app.loadAdminStations(),
            app.loadAdminPeople(),
        ]).catch((error) => {
            console.error('Setup load failed:', error);
            app.showToast('Setup data se nepodařilo načíst', 'error');
        });
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

        const response = await fetch('http://localhost:8000/api/admin/people', {
            headers: this.getAdminHeaders(app),
        });

        if (response.status === 401) {
            window.Auth.handleUnauthorized();
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

        select.innerHTML = '<option value="">Ruční zadání</option>';
        app.adminPeople.forEach((person) => {
            const option = document.createElement('option');
            option.value = person.name || '';
            option.textContent = person.phone
                ? `${person.name} · ${person.phone}`
                : (person.name || 'Neznámá osoba');
            select.appendChild(option);
        });

        if (preferredName && app.adminPeople.some((person) => person.name === preferredName)) {
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

        const person = app.adminPeople.find((item) => item.name === selectedName);
        if (!person) {
            return;
        }

        const nameField = document.getElementById('admin-person-name');
        const phoneField = document.getElementById('admin-person-phone');

        if (nameField) {
            nameField.value = person.name || '';
        }
        if (phoneField) {
            phoneField.value = person.phone || '';
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

        if (window.MapModule?.map) {
            setTimeout(() => window.MapModule.map.invalidateSize(), 120);
        }
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

        const response = await fetch('http://localhost:8000/api/admin/stations', {
            headers: this.getAdminHeaders(app),
        });

        if (response.status === 401) {
            window.Auth.handleUnauthorized();
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
                <div class="station-detail-meta"><strong>Poznámka:</strong> ${app.escapeHtml(station.description || '-')}</div>
            </div>
        `;

        document.getElementById('admin-station-id').value = station.station_id || '';
        document.getElementById('admin-person-name').value = station.current_user?.name || '';
        document.getElementById('admin-person-role').value = station.current_user?.role
            || this.getDefaultRoleForStation(station.station_type);
        document.getElementById('admin-person-phone').value = station.current_user?.phone || '';
        document.getElementById('admin-person-note').value = '';
        this.renderAdminPeopleOptions(app, station.current_user?.name || '');
        form.classList.remove('hidden');

        this.renderAdminHistory(app, station.assigned_users || []);
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
        const note = document.getElementById('admin-person-note')?.value.trim() || null;

        if (!stationId || !name || !role) {
            app.showToast('Vyplň stanici, jméno a roli', 'info');
            return;
        }

        const response = await fetch(`http://localhost:8000/api/admin/station/${encodeURIComponent(stationId)}/reassign-user`, {
            method: 'POST',
            headers: this.getAdminHeaders(app),
            body: JSON.stringify({ name, role, phone, note }),
        });

        if (response.status === 401) {
            window.Auth.handleUnauthorized();
            return;
        }

        if (!response.ok) {
            app.showToast('Přiřazení se nepodařilo uložit', 'error');
            return;
        }

        await this.loadAdminStations(app);
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

        const response = await fetch(`http://localhost:8000/api/admin/station/${encodeURIComponent(stationId)}/release-user`, {
            method: 'POST',
            headers: this.getAdminHeaders(app),
            body: JSON.stringify({ note }),
        });

        if (response.status === 401) {
            window.Auth.handleUnauthorized();
            return;
        }

        if (!response.ok) {
            app.showToast('Pozici se nepodařilo uvolnit', 'error');
            return;
        }

        await this.loadAdminStations(app);
        app.showToast(`Pozice ${stationId} uvolněna`, 'success');
    },
};

window.SetupAdminModule = SetupAdminModule;