/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {MapsArchParser} from "./maps_arch_parser";
import {MapsModel} from "./maps_model";
import {MapsController} from "./maps_controller";
import {MapsRenderer} from "./maps_renderer";

export const mapsView = {
    type: "map",
    display_name: _t("Maps"),
    icon: "fa fa-map",
    multiRecord: true,
    Controller: MapsController,
    Renderer: MapsRenderer,
    Model: MapsModel,
    ArchParser: MapsArchParser,
    buttonTemplate: "wi_base_web_maps.MapsView.Buttons",

    props: (genericProps, view, config) => {
        let modelParams = genericProps.state;
        if (!modelParams) {
            const {arch, resModel, fields, context} = genericProps;
            const parser = new view.ArchParser();
            const archInfo = parser.parse(arch);
            const views = config.views || [];
            modelParams = {
                context: context,
                defaultOrder: archInfo.defaultOrder,
                fieldNames: archInfo.fieldNames,
                fieldNamesMarkerPopup: archInfo.fieldNamesMarkerPopup,
                fields: fields,
                hasFormView: views.some((view_type) => view_type[1] === "form"),
                hideAddress: archInfo.hideAddress || false,
                hideName: archInfo.hideName || false,
                hideTitle: archInfo.hideTitle || false,
                limit: archInfo.limit || 80,
                numbering: archInfo.routing || false,
                offset: 0,
                panelTitle:
                    archInfo.panelTitle || config.getDisplayName() || _t("Items"),
                resModel: resModel,
                locationField: archInfo.locationField,
                routing: archInfo.routing || false,
            };
        }

        return {
            ...genericProps,
            Model: view.Model,
            modelParams,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
        };
    },
};

registry.category("views").add("maps", mapsView);
