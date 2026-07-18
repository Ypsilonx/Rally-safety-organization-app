/**
 * Rally Safety App - Messaging and communication UI module.
 * Handles chat rendering, incoming messages and communication drawer behavior.
 */

const AppMessagingModule = {
    /**
     * Send chat message.
     * @param {Object} app
     */
    sendChatMessage(app) {
        const input = document.getElementById('message-input');
        const content = input?.value.trim();

        if (!input || !content) return;

        const ownMessage = {
            message_id: `temp_${Date.now()}`,
            sender: {
                user_id: app.user.user_id,
                name: app.user.name,
                role: app.user.role,
                station_id: app.user.station_id || null,
            },
            message_type: 'chat',
            content,
            created_at: new Date().toISOString(),
        };

        app.displayMessage(ownMessage);
        window.wsClient.sendChatMessage(content);

        input.value = '';
        app.hideTagSuggestions();
        input.focus();
    },

    /**
     * Handle incoming WebSocket message.
     * @param {Object} app
     * @param {Object} message
     */
    handleMessage(app, message) {
        console.log('Handling message:', message);

        const normalized = app.normalizeIncomingMessage(message);
        if (!normalized) {
            return;
        }

        if (normalized?.type === 'error') {
            const missing = Array.isArray(normalized?.details?.missing_stations)
                ? normalized.details.missing_stations.join(', ')
                : '';
            const detailText = missing ? ` Chybí: ${missing}` : '';
            app.showToast(`${normalized.message || 'Chyba komunikace'}${detailText}`, 'error');
            if (missing) {
                app.requestGateStatusRefresh();
            }
            return;
        }

        app.applyRzStateFromMessage(normalized);
        app.applyMarkerAlertFromMessage(normalized);
        if (normalized.rz_name) {
            app.applyRzName(normalized.rz_name);
        }
        if (normalized.communication_reset_version !== undefined) {
            app.applyCommunicationResetVersion(normalized.communication_reset_version, true);
        }
        app.registerSenderForTagging(normalized);
        app.displayMessage(normalized);

        if (app.isInfoChannelMessage(normalized)) {
            app.displayInfoMessage(normalized);
        }

        if (app.isVedeniUser() && app.isIncidentForDashboard(normalized)) {
            app.addIncidentWarning(normalized);
        }

        if (normalized.message_type === 'incident' || normalized.message_type === 'broadcast') {
            app.showToast(normalized.content, 'error');
        }

        if (normalized.operation_command || normalized.readiness_state || normalized.message_type === 'incident') {
            app.requestGateStatusRefresh();
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
                detail: { stationId },
            }));
            return;
        }

        if (message.readiness_state === 'ready') {
            window.dispatchEvent(new CustomEvent('station:clear-alert', {
                detail: { stationId },
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
     * Display message in chat area.
     * @param {Object} app
     * @param {Object} message
     * @param {boolean} persist
     */
    displayMessage(app, message, persist = true) {
        const messagesArea = document.getElementById('messages');
        if (!messagesArea) {
            return;
        }

        const welcomeMsg = messagesArea.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        const messageEl = document.createElement('div');
        messageEl.className = 'message';

        const isOwnMessage = message.sender?.user_id === app.user.user_id;
        if (isOwnMessage) {
            messageEl.classList.add('own');
        }

        if (message.message_type === 'system' || message.message_type === 'broadcast') {
            messageEl.classList.add('system');
        }

        const senderName = message.sender?.name || 'Systém';
        const timestamp = app.formatTime(message.created_at);

        messageEl.innerHTML = `
            <div class="message-header">
                <span class="message-sender">${senderName}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-content">${app.renderTaggedContent(message.content)}</div>
        `;

        messagesArea.appendChild(messageEl);
        if (persist) {
            app.persistStateItem('chat', message);
        }
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
     * @param {Object} app
     * @param {Object} message
     * @param {boolean} persist
     */
    displayInfoMessage(app, message, persist = true) {
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
        const timestamp = app.formatTime(message.created_at);
        item.innerHTML = `
            <div class="message-header">
                <span class="message-sender">${app.escapeHtml(senderName)}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-content">${app.renderTaggedContent(message.content || '')}</div>
        `;

        infoFeed.appendChild(item);
        infoFeed.scrollTop = infoFeed.scrollHeight;

        if (persist) {
            app.persistStateItem('info', message);
        }
    },

    /**
     * Switch between chat and info tabs in communication panel.
     * @param {Object} app
     * @param {string} tabName
     */
    switchCommsTab(app, tabName) {
        app.activeCommsTab = tabName === 'info' ? 'info' : 'chat';

        document.querySelectorAll('.comms-tab').forEach((btn) => {
            const isActive = btn.dataset.tab === app.activeCommsTab;
            btn.classList.toggle('active', isActive);
            btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });

        const chatPane = document.getElementById('chat-pane');
        const infoPane = document.getElementById('info-pane');
        if (chatPane) {
            chatPane.classList.toggle('active', app.activeCommsTab === 'chat');
        }
        if (infoPane) {
            infoPane.classList.toggle('active', app.activeCommsTab === 'info');
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
};

window.AppMessagingModule = AppMessagingModule;