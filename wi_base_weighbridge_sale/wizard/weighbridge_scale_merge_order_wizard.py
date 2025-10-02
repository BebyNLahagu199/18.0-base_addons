from odoo import models


class WeighbridgeScaleMergeOrder(models.TransientModel):
    _inherit = "weighbridge.scale.merge.order"

    def action_confirm(self):
        res = super().action_confirm()

        is_shipment = self.active_scale_ids[0].delivery_type == "shipment"
        if is_shipment:
            for rec in self.active_scale_ids:
                rec.sale_id = rec.sudo()._generate_sale_order(self.date)

        return res
