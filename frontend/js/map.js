/**
 * Rally Safety App - Map module
 * Initializes Leaflet map and renders sample rally track from GeoJSON.
 */

const MAP_CONFIG = {
    tileUrl: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
    fallbackCenter: [49.1951, 16.6068],
    fallbackZoom: 12,
    trackColor: '#dc2626',
    statusApiUrl: 'http://localhost:8000/api/stations/status',
    stationRefreshMs: 15000,
    markerAlertDurationMs: 15 * 60 * 1000,
};

const STATION_COORDINATES = {
    'TK-01': [49.2088, 16.5792],
    'ZT-05': [49.1936, 16.6241],
};

const ROLE_ICON_MAP = {
    vedouci: 'V',
    zastupce: 'Z',
    komisar_trat: 'T',
    casomer: 'C',
    parkovani: 'P',
    zdravotnik: '+',
    start: 'S',
    cil: 'F',
    bezpecnost: 'B',
};

const SAMPLE_TRACK_FALLBACK = {
    type: 'FeatureCollection',
    features: [
        {
            type: 'Feature',
            properties: { name: 'Sample RZ Track' },
            geometry: {
                type: 'LineString',
                coordinates: [
                    [16.5766, 49.2093],
                    [16.5885, 49.2054],
                    [16.6018, 49.2013],
                    [16.6172, 49.1948],
                    [16.6339, 49.1882],
                    [16.6484, 49.1831],
                ],
            },
        },
    ],
};

/**
 * Map module singleton.
 */
