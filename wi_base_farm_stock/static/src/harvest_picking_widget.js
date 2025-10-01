/** @odoo-module */

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField, x2ManyField} from "@web/views/fields/x2many/x2many_field";

export class HarvestLinesRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.threadService = useService("mail.thread");
    }
}

export class HarvestPickingWidget extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: HarvestLinesRenderer,
    };

    setup() {
        super.setup();
        this.canOpenRecord = false;
        this.activeActions.create = false;
    }

    computeActiveActions(props) {
        super.computeActiveActions(props);
        const activeActions = this.state.activeActions;
        activeActions.create = false;
        activeActions.createEdit = false;
    }

    get isMany2Many() {
        // The field is used like a many2many to allow for adding existing lines to the sheet.
        return true;
    }
}

export const harvestPickingWidget = {
    ...x2ManyField,
    component: HarvestPickingWidget,
};

registry.category("fields").add("harvest_picking_widget", harvestPickingWidget);
