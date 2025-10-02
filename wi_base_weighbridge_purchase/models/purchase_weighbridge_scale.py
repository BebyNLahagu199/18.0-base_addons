from odoo import fields, models


class WeighbridgeScale(models.Model):
    _inherit = "weighbridge.scale"

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
    )

    def action_post(self):
        res = super().action_post()

        date_ref = self[0].date
        is_all_acceptance = all(data.delivery_type == "acceptance" for data in self)
        is_diff_date = any(data.date != date_ref for data in self)
        merge_po = self.company_id.merge_purchase_order
        if is_all_acceptance and merge_po and (1 < len(self) <= 80) and is_diff_date:
            return self._trigger_wizard()
        else:
            for rec in self:
                if rec.delivery_type == "acceptance" and not rec.is_return:
                    rec.purchase_id = rec.sudo()._generate_purchase_order()

        return res

    def _trigger_wizard(self):
        new_wizard = self.env["weighbridge.scale.merge.order"].create({})
        return {
            "type": "ir.actions.act_window",
            "name": "Merge PO",
            "res_model": "weighbridge.scale.merge.order",
            "view_mode": "form",
            "target": "new",
            "res_id": new_wizard.id,
            "view_id": self.env.ref(
                "wi_base_weighbridge.weighbridge_scale_merge_order_wizard_view"
            ).id,
        }

    def _generate_purchase_order(self, date=False):
        """Generate a purchase order using the vendor's parent company
        if the setting is enabled.
        If no parent company exists, use the original vendor.
        Merges purchase orders if enabled, otherwise creates a new one.
        """

        date = self.date if not date else date
        merge_po = self.company_id.merge_purchase_order

        use_parent_company = self.company_id.purchase_to_parent_company

        partner_id = self.partner_id.id
        if use_parent_company and self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id.id

        if not partner_id:
            return False

        purchase_order = self.env["purchase.order"].search(
            [
                ("weighbridge_weighbridge_id", "=", self.weighbridge_id.id),
                ("date_order", "=", date),
                ("partner_id", "=", partner_id),
                ("state", "!=", "cancel"),
            ]
        )

        if purchase_order and merge_po:
            # Merge with existing purchase order
            purchase_order_line_data = self._prepare_purchase_order_line(date=date)
            purchase_order.write({"order_line": [(0, 0, purchase_order_line_data)]})

            # Update partner reference
            if purchase_order.partner_ref and self.delivery_number:
                purchase_order.partner_ref += ", %s" % self.delivery_number
            elif self.delivery_number:
                purchase_order.partner_ref = self.delivery_number

            # Update origin field
            purchase_order.origin += ", %s" % self.name
            purchase_id = purchase_order.id

        else:
            purchase_order_line_data = self._prepare_purchase_order_line(date=date)
            purchase_order_data = self._prepare_purchase_order(
                purchase_order_line_data, date=date
            )

            purchase_order_data["partner_id"] = partner_id

            purchase_id = self.env["purchase.order"].create(purchase_order_data)
            purchase_id.button_confirm()
            purchase_id.date_approve = purchase_id.date_planned

        return purchase_id

    def _prepare_purchase_order_line(self, date=False):
        date = self.date if not date else date
        return {
            "weighbridge_scale_id": self.id,
            "product_id": self.product_id.id,
            "name": "%s : %s" % (self.name, self.product_id.display_name),
            "date_planned": date,
            "product_qty": self.net_after_quality_control,
            "product_uom": self.uom_id.id,
            "date_order": date,
        }

    def _prepare_purchase_order(self, purchase_order_line, date=False):
        date = self.date if not date else date
        return {
            "weighbridge_scale_ids": self,
            "weighbridge_weighbridge_id": self.weighbridge_id.id,
            "partner_id": self.partner_id.id,
            "date_approve": date,
            "date_planned": date,
            "date_order": date,
            "order_line": [(0, 0, purchase_order_line)],
            "company_id": self.company_id.id,
            "origin": self.name,
            "partner_ref": self.delivery_number,
        }

    def action_view_purchase_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "wi_base_weighbridge_purchase.action_purchase_weighbridge_purchase_view"
        )
        action["views"] = [
            (
                self.env.ref(
                    "wi_base_weighbridge_purchase.purchase_order_view_form_inherit_weighbridge"
                ).id,
                "form",
            )
        ]
        action["res_id"] = self.purchase_id.id

        return action

    def action_cancel(self):
        res = super().action_cancel()

        if self.purchase_id:
            if len(self.purchase_id.order_line) > 1:
                purchase_order_line = self.env["purchase.order.line"].search(
                    [
                        ("weighbridge_scale_id", "=", self.id),
                    ]
                )
                self.purchase_id.button_draft()
                self.purchase_id.order_line = [(2, purchase_order_line.id)]
                self.purchase_id.button_confirm()
            elif len(self.purchase_id.order_line) == 1:
                self.purchase_id.button_cancel()
            self.purchase_id = False

        return res


class WeighbridgeScaleReturn(models.TransientModel):
    _inherit = "weighbridge.scale.return"

    def _prepare_field_to_update(self, weighbridge_scale):
        res = super()._prepare_field_to_update(weighbridge_scale)
        res["purchase_id"] = False
        return res