const MapModule = {
    map: null,
    trackLayer: null,
    stationLayer: null,
    stationMarkers: new Map(),
    stationAlerts: new Map(),
    stationRefreshTimer: null,
    isInitialized: false,

    /**
     * Initialize map once after app login.
     *
     * @returns {Promise<void>}
     */
    async init() {
        if (this.isInitialized) {
            return;
        }

        const mapElement = document.getElementById('map');
        if (!mapElement || typeof L === 'undefined') {
            this.setStatus('Mapa není dostupná', true);
            return;
        }

        this.map = L.map('map', {
            zoomControl: true,
            preferCanvas: true,
        }).setView(MAP_CONFIG.fallbackCenter, MAP_CONFIG.fallbackZoom);

        L.tileLayer(MAP_CONFIG.tileUrl, {
            maxZoom: 19,
            attribution: MAP_CONFIG.attribution,
        }).addTo(this.map);

        const geojson = await this.loadTrackGeoJson();
        this.renderTrack(geojson);

        this.stationLayer = L.layerGroup().addTo(this.map);

        window.addEventListener('station:alert', (event) => {
            const stationId = event.detail?.stationId;
            this.markStationAlert(stationId);
        });

        window.addEventListener('station:clear-alert', (event) => {
            const stationId = event.detail?.stationId;
            this.clearStationAlert(stationId);
        });

        window.addEventListener('station:clear-all-alerts', () => {
            this.clearAllStationAlerts();
        });

        await this.refreshStationMarkers();
        this.startStationRefresh();

        this.isInitialized = true;

        // Leaflet needs resize invalidation after flex layout settles.
        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 120);
    },

    /**
     * Start periodic station refresh from backend status API.
     */
    startStationRefresh() {
        if (this.stationRefreshTimer) {
            clearInterval(this.stationRefreshTimer);
        }
        this.stationRefreshTimer = setInterval(() => {
            this.refreshStationMarkers().catch((error) => {
                console.error('Station refresh failed:', error);
                this.setStatus('Chyba načítání stanic', true);
            });
        }, MAP_CONFIG.stationRefreshMs);
    },

    /**
     * Fetch status API and render station markers.
     *
     * @returns {Promise<void>}
     */
    async refreshStationMarkers() {
        if (!this.stationLayer) {
            return;
        }

        try {
            const response = await fetch(MAP_CONFIG.statusApiUrl);
            if (!response.ok) {
                throw new Error(`Status API ${response.status}`);
            }

            const payload = await response.json();
            const stations = Array.isArray(payload.stations) ? payload.stations : [];
            this.renderStationMarkers(stations);
            this.updateStatusFromStations(stations);
            this.updateOnlineCounter(stations);

            window.dispatchEvent(new CustomEvent('stations:update', {
                detail: {
                    stations,
                },
            }));
        } catch (error) {
            console.error('Failed to load station statuses:', error);
            this.setStatus('Status stanic nedostupný', true);
        }
    },

    /**
     * Render station markers with online/offline colors.
     *
     * @param {Array<Object>} stations - Station status records
     */
    renderStationMarkers(stations) {
        if (!this.stationLayer) {
            return;
        }

        this.stationLayer.clearLayers();
        this.stationMarkers.clear();

        stations.forEach((station, index) => {
            const latLng = this.getStationLatLng(station.station_id, index);
            const online = Boolean(station.online);
            const roleIcon = this.getRoleIcon(station.role);
            const alertActive = this.isStationAlert(station.station_id);
            const marker = L.marker(latLng, {
                icon: this.createStationIcon(online, roleIcon, alertActive),
            });

            marker.bindPopup(this.buildStationPopup(station));
            marker.bindTooltip(station.station_id || 'N/A', {
                direction: 'top',
                offset: [0, -8],
            });

            marker.addTo(this.stationLayer);

            const stationId = station.station_id;
            if (stationId) {
                this.stationMarkers.set(stationId.toLowerCase(), marker);
            }
        });
    },

    /**
     * Build custom marker icon with status color + role symbol.
     *
     * @param {boolean} online - Online status
     * @param {string} roleIcon - Single letter role icon
     * @returns {Object}
     */
    createStationIcon(online, roleIcon, alertActive) {
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
     *
     * @param {string} role - Station role identifier
     * @returns {string}
     */
    getRoleIcon(role) {
        if (!role) {
            return '?';
        }
        return ROLE_ICON_MAP[role] || role.charAt(0).toUpperCase();
    },

    /**
     * Mark station as alerting for visual emphasis.
     *
     * @param {string} stationId - Station identifier
     */
    markStationAlert(stationId) {
        if (!stationId) {
            return;
        }
        this.stationAlerts.set(stationId.toLowerCase(), Date.now() + MAP_CONFIG.markerAlertDurationMs);
        this.refreshStationMarkers().catch((error) => {
            console.error('Failed to refresh station alerts:', error);
        });
    },

    /**
     * Clear one station alert state.
     *
     * @param {string} stationId - Station identifier
     */
    clearStationAlert(stationId) {
        if (!stationId) {
            return;
        }
        this.stationAlerts.delete(stationId.toLowerCase());
        this.refreshStationMarkers().catch((error) => {
            console.error('Failed to clear station alert:', error);
        });
    },

    /**
     * Clear all active station alerts.
     */
    clearAllStationAlerts() {
        this.stationAlerts.clear();
        this.refreshStationMarkers().catch((error) => {
            console.error('Failed to clear all station alerts:', error);
        });
    },

    /**
     * Determine if station currently has active alert marker state.
     *
     * @param {string} stationId - Station identifier
     * @returns {boolean}
     */
    isStationAlert(stationId) {
        if (!stationId) {
            return false;
        }

        const key = stationId.toLowerCase();
        const expiresAt = this.stationAlerts.get(key);
        if (!expiresAt) {
            return false;
        }

        if (Date.now() > expiresAt) {
            this.stationAlerts.delete(key);
            return false;
        }

        return true;
    },

    /**
     * Focus map view on a station marker and open popup.
     *
     * @param {string} stationId - Station identifier
     * @returns {boolean}
     */
    focusStation(stationId) {
        if (!this.map || !stationId) {
            return false;
        }

        const marker = this.stationMarkers.get(stationId.toLowerCase());
        if (!marker) {
            return false;
        }

        this.map.flyTo(marker.getLatLng(), Math.max(this.map.getZoom(), 14), {
            duration: 0.35,
        });
        marker.openPopup();
        return true;
    },

    /**
     * Build popup HTML with station details.
     *
     * @param {Object} station - Station status object
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
     * Format absolute timestamp for popup detail.
     *
     * @param {string} isoString - ISO datetime string
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
     * Pick station coordinates from known map or deterministic fallback.
     *
     * @param {string} stationId - Station identifier
     * @param {number} index - Station index in list
     * @returns {Array<number>}
     */
    getStationLatLng(stationId, index) {
        if (stationId && STATION_COORDINATES[stationId]) {
            return STATION_COORDINATES[stationId];
        }

        const baseLat = MAP_CONFIG.fallbackCenter[0] + (index * 0.004);
        const baseLng = MAP_CONFIG.fallbackCenter[1] - (index * 0.0035);
        return [baseLat, baseLng];
    },

    /**
     * Update map status label from station list.
     *
     * @param {Array<Object>} stations - Station status list
     */
    updateStatusFromStations(stations) {
        const total = stations.length;
        const online = stations.filter((item) => item.online).length;
        this.setStatus(`Trať načtena | Stanice ${online}/${total} online`);
    },

    /**
     * Update admin online stat card if present.
     *
     * @param {Array<Object>} stations - Station status list
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
     * Load GeoJSON track with graceful fallback.
     *
     * @returns {Promise<Object>} GeoJSON FeatureCollection
     */
    async loadTrackGeoJson() {
        const candidates = [
            '/data/example-track.geojson',
            '../data/example-track.geojson',
            'data/example-track.geojson',
        ];

        for (const path of candidates) {
            try {
                const response = await fetch(path);
                if (!response.ok) {
                    continue;
                }
                return await response.json();
            } catch (_error) {
                // Continue with next candidate path.
            }
        }

        this.setStatus('Použit fallback trati', true);
        return SAMPLE_TRACK_FALLBACK;
    },

    /**
     * Render track GeoJSON and fit map bounds.
     *
     * @param {Object} geojson - GeoJSON FeatureCollection
     */
    renderTrack(geojson) {
        if (!this.map) {
            return;
        }

        if (this.trackLayer) {
            this.map.removeLayer(this.trackLayer);
        }

        this.trackLayer = L.geoJSON(geojson, {
            style: {
                color: MAP_CONFIG.trackColor,
                weight: 5,
                opacity: 0.9,
            },
        }).addTo(this.map);

        const bounds = this.trackLayer.getBounds();
        if (bounds.isValid()) {
            this.map.fitBounds(bounds, { padding: [18, 18] });
        }
    },

    /**
     * Update status label shown above map.
     *
     * @param {string} message - Status text
     * @param {boolean} warning - Whether to show warning color
     */
    setStatus(message, warning = false) {
        const statusEl = document.getElementById('map-status');
        if (!statusEl) {
            return;
        }
        statusEl.textContent = message;
        statusEl.style.color = warning ? '#fbbf24' : '#9ca3af';
    },

    /**
     * Escape HTML string for safe marker popup rendering.
     *
     * @param {string} text - Input text
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

window.MapModule = MapModule;
