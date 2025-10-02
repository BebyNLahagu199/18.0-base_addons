from datetime import timedelta

from odoo import fields, models


class WeighbridgeScale(models.Model):
    _inherit = "weighbridge.scale"

    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
    )

    def action_post(self):
        res = super().action_post()

        date_ref = self[0].date
        is_all_shipment = all(data.delivery_type == "shipment" for data in self)
        is_diff_date = any(data.date != date_ref for data in self)
        merge_so = self.company_id.merge_sale_order

        if is_all_shipment and merge_so and (1 < len(self) <= 80) and is_diff_date:
            return self._trigger_wizard()
        else:
            for rec in self:
                if rec.delivery_type == "shipment" and not rec.is_return:
                    rec.sale_id = rec.sudo()._generate_sale_order()

        return res

    def _trigger_wizard(self):
        new_wizard = self.env["weighbridge.scale.merge.order"].create({})
        return {
            "type": "ir.actions.act_window",
            "name": "Merge SO",
            "res_model": "weighbridge.scale.merge.order",
            "view_mode": "form",
            "target": "new",
            "res_id": new_wizard.id,
            "view_id": self.env.ref(
                "wi_base_weighbridge.weighbridge_scale_merge_order_wizard_view"
            ).id,
        }

    def _generate_sale_order(self, date=False):
        date = self.date if not date else date
        merge_so = self.company_id.merge_sale_order
        date_start = date
        date_end = date_start + timedelta(days=1)
        partner_id = self.partner_id.id
        if self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id.id
        sale_order = self.env["sale.order"].search(
            [
                ("weighbridge_weighbridge_id", "=", self.weighbridge_id.id),
                ("validity_date", ">=", date_start),
                ("validity_date", "<", date_end),
                ("partner_id", "=", partner_id),
                ("state", "!=", "cancel"),
            ]
        )
        if sale_order and merge_so:
            sale_order_line_data = self._prepare_sale_order_line(date=date)
            sale_order["order_line"] = [(0, 0, sale_order_line_data)]
            if sale_order["client_order_ref"] and self.delivery_number:
                sale_order["client_order_ref"] += ", %s" % self.delivery_number
            elif self.delivery_number:
                sale_order["client_order_ref"] = self.delivery_number
            sale_id = sale_order.id
        else:
            sale_order_line_data = self._prepare_sale_order_line(date=date)
            sale_order_data = self._prepare_sale_order(sale_order_line_data, date=date)
            sale_id = sale_order.create(sale_order_data)
            sale_id.action_confirm()

        return sale_id

    def _prepare_sale_order_line(self, date=False):
        date = self.date if not date else date
        return {
            "weighbridge_scale_id": self.id,
            "product_id": self.product_id.id,
            "name": "%s : %s" % (self.name, self.product_id.display_name),
            "product_uom_qty": self.net_after_quality_control,
            "product_uom": self.uom_id.id,
            "scheduled_date": date,
        }

    def _prepare_sale_order(self, sale_order_line, date=False):
        date = self.date if not date else date
        return {
            "weighbridge_scale_ids": self,
            "weighbridge_weighbridge_id": self.weighbridge_id.id,
            "partner_id": self.partner_id.id,
            "validity_date": date,
            "order_line": [(0, 0, sale_order_line)],
            "company_id": self.company_id.id,
            "origin": self.name,
            "client_order_ref": self.delivery_number,
        }

    def action_view_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "wi_base_weighbridge_sale.action_sale_weighbridge_sale_view"
        )
        action["views"] = [
            (
                self.env.ref(
                    "wi_base_weighbridge_sale.sale_order_view_form_inherit_weighbridge"
                ).id,
                "form",
            )
        ]
        action["res_id"] = self.sale_id.id

        return action

    def action_cancel(self):
        self.env.context = dict(self.env.context, disable_cancel_warning=True)

        res = super().action_cancel()

        if self.sale_id:
            if len(self.sale_id.order_line) > 1:
                sale_order_line = self.sale_id.order_line.filtered(
                    lambda x: x.weighbridge_scale_id.id == self.id
                )
                self.sale_id.action_draft()
                self.sale_id.order_line = [(2, sale_order_line.id)]
                self.sale_id.action_confirm()
            elif len(self.sale_id.order_line) == 1:
                self.sale_id.action_cancel()
            self.sale_id = False

        return res


class WeighbridgeScaleReturn(models.TransientModel):
    _inherit = "weighbridge.scale.return"

    def _prepare_field_to_update(self, weighbridge_scale):
        res = super()._prepare_field_to_update(weighbridge_scale)
        res["sale_id"] = False
        return res
