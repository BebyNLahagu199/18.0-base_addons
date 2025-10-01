/** @odoo-module **/
import {MapsController} from "@wi_base_web_maps/maps_controller";
import {MapsModel} from "@wi_base_web_maps/maps_model";
import {patch} from "@web/core/utils/patch";
import {MapsRenderer} from "@wi_base_web_maps/maps_renderer";
import {onWillStart, useRef, useState} from "@odoo/owl";
import {loadJS, loadCSS} from "@web/core/assets";

patch(MapsModel.prototype, {
    _fetchRecordsLocation(metaData, data, ids) {
        let model = metaData.resModel;
        const domain = [
            ["contact_address_complete", "!=", "False"],
            ["id", "in", ids],
        ];
        const fields = [
            "contact_address_complete",
            "location_latitude",
            "location_longitude",
            "web_maps_data",
        ];
        if (metaData.locationField !== "id") {
            model = metaData.fields[metaData.locationField].relation;
        }
        return this.orm.searchRead(model, domain, fields);
    },
});

patch(MapsController.prototype, {
    setup() {
        super.setup();
        onWillStart(() =>
            Promise.all([
                loadJS("/wi_base_web_maps/static/lib/leaflet/leaflet.js"),
                loadCSS("/wi_base_web_maps/static/lib/leaflet/leaflet.css"),
                loadJS("/web/static/lib/Chart/Chart.js"),
            ])
        );
    },
});

