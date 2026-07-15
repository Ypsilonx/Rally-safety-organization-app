/**
 * Rally Safety App - Incident and broadcast operations.
 */

const AppOperationsIncidentsModule = {
    /**
     * Send broadcast message (admin only).
     * @param {Object} app
     */
    async sendBroadcast(app) {
        const content = prompt('Hromadná zpráva všem stanicím:');
        if (!content || !content.trim()) return;

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

        const broadcastMessage = {
            message_id: `broadcast_${Date.now()}`,
            sender: {
                user_id: app.user.user_id,
                name: app.user.name,
                role: app.user.role,
            },
            message_type: 'broadcast',
            content: `📢 HROMADNÁ ZPRÁVA VŠEM\n\n${content.trim()}\n\n→ Odesláno ${onlineCount} online stanicím`,
            created_at: new Date().toISOString(),
        };

        app.displayMessage(broadcastMessage);
        window.wsClient.sendSystemMessage('broadcast', content.trim());
        app.showToast(`Hromadná zpráva odeslána ${onlineCount} stanicím`, 'success');
    },

    /**
     * Send predefined operational alert from vedeni panel.
     * @param {Object} app
     * @param {string} alertKey
     */
    sendAlertPreset(app, alertKey) {
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
                user_id: app.user.user_id,
                name: app.user.name,
                role: app.user.role,
                station_id: app.user.station_id || null,
            },
            ...payload,
        };

        app.displayMessage(ownMessage);
        app.displayInfoMessage(ownMessage);
        app.applyRzStateFromCommand(alertKey);
        window.wsClient.sendMessage(payload);
        app.showToast('Předdefinované hlášení odesláno', 'success');
    },

    /**
     * Handle quick action button click.
     * @param {Object} app
     * @param {string} action
     */
    handleQuickAction(app, action) {
        if (action === 'ready') {
            app.incidentGateActive = false;
            if (app.user.station_id) {
                window.dispatchEvent(new CustomEvent('station:clear-alert', {
                    detail: { stationId: app.user.station_id },
                }));
            }
            window.wsClient.sendMessage({
                message_type: 'status_update',
                readiness_state: 'ready',
                content: '✅ Stanice připravena',
                created_at: new Date().toISOString(),
            });
            app.showToast('Stav odeslán', 'success');
            return;
        }

        if (action === 'issue') {
            const detail = prompt('Popiš stručně problém na stanici:');
            if (!detail || !detail.trim()) {
                app.showToast('Incident nebyl odeslán', 'info');
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
                    user_id: app.user.user_id,
                    name: app.user.name,
                    role: app.user.role,
                    station_id: app.user.station_id || null,
                },
                ...payload,
            };

            app.displayMessage(ownMessage);
            app.displayInfoMessage(ownMessage);
            app.applyMarkerAlertFromMessage(ownMessage);
            window.wsClient.sendMessage(payload);
            app.incidentGateActive = true;
            app.showToast('Incident odeslán vedení', 'error');
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
                    user_id: app.user.user_id,
                    name: app.user.name,
                    role: app.user.role,
                    station_id: app.user.station_id || null,
                },
                ...payload,
            };

            app.displayMessage(ownMessage);
            app.displayInfoMessage(ownMessage);
            app.applyMarkerAlertFromMessage(ownMessage);
            window.wsClient.sendMessage(payload);
            app.incidentGateActive = true;
            app.showToast('Akutní incident odeslán vedení', 'error');
        }
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
     * @param {Object} app
     * @param {Object} message
     * @param {boolean} persist
     */
    addIncidentWarning(app, message, persist = true) {
        const feed = document.getElementById('incident-feed');
        if (!feed) {
            return;
        }

        const empty = feed.querySelector('.incident-empty');
        if (empty) {
            empty.remove();
        }

        const senderName = app.escapeHtml(message.sender?.name || 'Neznámý');
        const senderPhone = app.escapeHtml(message.sender?.phone || 'neuvedeno');
        const text = app.escapeHtml(message.content || 'Bez obsahu');

        const item = document.createElement('div');
        feed.querySelectorAll('.incident-item.latest').forEach((existing) => {
            existing.classList.remove('latest');
        });

        item.className = 'incident-item latest';
        item.innerHTML = `
            <strong>${senderName}</strong> (${app.formatTime(message.created_at)})<br>
            ${text}<br>
            Kontakt: <a href="tel:${senderPhone}">${senderPhone}</a>
        `;

        feed.prepend(item);
        while (feed.children.length > 20) {
            feed.removeChild(feed.lastChild);
        }

        if (persist) {
            app.persistStateItem('incidents', message);
        }
    },
};

window.AppOperationsIncidentsModule = AppOperationsIncidentsModule;