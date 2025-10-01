/** @odoo-module **/

import {Component, onMounted, onWillStart, useRef} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {rpc} from "@web/core/network/rpc";

class MapInspection extends Component {
    static template = "wi_base_farm_inspection.MapInspection";

    setup() {
        this.mapRef = useRef("mapReport");
        this.searchInputRef = useRef("searchInput");
        this.searchResultsRef = useRef("searchResults");

        this.markersGroup = null;
        this.routeLine = [];
        this.legendControl = null;

        this.employees = [];

        this.geoColorsNormal = [
            "#fa0505ff",
            "#1f78b4",
            "#b2df8a",
            "#33a02c",
            "#fb9a99",
        ];
        this.geoColorsSatellite = [
            "#fdf904ff",
            "#024c74ff",
            "#b2f2a6",
            "#7fc97f",
            "#fdbb84",
        ];

        this.routeColorsNormal = [
            "blue",
            "green",
            "orange",
            "purple",
            "brown",
            "lime",
            "teal",
            "navy",
            "gray",
        ];
        this.routeColorsSatellite = [
            "#f1e203ff",
            "#90ee90",
            "#ffa500",
            "#d580ff",
            "#deb887",
            "#c0ff3e",
            "#40e0d0",
            "#87cefa",
            "#d3d3d3",
        ];

        this.isSatellite = false;

        onWillStart(async () => {
            await new Promise((resolve) => {
                const check = () => (window.L ? resolve() : setTimeout(check, 500));
                check();
            });

            const companyId = this.env.services.company.currentCompany.id;
            if (!companyId) return console.log("No company_id found");

            try {
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
                console.warn("Failed to load geo data:", error);
            }
        });

        onMounted(async () => {
            await this._getMap();
            this._setupSearch();
        });
    }

