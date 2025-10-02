from odoo import models


class WeighbridgeScaleMergeOrder(models.TransientModel):
    _inherit = "weighbridge.scale.merge.order"

    def action_confirm(self):
        res = super().action_confirm()

        is_acceptance = self.active_scale_ids[0].delivery_type == "acceptance"
        if is_acceptance:
            for rec in self.active_scale_ids:
                rec.purchase_id = rec.sudo()._generate_purchase_order(self.date)

        return res
