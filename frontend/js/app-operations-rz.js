/**
 * Rally Safety App - RZ operation state and gate logic.
 */

const AppOperationsRzModule = {
    /**
     * Toggle admin panel collapse.
     */
    toggleAdminPanel() {
        const header = document.querySelector('.panel-header');
        const content = document.querySelector('.panel-content');
        if (!header || !content) {
            return;
        }

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
     * Update top badge + map border according to current RZ state.
     * @param {Object} app
     */
    applyRzStateUi(app) {
        const badge = document.getElementById('rz-live-status');
        const mapPanel = document.querySelector('.map-panel');

        if (badge) {
            badge.classList.remove('running', 'paused', 'stopped');
            badge.classList.add(app.rzState);

            if (app.rzState === 'paused') {
                badge.textContent = 'RZ: Pozastavena';
            } else if (app.rzState === 'stopped') {
                badge.textContent = 'RZ: Zastavena';
            } else {
                badge.textContent = 'RZ: V provozu';
            }
        }

        if (mapPanel) {
            const warning = app.rzState === 'paused' || app.rzState === 'stopped';
            mapPanel.classList.toggle('rz-warning', warning);
        }
    },

    /**
     * Apply RZ state based on operation command.
     * @param {Object} app
     * @param {string} command
     */
    applyRzStateFromCommand(app, command) {
        if (command === 'rz_stop') {
            app.setRzState('stopped');
        } else if (command === 'rz_hold') {
            app.setRzState('paused');
        } else if (command === 'rz_resume') {
            app.setRzState('running');
        }
    },

    /**
     * Inspect message payload and update RZ state when command/state text indicates change.
     * @param {Object} app
     * @param {Object} message
     */
    applyRzStateFromMessage(app, message) {
        if (!message) {
            return;
        }

        if (message.operation_command) {
            app.applyRzStateFromCommand(message.operation_command);
            return;
        }

        const text = String(message.content || '').toLowerCase();
        if (text.includes('rz zastavena')) {
            app.setRzState('stopped');
        } else if (text.includes('rz pozastavena')) {
            app.setRzState('paused');
        } else if (text.includes('rz opět v provozu')) {
            app.setRzState('running');
        }
    },

    /**
     * Refresh readiness gate state from backend for admin dashboard.
     * @param {Object} app
     */
    startGateStatusRefresh(app) {
        if (!app.isVedeniUser()) {
            return;
        }

        if (app.gateRefreshTimer) {
            clearInterval(app.gateRefreshTimer);
            app.gateRefreshTimer = null;
        }

        app.refreshGateStatus().catch((error) => {
            console.error('Gate status refresh failed:', error);
        });

        app.gateRefreshTimer = setInterval(() => {
            app.refreshGateStatus().catch((error) => {
                console.error('Gate status refresh failed:', error);
            });
        }, 12000);
    },

    /**
     * Queue immediate gate refresh, while collapsing burst updates.
     * @param {Object} app
     */
    requestGateStatusRefresh(app) {
        if (!app.isVedeniUser()) {
            return;
        }

        if (app.gateRefreshQueued) {
            return;
        }

        app.gateRefreshQueued = true;
        setTimeout(() => {
            app.gateRefreshQueued = false;
            app.refreshGateStatus().catch((error) => {
                console.error('Gate status refresh failed:', error);
            });
        }, 250);
    },

    /**
     * Load readiness snapshot and update gate indicator in admin board.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async refreshGateStatus(app) {
        const gateLabel = document.getElementById('incident-gate-status');
        const missingLabel = document.getElementById('incident-gate-missing');
        if (!gateLabel || !missingLabel || !app.isVedeniUser()) {
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
        app.incidentGateActive = incidentActive;
        app.gateMissingStations = missingStations;

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
     * @param {Object} app
     * @returns {boolean}
     */
    isVedeniUser(app) {
        return app.user?.role === 'vedouci' || app.user?.role === 'zastupce';
    },
};

window.AppOperationsRzModule = AppOperationsRzModule;