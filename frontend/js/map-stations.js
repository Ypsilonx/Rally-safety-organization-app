/**
 * Rally Safety App - Station marker service for Leaflet map.
 */

const MapStationsModule = {
    /**
     * Fetch status API and render station markers.
     * @param {Object} mapModule
     * @returns {Promise<void>}
     */
    async refreshStationMarkers(mapModule) {
        if (!mapModule.stationLayer) {
            return;
        }

        try {
            const response = await fetch(mapModule.config.statusApiUrl);
            if (!response.ok) {
                throw new Error(`Status API ${response.status}`);
            }

            const payload = await response.json();
            const stations = Array.isArray(payload.stations) ? payload.stations : [];
            this.renderStationMarkers(mapModule, stations);
            this.updateStatusFromStations(mapModule, stations);
            this.updateOnlineCounter(stations);

            window.dispatchEvent(new CustomEvent('stations:update', {
                detail: {
                    stations,
                },
            }));
        } catch (error) {
            console.error('Failed to load station statuses:', error);
            mapModule.setStatus('Status stanic nedostupný', true);
        }
    },

    /**
     * Mark station as alerting for visual emphasis.
     * @param {Object} mapModule
     * @param {string} stationId
     */
    markStationAlert(mapModule, stationId) {
        if (!stationId) {
            return;
        }
        mapModule.stationAlerts.set(
            stationId.toLowerCase(),
            Date.now() + mapModule.config.markerAlertDurationMs,
        );
        this.refreshStationMarkers(mapModule).catch((error) => {
            console.error('Failed to refresh station alerts:', error);
        });
    },

    /**
     * Clear one station alert state.
     * @param {Object} mapModule
     * @param {string} stationId
     */
    clearStationAlert(mapModule, stationId) {
        if (!stationId) {
            return;
        }
        mapModule.stationAlerts.delete(stationId.toLowerCase());
        this.refreshStationMarkers(mapModule).catch((error) => {
            console.error('Failed to clear station alert:', error);
        });
    },

    /**
     * Clear all active station alerts.
     * @param {Object} mapModule
     */
    clearAllStationAlerts(mapModule) {
        mapModule.stationAlerts.clear();
        this.refreshStationMarkers(mapModule).catch((error) => {
            console.error('Failed to clear all station alerts:', error);
        });
    },

    /**
     * Focus map view on a station marker and open popup.
     * @param {Object} mapModule
     * @param {string} stationId
     * @returns {boolean}
     */
    focusStation(mapModule, stationId) {
        if (!mapModule.map || !stationId) {
            return false;
        }

        const marker = mapModule.stationMarkers.get(stationId.toLowerCase());
        if (!marker) {
            return false;
        }

        mapModule.map.flyTo(marker.getLatLng(), Math.max(mapModule.map.getZoom(), 14), {
            duration: 0.35,
        });
        marker.openPopup();
        return true;
    },

    /**
     * Determine if station currently has active alert marker state.
     * @param {Object} mapModule
     * @param {string} stationId
     * @returns {boolean}
     */
    isStationAlert(mapModule, stationId) {
        if (!stationId) {
            return false;
        }

        const key = stationId.toLowerCase();
        const expiresAt = mapModule.stationAlerts.get(key);
        if (!expiresAt) {
            return false;
        }

        if (Date.now() > expiresAt) {
            mapModule.stationAlerts.delete(key);
            return false;
        }

        return true;
    },

    /**
     * Render station markers with online/offline colors.
     * @param {Object} mapModule
     * @param {Array<Object>} stations
     */
    renderStationMarkers(mapModule, stations) {
        mapModule.stationLayer.clearLayers();
        mapModule.stationMarkers.clear();

        stations.forEach((station, index) => {
            const latLng = this.getStationLatLng(mapModule, station.station_id, index);
            const online = Boolean(station.online);
            const roleIcon = this.getRoleIcon(mapModule, station.role);
            const alertActive = this.isStationAlert(mapModule, station.station_id);
            const marker = L.marker(latLng, {
                icon: this.createStationIcon(mapModule, online, roleIcon, alertActive),
            });

            marker.bindPopup(this.buildStationPopup(station));
            marker.bindTooltip(station.station_id || 'N/A', {
                direction: 'top',
                offset: [0, -8],
            });

            marker.addTo(mapModule.stationLayer);

            const stationId = station.station_id;
            if (stationId) {
                mapModule.stationMarkers.set(stationId.toLowerCase(), marker);
            }
        });
    },

    /**
     * Build custom marker icon with status color + role symbol.
     * @param {Object} mapModule
     * @param {boolean} online
     * @param {string} roleIcon
     * @param {boolean} alertActive
     * @returns {Object}
     */
    createStationIcon(mapModule, online, roleIcon, alertActive) {
        const stateClass = online ? 'online' : 'offline';
        const alertClass = alertActive ? 'alert' : '';
        const alertFlag = alertActive ? '<span class="station-alert-flag">!</span>' : '';
        const html = `
            <div class="station-marker ${stateClass} ${alertClass}">
                ${this.escapeHtml(roleIcon)}
                ${alertFlag}
            </div>
        `;
        return L.divIcon({
            className: 'station-marker-wrapper',
            html,
            iconSize: [26, 26],
            iconAnchor: [13, 13],
            popupAnchor: [0, -10],
        });
    },

    /**
     * Resolve role/type symbol shown inside station marker.
     * @param {Object} mapModule
     * @param {string} role
     * @returns {string}
     */
    getRoleIcon(mapModule, role) {
        if (!role) {
            return '?';
        }
        return mapModule.roleIconMap[role] || role.charAt(0).toUpperCase();
    },

    /**
     * Build popup HTML with station details.
     * @param {Object} station
     * @returns {string}
     */
    buildStationPopup(station) {
        const status = station.online ? 'Online' : 'Offline';
        const badgeClass = station.online ? 'online' : 'offline';
        const name = this.escapeHtml(station.name || 'Neznámá stanice');
        const role = this.escapeHtml(station.role || 'N/A');
        const stationId = this.escapeHtml(station.station_id || 'N/A');
        const seconds = Number.isFinite(station.seconds_since_last_seen)
            ? station.seconds_since_last_seen
            : 0;
        const absoluteLastSeen = this.formatAbsoluteTime(station.last_seen);
        const activeConnections = Number.isFinite(station.active_connections)
            ? station.active_connections
            : 0;

        return `
            <div class="map-popup">
                <h4>${stationId}</h4>
                <p><strong>Stanice:</strong> ${name}</p>
                <p><strong>Role:</strong> ${role}</p>
                <p><strong>Připojení:</strong> ${activeConnections}</p>
                <p><strong>Poslední aktivita:</strong> před ${seconds}s</p>
                <p><strong>Naposledy:</strong> ${absoluteLastSeen}</p>
                <span class="map-popup-badge ${badgeClass}">${status}</span>
            </div>
        `;
    },

    /**
     * Pick station coordinates from known map or deterministic fallback.
     * @param {Object} mapModule
     * @param {string} stationId
     * @param {number} index
     * @returns {Array<number>}
     */
    getStationLatLng(mapModule, stationId, index) {
        if (stationId && mapModule.stationCoordinates[stationId]) {
            return mapModule.stationCoordinates[stationId];
        }

        const baseLat = mapModule.config.fallbackCenter[0] + (index * 0.004);
        const baseLng = mapModule.config.fallbackCenter[1] - (index * 0.0035);
        return [baseLat, baseLng];
    },

    /**
     * Update map status label from station list.
     * @param {Object} mapModule
     * @param {Array<Object>} stations
     */
    updateStatusFromStations(mapModule, stations) {
        const total = stations.length;
        const online = stations.filter((item) => item.online).length;
        mapModule.setStatus(`Trať načtena | Stanice ${online}/${total} online`);
    },

    /**
     * Update admin online stat card if present.
     * @param {Array<Object>} stations
     */
    updateOnlineCounter(stations) {
        const onlineEl = document.getElementById('stat-online');
        const offlineEl = document.getElementById('stat-offline');
        const offlineListEl = document.getElementById('stat-offline-list');

        if (!onlineEl || !offlineEl || !offlineListEl) {
            return;
        }

        const total = stations.length;
        const online = stations.filter((item) => item.online).length;
        const offlineStations = stations.filter((item) => !item.online);

        onlineEl.textContent = `${online}/${total}`;
        offlineEl.textContent = String(offlineStations.length);
        offlineListEl.textContent = offlineStations.length
            ? offlineStations.map((item) => item.station_id || 'N/A').join(', ')
            : '-';
    },

    /**
     * Format absolute timestamp for popup detail.
     * @param {string} isoString
     * @returns {string}
     */
    formatAbsoluteTime(isoString) {
        if (!isoString) {
            return 'N/A';
        }
        try {
            const date = new Date(isoString);
            return date.toLocaleString('cs-CZ', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            });
        } catch (_error) {
            return 'N/A';
        }
    },

    /**
     * Escape HTML string for safe marker popup rendering.
     * @param {string} text
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

window.MapStationsModule = MapStationsModule;