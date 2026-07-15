/**
 * Rally Safety App - Track loading and rendering for Leaflet map.
 */

const MapTrackModule = {
    /**
     * Load GeoJSON track with graceful fallback.
     * @param {Object} mapModule
     * @returns {Promise<Object>} GeoJSON FeatureCollection
     */
    async loadTrackGeoJson(mapModule) {
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

        mapModule.setStatus('Použit fallback trati', true);
        return mapModule.fallbackTrack;
    },

    /**
     * Render track GeoJSON and fit map bounds.
     * @param {Object} mapModule
     * @param {Object} geojson
     */
    renderTrack(mapModule, geojson) {
        if (!mapModule.map) {
            return;
        }

        if (mapModule.trackLayer) {
            mapModule.map.removeLayer(mapModule.trackLayer);
        }

        mapModule.trackLayer = L.geoJSON(geojson, {
            style: {
                color: mapModule.config.trackColor,
                weight: 5,
                opacity: 0.9,
            },
        }).addTo(mapModule.map);

        const bounds = mapModule.trackLayer.getBounds();
        if (bounds.isValid()) {
            mapModule.map.fitBounds(bounds, { padding: [18, 18] });
        }
    },
};

window.MapTrackModule = MapTrackModule;