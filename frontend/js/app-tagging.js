/**
 * Rally Safety App - Tagging and station suggestion module.
 * Handles @user/#station completion and station-focused tag interactions.
 */

const AppTaggingModule = {
    /**
     * Track known users and stations for tag suggestions.
     * @param {Object} app
     * @param {Object} message
     */
    registerSenderForTagging(app, message) {
        const senderName = message?.sender?.name;
        if (senderName) {
            app.knownUsers.add(senderName);
        }
    },

    /**
     * Update known station tags from status API payload.
     * @param {Object} app
     * @param {Array<Object>} stations
     */
    updateStationTags(app, stations) {
        stations.forEach((station) => {
            if (station.station_id) {
                app.knownStations.add(station.station_id);
            }

            if (station.name) {
                app.knownUsers.add(station.name);
            }
        });
    },

    /**
     * Handle click on station tag and focus marker on map.
     * @param {Object} app
     * @param {MouseEvent} event
     */
    handleTagClick(app, event) {
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
            app.showToast(`Stanice ${stationId} zatím není na mapě`, 'info');
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
     * @param {Object} app
     * @param {InputEvent} event
     */
    onMessageInputChanged(app, event) {
        const input = event.target;
        const value = input.value;
        const caret = input.selectionStart || value.length;
        const context = this.findTagContext(value, caret);

        if (!context) {
            app.hideTagSuggestions();
            return;
        }

        const pool = context.type === '@'
            ? Array.from(app.knownUsers)
            : Array.from(app.knownStations);

        const normalizedQuery = context.query.toLowerCase();
        const candidates = pool
            .filter((item) => item.toLowerCase().startsWith(normalizedQuery))
            .sort((a, b) => a.localeCompare(b, 'cs'))
            .slice(0, 7);

        if (!candidates.length) {
            app.hideTagSuggestions();
            return;
        }

        app.tagSuggestion = {
            active: true,
            type: context.type,
            query: context.query,
            start: context.start,
            end: caret,
            selectedIndex: 0,
            candidates,
        };

        this.renderTagSuggestions(app);
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
     * @param {Object} app
     */
    renderTagSuggestions(app) {
        const list = document.getElementById('tag-suggestions');
        if (!list || !app.tagSuggestion.active) {
            return;
        }

        const prefix = app.tagSuggestion.type;
        list.innerHTML = app.tagSuggestion.candidates
            .map((item, index) => {
                const active = index === app.tagSuggestion.selectedIndex ? 'active' : '';
                return `<button type="button" class="tag-suggestion-item ${active}" data-tag="${app.escapeHtml(item)}">${prefix}${app.escapeHtml(item)}</button>`;
            })
            .join('');

        list.classList.remove('hidden');

        list.querySelectorAll('.tag-suggestion-item').forEach((button) => {
            button.addEventListener('mousedown', (event) => {
                event.preventDefault();
                const tag = button.dataset.tag;
                this.applyTagSuggestion(app, tag);
            });
        });
    },

    /**
     * Apply selected tag into message input.
     * @param {Object} app
     * @param {string} tag
     */
    applyTagSuggestion(app, tag) {
        const input = document.getElementById('message-input');
        if (!input || !app.tagSuggestion.active) {
            return;
        }

        const before = input.value.slice(0, app.tagSuggestion.start);
        const after = input.value.slice(app.tagSuggestion.end);
        const insert = `${app.tagSuggestion.type}${tag} `;
        input.value = `${before}${insert}${after}`;
        const newCaret = (before + insert).length;
        input.setSelectionRange(newCaret, newCaret);
        input.focus();
        this.hideTagSuggestions(app);
    },

    /**
     * Keyboard support for suggestion dropdown.
     * @param {Object} app
     * @param {KeyboardEvent} event
     */
    onMessageInputKeyDown(app, event) {
        if (!app.tagSuggestion.active) {
            return;
        }

        const total = app.tagSuggestion.candidates.length;
        if (!total) {
            return;
        }

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            app.tagSuggestion.selectedIndex = (app.tagSuggestion.selectedIndex + 1) % total;
            this.renderTagSuggestions(app);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            app.tagSuggestion.selectedIndex = (app.tagSuggestion.selectedIndex - 1 + total) % total;
            this.renderTagSuggestions(app);
        } else if (event.key === 'Enter') {
            event.preventDefault();
            const tag = app.tagSuggestion.candidates[app.tagSuggestion.selectedIndex];
            this.applyTagSuggestion(app, tag);
        } else if (event.key === 'Escape') {
            event.preventDefault();
            this.hideTagSuggestions(app);
        }
    },

    /**
     * Hide and reset tag suggestion UI.
     * @param {Object} app
     */
    hideTagSuggestions(app) {
        app.tagSuggestion.active = false;
        app.tagSuggestion.candidates = [];
        app.tagSuggestion.selectedIndex = 0;

        const list = document.getElementById('tag-suggestions');
        if (list) {
            list.classList.add('hidden');
            list.innerHTML = '';
        }
    },

    /**
     * Render message content with highlighted @user and #station tags.
     * @param {Object} app
     * @param {string} text
     * @returns {string}
     */
    renderTaggedContent(app, text) {
        const source = String(text || '');
        const tokenRegex = /([@#][\w-]+)/g;
        const parts = source.split(tokenRegex);

        return parts.map((part) => {
            if (part.startsWith('@')) {
                const rawUser = part.slice(1);
                const knownUser = this.resolveKnownItem(app.knownUsers, rawUser);
                if (!knownUser) {
                    return app.escapeHtml(part);
                }
                return `<span class="chat-tag chat-tag-user">@${app.escapeHtml(knownUser)}</span>`;
            }
            if (part.startsWith('#')) {
                const rawStation = part.slice(1);
                const knownStation = this.resolveKnownItem(app.knownStations, rawStation);
                if (!knownStation) {
                    return app.escapeHtml(part);
                }
                const safeStation = app.escapeHtml(knownStation);
                return `<span class="chat-tag chat-tag-station chat-tag-clickable" data-station-id="${safeStation}" title="Přejít na stanici na mapě">#${safeStation}</span>`;
            }
            return app.escapeHtml(part);
        }).join('');
    },
};

window.AppTaggingModule = AppTaggingModule;