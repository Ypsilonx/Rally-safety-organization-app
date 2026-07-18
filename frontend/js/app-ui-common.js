/**
 * Rally Safety App - Shared UI/common helpers.
 * Handles formatting, toast notifications, auth fallback and persisted UI state.
 */

const AppUiCommonModule = {
    /**
     * Handle connection status change.
     * @param {Object} app
     * @param {string} status
     */
    handleStatusChange(app, status) {
        console.log('Status changed:', status);

        const indicator = document.getElementById('connection-status');
        if (!indicator) {
            return;
        }

        indicator.className = 'status-indicator';

        switch (status) {
            case 'online':
                indicator.classList.add('online');
                indicator.title = 'Připojeno';
                app.showToast('Připojeno k serveru', 'success');
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
                app.showToast('Spojení se serverem selhalo', 'error');
                app.scheduleReauthentication('Spojení selhalo. Přihlaste se znovu.');
                break;
            case 'auth_failed':
                indicator.classList.add('offline');
                indicator.title = 'Neplatné přihlášení';
                app.showToast('Relace vypršela. Přihlaste se znovu.', 'error');
                app.scheduleReauthentication('Relace vypršela. Přihlaste se znovu.');
                break;
        }
    },

    /**
     * Redirect to login after communication/auth failures.
     * @param {Object} app
     * @param {string} reason
     */
    scheduleReauthentication(app, reason) {
        if (app.reauthScheduled) {
            return;
        }

        app.reauthScheduled = true;
        setTimeout(() => {
            if (reason) {
                console.warn(reason);
            }
            window.Auth.logout();
        }, 1200);
    },

    /**
     * Handle generic app error.
     * @param {Object} app
     * @param {Error} error
     */
    handleError(app, error) {
        console.error('App error:', error);
        app.showToast('Chyba komunikace', 'error');
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
     * @param {Object} app
     */
    loadRzState(app) {
        const saved = localStorage.getItem(this.getRzStateStorageKey());
        if (saved === 'running' || saved === 'paused' || saved === 'stopped') {
            app.rzState = saved;
            return;
        }
        app.rzState = 'running';
    },

    /**
     * Persist and apply RZ operation state.
     * @param {Object} app
     * @param {'running'|'paused'|'stopped'} state
     */
    setRzState(app, state) {
        app.rzState = state;
        localStorage.setItem(this.getRzStateStorageKey(), state);
        app.applyRzStateUi();
    },

    /**
     * Get local storage key for per-user persisted UI state.
     * @param {Object} app
     * @param {string} bucket
     * @returns {string}
     */
    getStateStorageKey(app, bucket) {
        return `rally_state_${app.user?.user_id || 'guest'}_${bucket}`;
    },

    /**
     * Load persisted state arrays for current user.
     * @param {Object} app
     */
    loadPersistedState(app) {
        ['chat', 'info', 'incidents'].forEach((bucket) => {
            try {
                const raw = localStorage.getItem(this.getStateStorageKey(app, bucket));
                const parsed = raw ? JSON.parse(raw) : [];
                app.persistedState[bucket] = Array.isArray(parsed) ? parsed : [];
            } catch (_error) {
                app.persistedState[bucket] = [];
            }
        });
    },

    /**
     * Persist one UI record into local storage with bounded history.
     * @param {Object} app
     * @param {'chat'|'info'|'incidents'} bucket
     * @param {Object} payload
     */
    persistStateItem(app, bucket, payload) {
        if (!app.persistedState[bucket]) {
            return;
        }

        const maxSize = app.stateStorageLimits[bucket] || 100;
        app.persistedState[bucket].push(payload);
        if (app.persistedState[bucket].length > maxSize) {
            app.persistedState[bucket] = app.persistedState[bucket].slice(-maxSize);
        }

        localStorage.setItem(
            this.getStateStorageKey(app, bucket),
            JSON.stringify(app.persistedState[bucket]),
        );
    },

    /**
     * Restore persisted chat/info/incident messages into current UI.
     * @param {Object} app
     */
    restorePersistedUiState(app) {
        app.persistedState.chat.forEach((message) => app.displayMessage(message, false));
        app.persistedState.info.forEach((message) => app.displayInfoMessage(message, false));
        app.persistedState.incidents.forEach((message) => app.addIncidentWarning(message, false));
    },

    /**
     * Set vedeni contact link for komisar quick actions.
     * @param {Object} app
     */
    updateVedeniContact(app) {
        const list = document.getElementById('leadership-contacts-list');
        if (!list) {
            return;
        }

        const fallbackContacts = [
            {
                station_id: 'VRZ',
                label: 'Vedoucí RZ',
                phone: app.user?.vedeni_phone || '+420777123456',
            },
            {
                station_id: 'ZVRZ',
                label: 'Zástupce vedoucího RZ',
                phone: '+420777123457',
            },
            {
                station_id: 'VBRZ',
                label: 'Vedoucí bezpečnosti RZ',
                phone: '+420777123458',
            },
            {
                station_id: 'ZVBRZ',
                label: 'Zástupce vedoucího bezpečnosti RZ',
                phone: '+420777123459',
            },
        ];

        const contacts = Array.isArray(app.user?.leadership_contacts) && app.user.leadership_contacts.length
            ? app.user.leadership_contacts
            : fallbackContacts;

        list.innerHTML = '';
        contacts.forEach((contact) => {
            const row = document.createElement('div');
            row.className = 'leadership-contact-row';

            const label = document.createElement('span');
            label.className = 'leadership-contact-label';
            label.textContent = `${contact.label || contact.station_id || 'Vedení'}:`;

            const link = document.createElement('a');
            const phone = String(contact.phone || 'neuvedeno').trim();
            link.href = phone.startsWith('+') || /^\d/.test(phone) ? `tel:${phone}` : '#';
            link.textContent = phone;

            row.appendChild(label);
            row.appendChild(link);
            list.appendChild(row);
        });
    },

    /**
     * Handle logout.
     */
    handleLogout() {
        if (confirm('Opravdu se chcete odhlásit?')) {
            window.Auth.logout();
        }
    },

    /**
     * Show toast notification.
     * @param {string} message
     * @param {string} type
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) {
            return;
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /**
     * Format timestamp to HH:MM.
     * @param {string} isoString
     * @returns {string}
     */
    formatTime(isoString) {
        if (!isoString) return '';

        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString('cs-CZ', {
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return '';
        }
    },

    /**
     * Format timestamp to locale date and time.
     * @param {string} isoString
     * @returns {string}
     */
    formatDateTime(isoString) {
        if (!isoString) return '-';

        try {
            const date = new Date(isoString);
            return date.toLocaleString('cs-CZ', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return '-';
        }
    },

    /**
     * Escape HTML to prevent XSS.
     * @param {string} text
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

window.AppUiCommonModule = AppUiCommonModule;