    async _getMap() {
        const mapEl = this.mapRef.el;
        if (!mapEl) return;

        this.map = L.map(mapEl).setView([-2.5, 118], 5);

        this.normalLayer = L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                attribution: "© OpenStreetMap contributors",
            }
        );
        this.satelliteLayer = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            {attribution: "Tiles © Esri"}
        );

        this.normalLayer.addTo(this.map);
        this.markersGroup = L.layerGroup().addTo(this.map);
        this.routeLine = [];

        // Toggle map button
        const toggleButton = L.control({position: "topleft"});
        toggleButton.onAdd = () => {
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
                this.isSatellite = !this.isSatellite;
                if (this.isSatellite) {
                    this.map.removeLayer(this.normalLayer);
                    this.map.addLayer(this.satelliteLayer);
                    div.innerHTML =
                        '<img src="/wi_base_farm_inspection/static/src/img/satellite.png" width="24" height="24"/>';
                } else {
                    this.map.removeLayer(this.satelliteLayer);
                    this.map.addLayer(this.normalLayer);
                    div.innerHTML =
                        '<img src="/wi_base_farm_inspection/static/src/img/street.png" width="24" height="24"/>';
                }
                this._updateMapColors();
            };
            return div;
        };
        toggleButton.addTo(this.map);

        // Load GeoJSON estates
        if (this.geojsonData && this.geojsonData.length) {
            let colorIndex = 0;
            this.geoLayers = [];
            this.geojsonData.forEach((geojson) => {
                const color =
                    this.geoColorsNormal[colorIndex % this.geoColorsNormal.length];
                colorIndex++;
                const geoLayer = L.geoJSON(geojson, {
                    style: {color, weight: 0.7, fillOpacity: 0},
                    onEachFeature: (feature, layer) => {
                        if (feature.properties?.No_Blok) {
                            layer.bindTooltip(feature.properties.No_Blok, {
                                permanent: true,
                                direction: "center",
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
                                    tooltipEl.style.color = this.isSatellite
                                        ? "white"
                                        : "black";
                                }
                            });
                        }
                    },
                }).addTo(this.map);
                this.geoLayers.push(geoLayer);

                const map = this.map;
                this.map.on("zoomend", function () {
                    const currentZoom = map.getZoom();
                    geoLayer.eachLayer(function (layer) {
                        if (layer.getTooltip()) {
                            if (currentZoom >= 14) layer.openTooltip();
                            else layer.closeTooltip();
                        }
                    });
                });

                this.map.fire("zoomend");

                try {
                    this.map.fitBounds(geoLayer.getBounds());
                } catch (e) {
                    console.warn("Could not fit bounds:", e);
                }
            });
        }

        this._updateMapColors = () => {
            if (this.geoLayers) {
                this.geoLayers.forEach((geoLayer, idx) => {
                    const color = this.isSatellite
                        ? this.geoColorsSatellite[idx % this.geoColorsSatellite.length]
                        : this.geoColorsNormal[idx % this.geoColorsNormal.length];
                    geoLayer.setStyle({color, weight: 0.7, fillOpacity: 0});
                    geoLayer.eachLayer((layer) => {
                        const tooltipEl = layer.getTooltip()?.getElement();
                        if (tooltipEl)
                            tooltipEl.style.color = this.isSatellite
                                ? "white"
                                : "black";
                    });
                });
            }
            if (this.routeLine) {
                this.routeLine.forEach((line, idx) => {
                    const color = this.isSatellite
                        ? this.routeColorsSatellite[
                        idx % this.routeColorsSatellite.length
                            ]
                        : this.routeColorsNormal[idx % this.routeColorsNormal.length];
                    line.setStyle({color});
                });
            }
        };

        // Load inspections
        const inspections = await rpc(
            "/get/inspection/location/data",
            {
                company_id: this.env.services.company.currentCompany.id,
            }
        );

        const employeeMap = {};
        inspections.forEach((insp) => {
            const empId = insp.employee_id || "Unknown";
            if (!employeeMap[empId]) {
                employeeMap[empId] = {
                    name: insp.employee_id || "Unknown",
                    inspections: [],
                };
            }
            employeeMap[empId].inspections.push({
                name: insp.name,
                coordinates: insp.coordinates || [],
                issues: insp.issue_ids || [],
            });
        });

        this.employees = inspections.map((emp) => {
            return {
                name: emp.employee_name || "Unknown",
                inspections: emp.inspections.map((insp) => {
                    const coords = insp.coordinates || [];
                    const issues = insp.issue_ids || [];
                    if (coords.length === 0) {
                        return {start: null, end: null, route: [], name: insp.name};
                    }
                    return {
                        start: {
                            lat: coords[0].latitude,
                            lon: coords[0].longitude,
                            city: "Start",
                        },
                        end: {
                            lat: coords[coords.length - 1].latitude,
                            lon: coords[coords.length - 1].longitude,
                            city: "End",
                        },
                        route: coords.map((c) => [c.latitude, c.longitude]),
                        name: insp.name,
                        issues: issues,
                    };
                }),
            };
        });
        this.showAllEmployees();
    }

    _setupSearch() {
        const input = this.searchInputRef.el;
        let debounceTimer = null;
        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => this._filterEmployees(input.value), 300);
        });
    }

    showAllEmployees() {
        if (!this.employees || !this.employees.length) return;

        const warningIcon = L.icon({
            iconUrl: "https://cdn-icons-png.flaticon.com/512/4539/4539472.png",
            iconSize: [45, 45],
            iconAnchor: [10, 34],
            popupAnchor: [0, -30],
        });

        this.markersGroup.clearLayers();
        this.routeLine.forEach((line) => this.map.removeLayer(line));
        this.routeLine = [];

        const resultsEl = this.searchResultsRef.el;
        resultsEl.innerHTML = "";

        const allBounds = [];
        this.issueMarkers = [];

        this.employees.forEach((emp, idx) => {
            const color = this.routeColorsNormal[idx % this.routeColorsNormal.length];

            // Sidebar employee
            const div = document.createElement("div");
            div.textContent = emp.name;
            div.style.cursor = "pointer";
            div.style.padding = "2px 0";
            div.addEventListener("click", () => this._showEmployeeRoute(emp, color));
            resultsEl.appendChild(div);

            // Semua inspections
            emp.inspections.forEach((insp) => {
                if (!insp.start || !insp.end) return;

                const startMarker = L.circleMarker([insp.start.lat, insp.start.lon], {
                    radius: 6,
                    color: "green",
                    fillColor: "green",
                    fillOpacity: 1,
                }).bindPopup(emp.name + "- (Start)");
                const endMarker = L.circleMarker([insp.end.lat, insp.end.lon], {
                    radius: 6,
                    color: "red",
                    fillColor: "red",
                    fillOpacity: 1,
                }).bindPopup(emp.name + "- (End)");

                this.markersGroup.addLayer(startMarker);
                this.markersGroup.addLayer(endMarker);

                insp.issues.forEach((issue) => {
                    if (issue.latitude && issue.longitude) {
                        const popupContent = `
                            <div>
                                <strong>Date:</strong> ${issue.date || "now"}<br/>
                                <strong>Issue:</strong> ${
                            issue.subject || "Unknown"
                        }<br/>
                                <button class="btn btn-primary mt-3 btn-issue-detail" data-id="${
                            issue.id
                        }">
                                    Detail
                                </button>
                            </div>
                        `;

                        const issueMarker = L.marker(
                            [issue.latitude, issue.longitude],
                            {
                                icon: warningIcon,
                            }
                        ).bindPopup(popupContent);

                        this.markersGroup.addLayer(issueMarker);
                        this.issueMarkers.push(issueMarker);
                    }
                });

                this.map.on("popupopen", (e) => {
                    const button =
                        e.popup._contentNode.querySelector(".btn-issue-detail");
                    if (button) {
                        button.addEventListener("click", () => {
                            const issueId = button.dataset.id;
                            if (issueId) {
                                this.env.services.action.doAction({
                                    type: "ir.actions.act_window",
                                    res_model: "farm.issue",
                                    res_id: parseInt(issueId, 10),
                                    views: [[false, "form"]],
                                    target: "current",
                                });
                            }
                        });
                    }
                });

                this.map.on("zoomend", () => {
                    const currentZoom = this.map.getZoom();
                    const minZoom = 14;

                    this.issueMarkers.forEach((marker) => {
                        if (currentZoom >= minZoom) {
                            if (!this.map.hasLayer(marker)) this.map.addLayer(marker);
                        } else if (this.map.hasLayer(marker))
                            this.map.removeLayer(marker);
                    });
                });

                const routeLine = L.polyline(insp.route, {
                    color,
                    weight: 3,
                    opacity: 0.8,
                    dashArray: "5,5",
                }).addTo(this.map);
                this.routeLine.push(routeLine);

                allBounds.push(
                    [insp.start.lat, insp.start.lon],
                    [insp.end.lat, insp.end.lon]
                );
            });
        });

        if (allBounds.length) this.map.fitBounds(allBounds);
        this._addLegend(this.employees);
    }

    _showEmployeeRoute(emp, color = "green") {
        this.markersGroup.clearLayers();
        this.routeLine.forEach((line) => this.map.removeLayer(line));
        this.routeLine = [];

        const warningIcon = L.icon({
            iconUrl: "https://cdn-icons-png.flaticon.com/512/4539/4539472.png",
            iconSize: [45, 45],
            iconAnchor: [10, 34],
            popupAnchor: [0, -30],
        });

        const allBounds = [];
        this.issueMarkers = [];

        emp.inspections.forEach((insp) => {
            if (!insp.start || !insp.end) return;

            const startMarker = L.circleMarker([insp.start.lat, insp.start.lon], {
                radius: 6,
                color: "green",
                fillColor: "green",
                fillOpacity: 1,
            })
                .bindPopup(emp.name + "- (Start)")
                .openPopup();
            const endMarker = L.circleMarker([insp.end.lat, insp.end.lon], {
                radius: 6,
                color: "red",
                fillColor: "red",
                fillOpacity: 1,
            }).bindPopup(emp.name + "- (End)");

            this.markersGroup.addLayer(startMarker);
            this.markersGroup.addLayer(endMarker);

            insp.issues.forEach((issue) => {
                if (issue.latitude && issue.longitude) {
                    const popupContent = `
                        <div>
                            <strong>Date:</strong> ${issue.date || "now"}<br/>
                            <strong>Issue:</strong> ${issue.subject || "Unknown"}<br/>
                            <button class="btn btn-primary mt-3 btn-issue-detail" data-id="${
                        issue.id
                    }">
                                Detail
                            </button>
                        </div>
                    `;

                    const issueMarker = L.marker([issue.latitude, issue.longitude], {
                        icon: warningIcon,
                    }).bindPopup(popupContent);

                    this.markersGroup.addLayer(issueMarker);
                    this.issueMarkers.push(issueMarker);
                }
            });

            this.map.on("popupopen", (e) => {
                const button = e.popup._contentNode.querySelector(".btn-issue-detail");
                if (button) {
                    button.addEventListener("click", () => {
                        const issueId = button.dataset.id;
                        if (issueId) {
                            this.env.services.action.doAction({
                                type: "ir.actions.act_window",
                                res_model: "farm.issue",
                                res_id: parseInt(issueId, 10),
                                views: [[false, "form"]],
                                target: "current",
                            });
                        }
                    });
                }
            });

            this.map.on("zoomend", () => {
                const currentZoom = this.map.getZoom();
                const minZoom = 14;

                this.issueMarkers.forEach((marker) => {
                    if (currentZoom >= minZoom) {
                        if (!this.map.hasLayer(marker)) this.map.addLayer(marker);
                    } else if (this.map.hasLayer(marker)) this.map.removeLayer(marker);
                });
            });

            const routeLine = L.polyline(insp.route, {
                color,
                weight: 3,
                opacity: 0.8,
                dashArray: "5,5",
            }).addTo(this.map);
            this.routeLine.push(routeLine);

            allBounds.push(
                [insp.start.lat, insp.start.lon],
                [insp.end.lat, insp.end.lon]
            );
        });

        if (allBounds.length) this.map.fitBounds(allBounds);
        this._addLegend([emp]);
    }

    _filterEmployees(query) {
        const resultsEl = this.searchResultsRef.el;
        resultsEl.innerHTML = "";

        const warningIcon = L.icon({
            iconUrl: "https://cdn-icons-png.flaticon.com/512/4539/4539472.png",
            iconSize: [45, 45],
            iconAnchor: [10, 34],
            popupAnchor: [0, -30],
        });

        const filtered = this.employees.filter((emp) =>
            emp.name.toLowerCase().includes(query.toLowerCase())
        );

        this.markersGroup.clearLayers();
        this.routeLine.forEach((line) => this.map.removeLayer(line));
        this.routeLine = [];

        const allBounds = [];
        this.issueMarkers = [];

        filtered.forEach((emp, idx) => {
            const color = this.routeColorsNormal[idx % this.routeColorsNormal.length];

            emp.inspections.forEach((insp) => {
                if (!insp.start || !insp.end) return;

                const startMarker = L.circleMarker([insp.start.lat, insp.start.lon], {
                    radius: 6,
                    color: "green",
                    fillColor: "green",
                    fillOpacity: 1,
                }).bindPopup(emp.name + "- (Start)");
                const endMarker = L.circleMarker([insp.end.lat, insp.end.lon], {
                    radius: 6,
                    color: "red",
                    fillColor: "red",
                    fillOpacity: 1,
                }).bindPopup(emp.name + "- (End)");

                this.markersGroup.addLayer(startMarker);
                this.markersGroup.addLayer(endMarker);

                insp.issues.forEach((issue) => {
                    if (issue.latitude && issue.longitude) {
                        const popupContent = `
                            <div>
                                <strong>Date:</strong> ${issue.date || "now"}<br/>
                                <strong>Issue:</strong> ${
                            issue.subject || "Unknown"
                        }<br/>
                                <button class="btn btn-primary mt-3 btn-issue-detail" data-id="${
                            issue.id
                        }">
                                    Detail
                                </button>
                            </div>
                        `;

                        const issueMarker = L.marker(
                            [issue.latitude, issue.longitude],
                            {
                                icon: warningIcon,
                            }
                        ).bindPopup(popupContent);

                        this.markersGroup.addLayer(issueMarker);
                        this.issueMarkers.push(issueMarker);
                    }
                });

                this.map.on("popupopen", (e) => {
                    const button =
                        e.popup._contentNode.querySelector(".btn-issue-detail");
                    if (button) {
                        button.addEventListener("click", () => {
                            const issueId = button.dataset.id;
                            console.log("Button clicked, dataset.id =", issueId);
                            if (issueId) {
                                this.env.services.action.doAction({
                                    type: "ir.actions.act_window",
                                    res_model: "farm.issue",
                                    res_id: parseInt(issueId, 10),
                                    views: [[false, "form"]],
                                    target: "current",
                                });
                            }
                        });
                    }
                });

                this.map.on("zoomend", () => {
                    const currentZoom = this.map.getZoom();
                    const minZoom = 14;

                    this.issueMarkers.forEach((marker) => {
                        if (currentZoom >= minZoom) {
                            if (!this.map.hasLayer(marker)) this.map.addLayer(marker);
                        } else if (this.map.hasLayer(marker))
                            this.map.removeLayer(marker);
                    });
                });

                const routeLine = L.polyline(insp.route, {
                    color,
                    weight: 3,
                    opacity: 0.8,
                    dashArray: "5,5",
                }).addTo(this.map);
                this.routeLine.push(routeLine);

                allBounds.push(
                    [insp.start.lat, insp.start.lon],
                    [insp.end.lat, insp.end.lon]
                );
            });

            const div = document.createElement("div");
            div.textContent = emp.name;
            div.style.cursor = "pointer";
            div.style.padding = "2px 0";
            div.addEventListener("click", () => this._showEmployeeRoute(emp, color));
            resultsEl.appendChild(div);
        });

        if (allBounds.length) this.map.fitBounds(allBounds);
        this._addLegend(filtered);
    }

    _addLegend(employees) {
        if (this.legendControl) this.map.removeControl(this.legendControl);

        this.legendControl = L.control({position: "bottomleft"});
        this.legendControl.onAdd = () => {
            const div = L.DomUtil.create("div", "info legend");
            div.style.background = "white";
            div.style.padding = "10px";
            div.style.borderRadius = "5px";
            div.style.fontSize = "12px";
            div.style.lineHeight = "18px";
            div.style.boxShadow = "0 0 5px rgba(0,0,0,0.3)";

            const labels = employees.map((emp, i) => {
                const color = this.routeColorsNormal[i % this.routeColorsNormal.length];
                return `<div><span style="display:inline-block;width:20px;height:3px;background:${color};margin-right:6px;"></span>${emp.name}</div>`;
            });

            div.innerHTML = labels.join("");
            return div;
        };

        this.legendControl.addTo(this.map);
    }
}

registry.category("actions").add("map_inspection_action", MapInspection);