patch(MapsRenderer.prototype, {
    setup() {
        super.setup();
        this.weightDetail = useState({});
        this.canvasRoot = useRef("root-canvas");
        this.chart = [];
    },

    showAndCloseDetail() {
        const maps_view = document.getElementById("maps-view-coordinate");
        const detail_coordinate = document.getElementById("detail-coordinate");
        detail_coordinate.classList.remove("d-none");
        maps_view.classList.remove("col-md-10");
        maps_view.classList.add("col-md-6");
        const closeButton = $(".detail-close-btn");
        closeButton.on("click", function () {
            detail_coordinate.classList.add("d-none");
            maps_view.classList.remove("col-md-6");
            maps_view.classList.add("col-md-10");
        });
    },

    detailWeight(wmd) {
        const fields = {
            contact_address_complete: "#location-address",
            total_area: "#tot-a",
            average_weight: "#tot-aw",
            total_harvest_uom_qty: "#tot-p",
            total_tree_qty: "#tot-t",
        };

        for (const field in fields) {
            if (wmd[field]) {
                let text = "";
                if (
                    field === "total_area" ||
                    field === "total_harvest_uom_qty" ||
                    field === "average_weight"
                ) {
                    text =
                        parseFloat(wmd[field]).toFixed(2) +
                        (field === "total_area" ? " m²" : " kg");
                } else {
                    text = wmd[field];
                }
                $(fields[field]).text(text);
            } else {
                $(fields[field]).text(
                    field === "contact_address_complete"
                        ? "-"
                        : "0 " +
                              (field === "total_tree_qty"
                                  ? ""
                                  : field === "total_area"
                                  ? "m²"
                                  : "kg")
                );
            }
        }

        const detail_weight_total = [];
        const detail_weight_avg = [];
        const detail_days = [];
        var monthly = wmd.weight_data.monthly;
        var today_data = wmd.weight_data.today;
        if (monthly && monthly.length !== 0) {
            for (const rec of monthly) {
                detail_weight_total.push({
                    date_time: rec.month,
                    total_w: rec.total_weight,
                });
                detail_weight_avg.push({
                    date_time: rec.month,
                    main_product_n: rec.harvest_main_product_id,
                    other_product_n: rec.harvest_other_product_id,
                    main_avgw: rec.avg_harvest_weight,
                    other_avgw: rec.avg_other_harvest_weight,
                });
            }
            if (today_data !== undefined) {
                detail_days.push(today_data);
            }
        }
        return {
            total_weight: detail_weight_total,
            avg_weight: detail_weight_avg,
            days: detail_days,
        };
    },

    renderChart(data_weight) {
        const canvasRoot = $("#container-canvas").empty();
        this.chart.forEach((chart) => chart.destroy());
        this.chart = [];

        Object.entries(data_weight).forEach(([key, value]) => {
            if (key === "days") {
                this.renderDetailDataToday(value);
            } else {
                const canvas = $(`<canvas class="canvas-details-${key}" />`).appendTo(
                    canvasRoot
                );
                const config = this.getBarChartConfig(key, value);
                this.chart.push(new Chart(canvas, config));
            }
        });
    },

    renderDetailDataToday(data) {
        const daysLine = $("#today-line");
        $(".detail-data-today").remove();
        if (data.length === 0) {
            $(".d-no-data").removeClass("d-none");
            return;
        }
        $(".d-no-data").addClass("d-none");
        data.forEach((dayData) => {
            const rowsHTML = [
                {label: "Total Weight", key: "total_weight"},
                {label: "Average Weight", key: "avg_harvest_weight"},
                {label: "Average Other Weight", key: "avg_other_harvest_weight"},
            ]
                .map(
                    (row) => `
                <tr class="d-flex row detail-data-today">
                    <td class="d-flex col">
                        <div class="fw-bold text-wrap">${row.label}</div>
                        <div class="px-2"> : </div>
                        <div>${parseFloat(dayData[row.key]).toFixed(2)} kg</div>
                    </td>
                </tr>
            `
                )
                .join("");
            daysLine.after(rowsHTML);
        });
    },

    getBarChartConfig(keyType, data) {
        const config = {
            type: "bar",
            data: {
                labels: data.map((item) => item.date_time),
                datasets: [
                    {
                        backgroundColor: "rgba(153, 102, 255, 0.2)",
                        borderColor: "rgb(153, 102, 255)",
                        borderWidth: 1,
                        data: data.map(
                            (item) =>
                                item[
                                    keyType === "total_weight" ? "total_w" : "main_avgw"
                                ]
                        ),
                        label:
                            keyType === "total_weight"
                                ? "Total Weight"
                                : "Main Product",
                    },
                ],
            },
            options: {
                scales: {y: {beginAtZero: true}},
                plugins: {
                    title: {
                        display: true,
                        text:
                            keyType === "total_weight"
                                ? "Harvest Weight Total (kg)"
                                : "Harvest Average Weight (kg)",
                    },
                },
            },
        };
        if (keyType === "avg_weight") {
            config.data.datasets.push({
                backgroundColor: "rgba(54, 162, 235, 0.2)",
                borderColor: "rgb(54, 162, 235)",
                borderWidth: 1,
                data: data.map((item) => item.other_avgw),
                label: "Other Product",
            });
        }
        return config;
    },

    renderAnalyticBalanceGraph(analytic_balance) {
        const AnalyticCanvasRoot = $("#analytic-balance-canvas").empty();
        const canvas = $(`<canvas class="canvas-details-analytic" />`).appendTo(
            AnalyticCanvasRoot
        );
        const labels = Object.keys(analytic_balance);
        const datasets = Object.values(analytic_balance);

        // Data
        const data = {
            labels: labels,
            datasets: [
                {
                    label: "Amount",
                    data: datasets,
                    backgroundColor: "rgba(75, 192, 192, 0.2)",
                    borderColor: "rgba(75, 192, 192, 1)",
                    borderWidth: 1,
                },
            ],
        };

        // Configuration
        const config = {
            type: "bar",
            data: data,
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                    },
                },
                plugins: {
                    title: {
                        display: true,
                        text: "Analytic Balance Graph",
                    },
                },
            },
        };
        this.chart.push(new Chart(canvas, config));
    },

    detailData(record) {
        if (typeof record === "undefined") {
            return;
        }
        var web_maps_data = record.location.web_maps_data;
        var analytic_balance = web_maps_data.analytic_balance;
        this.showAndCloseDetail();
        this.renderChart(this.detailWeight(web_maps_data));
        this.renderAnalyticBalanceGraph(analytic_balance);
    },

    async centerAndOpenPin(record) {
        await super.centerAndOpenPin(record);
        var farmModel = this.props.model.env.searchModel.resModel;
        if (farmModel === "estate.estate" || farmModel === "estate.block") {
            this.detailData(record);
        }
    },
});
