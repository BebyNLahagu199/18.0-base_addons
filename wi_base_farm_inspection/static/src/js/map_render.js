/** @odoo-module **/

import {Component, onMounted, useRef, onWillStart} from "@odoo/owl";
import {registry} from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class MapOverview extends Component {
    static template = "wi_base_farm_inspection.MapOverview";

    static props = {
        coordinate_map: {type: [String, Object], optional: true},
        record: {type: Object, optional: true},
        readonly: {type: Boolean, optional: true},
        id: {optional: true},
        name: {type: String, optional: true},
    };

    setup() {
        this.mapRef = useRef("map");
        this.geojsonData = null;

        onWillStart(async () => {
            await new Promise((resolve) => {
                const check = () => (window.L ? resolve() : setTimeout(check, 100));
                check();
            });

            const record = this.env.model.root;
            const company = record.data.company_id;

            if (company && Array.isArray(company) && company.length > 0) {
                const companyId = company[0];

                try {
                    debugger;
                    const result = await rpc("/geo/location/data", {
                        company_id: companyId,
                    });
                    if (result && Array.isArray(result.estates)) {
                        this.geojsonData = result.estates
                            .map((e) => e.geojson)
                            .filter(Boolean);
                    } else if (result && result.geojson) {
                        this.geojsonData = JSON.parse(result.geojson);
                    }
                } catch (error) {
                    console.warn("Failed to load GeoJSON:", error);
                }
            } else {
                console.log("No company_id found in record");
            }
        });

        onMounted(() => {
            this._renderMap();
        });
    }

    // Render Map
    _renderMap() {
        setTimeout(() => {
            const L = window.L;
            const el = this.mapRef.el;

            if (!L || !el) return;

            const estateColorsNormal = [
                "red",
                "brown",
                "purple",
                "orange",
                "yellow",
                "pink",
            ];
            const estateColorsSatellite = ["lime", "yellow", "red", "white"];

            const map = L.map(el).setView([0, 0], 2);

            const normalLayer = L.tileLayer(
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                {maxZoom: 19, attribution: "© OpenStreetMap"}
            );

            const satellitLayer = L.tileLayer(
                "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                {attribution: "Tiles © Esri"}
            );

            map.addLayer(normalLayer);
            let isSatellite = false;
            let routeLine = null;
            const geoLayers = [];

            const toggleButton = L.control({position: "topleft"});
            toggleButton.onAdd = function () {
                const div = L.DomUtil.create(
                    "div",
                    "leaflet-bar leaflet-control leaflet-control-custom"
                );
                div.style.background = "white";
                div.style.padding = "5px";
                div.style.cursor = "pointer";
                div.innerHTML =
                    '<img src="/wi_base_farm_inspection/static/src/img/street.png" width="24" height="24"/>';
                div.onclick = () => {
                    if (isSatellite) {
                        map.removeLayer(satellitLayer);
                        map.addLayer(normalLayer);
                        div.innerHTML =
                            '<img src="/wi_base_farm_inspection/static/src/img/street.png" width="24" height="24"/>';
                        isSatellite = false;
                    } else {
                        map.removeLayer(normalLayer);
                        map.addLayer(satellitLayer);
                        div.innerHTML =
                            '<img src="/wi_base_farm_inspection/static/src/img/satellite.png" width="24" height="24"/>';
                        isSatellite = true;
                    }

                    geoLayers.forEach((geoLayer, index) => {
                        const newColor = isSatellite
                            ? estateColorsSatellite[
                                  index % estateColorsSatellite.length
                              ]
                            : estateColorsNormal[index % estateColorsNormal.length];
                        geoLayer.setStyle({color: newColor});

                        geoLayer.eachLayer((layer) => {
                            if (layer.getTooltip && layer.getTooltip()) {
                                const tooltipEl = layer.getTooltip().getElement();
                                if (tooltipEl) {
                                    tooltipEl.style.color = isSatellite
                                        ? "white"
                                        : "black";
                                }
                            }
                        });
                    });

                    if (routeLine) {
                        routeLine.setStyle({
                            color: isSatellite ? "red" : "blue",
                        });
                    }
                };
                return div;
            };
            toggleButton.addTo(map);

            const record = this.env.model.root;
            let coords = [];
            let issuePoints = [];

            try {
                const coordinateRecords = record.data.coordinate_ids.records || [];
                const issueRecords = record.data.issue_ids.records || [];

                const parsePoint = (r, sourceType = "Unknown") => {
                    let d = r.data;
                    if (typeof d === "string") d = JSON.parse(d);

                    const lat = parseFloat(d.lat ?? d.latitude);
                    const lng = parseFloat(d.lng ?? d.longitude);
                    if (isNaN(lat) || isNaN(lng)) return null;

                    return {
                        lat,
                        lng,
                        subject: d.subject || "No Subject",
                        date: d.date || null,
                        source: sourceType,
                        id: r.resId || d.id || null,
                        rawData: d,
                    };
                };

                const coordinatePoints = coordinateRecords
                    .map((r) => parsePoint(r, "Coordinate"))
                    .filter(Boolean);
                issuePoints = issueRecords
                    .map((r) => parsePoint(r, "Issue"))
                    .filter(Boolean);
                coords = [...coordinatePoints, ...issuePoints];
            } catch (e) {
                console.error("Error parsing coordinates:", e);
            }

            if (coords.length === 0) {
                L.marker([0, 0])
                    .addTo(map)
                    .bindPopup("No coordinate data available")
                    .openPopup();
                return;
            }

            map.setView([coords[0].lat, coords[0].lng], 12);

            if (Array.isArray(this.geojsonData)) {
                let colorIndex = 0;

                this.geojsonData.forEach((geojson) => {
                    const color =
                        estateColorsNormal[colorIndex % estateColorsNormal.length];
                    colorIndex++;

                    const geoLayer = L.geoJSON(geojson, {
                        style: {color: color, weight: 0.7, fillOpacity: 0},
                        onEachFeature: function (feature, layer) {
                            if (feature.properties?.No_Blok) {
                                layer.bindTooltip(feature.properties.No_Blok, {
                                    permanent: true,
                                    direction: "center",
                                    className: "",
                                    opacity: 1,
                                });

                                layer.on("add", () => {
                                    const tooltipEl = layer.getTooltip().getElement();
                                    if (tooltipEl) {
                                        tooltipEl.style.background = "none";
                                        tooltipEl.style.border = "none";
                                        tooltipEl.style.boxShadow = "none";
                                        tooltipEl.style.padding = "0";
                                        tooltipEl.style.fontWeight = "normal";
                                        tooltipEl.style.fontSize = "13px";
                                        tooltipEl.style.color = isSatellite
                                            ? "white"
                                            : "black";
                                    }
                                });
                            }
                        },
                    }).addTo(map);

                    geoLayers.push(geoLayer);

                    map.on("zoomend", function () {
                        const currentZoom = map.getZoom();
                        geoLayer.eachLayer(function (layer) {
                            if (layer.getTooltip()) {
                                if (currentZoom >= 14) layer.openTooltip();
                                else layer.closeTooltip();
                            }
                        });
                    });
                    map.fire("zoomend");

                    try {
                        map.fitBounds(geoLayer.getBounds());
                    } catch (e) {
                        console.warn("Could not fit bounds:", e);
                    }
                });
            }

            if (coords.length > 1) {
                const sortedCoords = coords.sort(
                    (a, b) => new Date(a.date || 0) - new Date(b.date || 0)
                );
                const linePoints = sortedCoords.map((c) => [c.lat, c.lng]);

                routeLine = L.polyline(linePoints, {
                    color: isSatellite ? "red" : "blue",
                    weight: 3,
                    opacity: 0.7,
                    dashArray: "5,5",
                }).addTo(map);

                const first = sortedCoords[0];
                const last = sortedCoords[sortedCoords.length - 1];

                L.circleMarker([first.lat, first.lng], {
                    color: "green",
                    radius: 6,
                    fillColor: "green",
                    fillOpacity: 1,
                })
                    .addTo(map)
                    .bindPopup("Start");

                L.circleMarker([last.lat, last.lng], {
                    color: "red",
                    radius: 6,
                    fillColor: "red",
                    fillOpacity: 1,
                })
                    .addTo(map)
                    .bindPopup("End");

                map.fitBounds(linePoints);
            }

            const warningIcon = L.icon({
                iconUrl: "https://cdn-icons-png.flaticon.com/512/4539/4539472.png",
                iconSize: [45, 45],
                iconAnchor: [10, 34],
                popupAnchor: [0, -30],
            });

            issuePoints.forEach((c, idx) => {
                const marker = L.marker([c.lat, c.lng], {icon: warningIcon}).addTo(map);
                const popupContent = `
                <div>
                    <b>${c.subject}</b><br/>
                    <b>Tanggal:</b> ${
                        c.date ? new Date(c.date).toLocaleDateString() : "-"
                    }<br/>
                            <button id="btn-issue-${idx}" class="btn btn-primary mt-3">Lihat Detail</button>
                        </div>
                    `;
                marker.bindPopup(popupContent);
                marker.on("popupopen", () => {
                    const btn = document.getElementById(`btn-issue-${idx}`);
                    if (btn) {
                        btn.addEventListener("click", () => {
                            if (!c.id) return;
                            this.env.services.action.doAction({
                                type: "ir.actions.act_window",
                                res_model: "farm.issue",
                                res_id: c.id,
                                views: [[false, "form"]],
                                target: "new",
                            });
                        });
                    }
                });
            });
        }, 0);
    }
}

export const mapOverview = {
    component: MapOverview,
    extractProps: ({attrs}) => {
        return {
            coordinate_map: attrs.coordinate_map || "{}",
            readonly: attrs.readonly === "1" || attrs.readonly === true,
            id: attrs.id,
            name: attrs.name,
        };
    },
};

registry.category("view_widgets").add("peta", mapOverview);
