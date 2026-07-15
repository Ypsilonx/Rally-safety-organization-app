/**
 * Rally Safety App - Map module
 * Initializes Leaflet map and delegates track/station logic to focused modules.
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
    config: MAP_CONFIG,
    stationCoordinates: STATION_COORDINATES,
    roleIconMap: ROLE_ICON_MAP,
    fallbackTrack: SAMPLE_TRACK_FALLBACK,
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

        const geojson = await window.MapTrackModule.loadTrackGeoJson(this);
        window.MapTrackModule.renderTrack(this, geojson);

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

        await window.MapStationsModule.refreshStationMarkers(this);
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
            window.MapStationsModule.refreshStationMarkers(this).catch((error) => {
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
        return window.MapStationsModule.refreshStationMarkers(this);
    },

    /**
     * Mark station as alerting for visual emphasis.
     *
     * @param {string} stationId - Station identifier
     */
    markStationAlert(stationId) {
        return window.MapStationsModule.markStationAlert(this, stationId);
    },

    /**
     * Clear one station alert state.
     *
     * @param {string} stationId - Station identifier
     */
    clearStationAlert(stationId) {
        return window.MapStationsModule.clearStationAlert(this, stationId);
    },

    /**
     * Clear all active station alerts.
     */
    clearAllStationAlerts() {
        return window.MapStationsModule.clearAllStationAlerts(this);
    },

    /**
     * Determine if station currently has active alert marker state.
     *
     * @param {string} stationId - Station identifier
     * @returns {boolean}
     */
    isStationAlert(stationId) {
        return window.MapStationsModule.isStationAlert(this, stationId);
    },

    /**
     * Focus map view on a station marker and open popup.
     *
     * @param {string} stationId - Station identifier
     * @returns {boolean}
     */
    focusStation(stationId) {
        return window.MapStationsModule.focusStation(this, stationId);
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

};

window.MapModule = MapModule;
