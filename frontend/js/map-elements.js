/**
 * Rally Safety App - Generic map elements layer for Leaflet map.
 * Renders commissioners, spectators, safety points and closures from GeoJSON.
 */

const MapElementsModule = {
    /**
     * Load element GeoJSON with graceful fallback.
     * @param {Object} mapModule
     * @returns {Promise<Object>} GeoJSON FeatureCollection
     */
    async loadElementsGeoJson(mapModule) {
        const candidates = [
            '/data/example-map-elements.geojson',
            '../data/example-map-elements.geojson',
            'data/example-map-elements.geojson',
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

        mapModule.setStatus('Použit fallback prvků trati', true);
        return this.getFallbackElements();
    },

    /**
     * Render generic map elements and fit their bounds if needed.
     * @param {Object} mapModule
     * @param {Object} geojson
     */
    renderElements(mapModule, geojson) {
        if (!mapModule.map || !mapModule.elementLayer) {
            return;
        }

        mapModule.elementLayer.clearLayers();
        mapModule.elementMarkers.clear();

        const elements = Array.isArray(geojson?.features) ? geojson.features : [];
        elements.forEach((feature) => {
            const geometryType = feature?.geometry?.type;
            if (geometryType === 'Point') {
                this.renderPointFeature(mapModule, feature);
            } else if (geometryType === 'LineString') {
                this.renderLineFeature(mapModule, feature);
            }
        });
    },

    /**
     * Render one point feature as a typed marker.
     * @param {Object} mapModule
     * @param {Object} feature
     */
    renderPointFeature(mapModule, feature) {
        const coordinates = feature.geometry.coordinates;
        if (!Array.isArray(coordinates) || coordinates.length < 2) {
            return;
        }

        const latLng = [coordinates[1], coordinates[0]];
        const properties = feature.properties || {};
        const kind = String(properties.kind || 'element');
        const marker = L.marker(latLng, {
            icon: this.createElementIcon(kind, properties.requires_commissioner),
        });

        marker.bindPopup(this.buildElementPopup(properties));
        marker.bindTooltip(properties.name || properties.element_id || 'Prvek', {
            direction: 'top',
            offset: [0, -8],
        });

        marker.addTo(mapModule.elementLayer);
        if (properties.element_id) {
            mapModule.elementMarkers.set(String(properties.element_id).toLowerCase(), marker);
        }
    },

    /**
     * Render one line feature as a styled segment.
     * @param {Object} mapModule
     * @param {Object} feature
     */
    renderLineFeature(mapModule, feature) {
        const coordinates = feature.geometry.coordinates;
        if (!Array.isArray(coordinates) || !coordinates.length) {
            return;
        }

        const properties = feature.properties || {};
        const kind = String(properties.kind || 'line');
        const style = this.getLineStyle(kind);

        L.geoJSON(feature, {
            style,
            onEachFeature: (_geoFeature, layer) => {
                layer.bindPopup(this.buildElementPopup(properties));
                layer.bindTooltip(properties.name || properties.element_id || 'Prvek', {
                    sticky: true,
                });
            },
        }).addTo(mapModule.elementLayer);
    },

    /**
     * Create a typed icon for point features.
     * @param {string} kind
     * @param {boolean} requiresCommissioner
     * @returns {Object}
     */
    createElementIcon(kind, requiresCommissioner) {
        const typeClass = this.getElementClass(kind, requiresCommissioner);
        const symbol = this.getElementSymbol(kind);
        return L.divIcon({
            className: 'element-marker-wrapper',
            html: `<div class="element-marker ${typeClass}">${this.escapeHtml(symbol)}</div>`,
            iconSize: [28, 28],
            iconAnchor: [14, 14],
            popupAnchor: [0, -12],
        });
    },

    /**
     * Build popup HTML for a feature.
     * @param {Object} properties
     * @returns {string}
     */
    buildElementPopup(properties) {
        const name = this.escapeHtml(properties.name || 'Prvek trati');
        const positionName = this.escapeHtml(properties.position_name || properties.element_id || 'neuvedeno');
        const contactName = properties.contact_name ? this.escapeHtml(properties.contact_name) : '';
        const contactPhone = properties.contact_phone ? this.escapeHtml(properties.contact_phone) : '';
        const kind = this.escapeHtml(properties.kind || 'element');
        const note = this.escapeHtml(properties.note || '-');
        const commissionerRule = properties.requires_commissioner ? 'ano' : 'ne';
        const ruleText = this.escapeHtml(properties.commissioner_rule || '-');
        const contactLines = [];

        if (contactName) {
            contactLines.push(`<p><strong>Kontakt:</strong> ${contactName}</p>`);
        }
        if (contactPhone) {
            contactLines.push(`<p><strong>Telefon:</strong> ${contactPhone}</p>`);
        }

        return `
            <div class="map-popup">
                <h4>${name}</h4>
                <p><strong>Název pozice:</strong> ${positionName}</p>
                ${contactLines.join('')}
                <p><strong>Typ:</strong> ${kind}</p>
                <p><strong>Podléhá pravidlům komisaře:</strong> ${commissionerRule}</p>
                <p><strong>Pravidlo:</strong> ${ruleText}</p>
                <p><strong>Poznámka:</strong> ${note}</p>
            </div>
        `;
    },

    /**
     * Return style for line features.
     * @param {string} kind
     * @returns {Object}
     */
    getLineStyle(kind) {
        if (kind === 'closure') {
            return {
                color: '#b91c1c',
                weight: 4,
                dashArray: '10 8',
                opacity: 0.9,
            };
        }

        return {
            color: '#0f172a',
            weight: 3,
            dashArray: '4 6',
            opacity: 0.85,
        };
    },

    /**
     * Return CSS class for an element type.
     * @param {string} kind
     * @param {boolean} requiresCommissioner
     * @returns {string}
     */
    getElementClass(kind, requiresCommissioner) {
        if (!requiresCommissioner) {
            return kind;
        }

        const commissionerKinds = new Set(['start', 'finish', 'timing', 'medical', 'fire', 'commissioner']);
        if (commissionerKinds.has(kind)) {
            return `${kind} commissioner`;
        }

        return `${kind} commissioner`;
    },

    /**
     * Return one-letter symbol for an element type.
     * @param {string} kind
     * @returns {string}
     */
    getElementSymbol(kind) {
        const symbols = {
            start: 'S',
            finish: 'F',
            timing: 'C',
            medical: '+',
            fire: 'H',
            spectator: 'D',
            retarder: 'R',
            closure: 'X',
            commissioner: 'K',
        };

        return symbols[kind] || kind.charAt(0).toUpperCase();
    },

    /**
     * Provide built-in fallback features when the file is unavailable.
     * @returns {Object}
     */
    getFallbackElements() {
        return {
            type: 'FeatureCollection',
            features: [],
        };
    },

    /**
     * Escape HTML string for safe rendering.
     * @param {string} text
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

window.MapElementsModule = MapElementsModule;
