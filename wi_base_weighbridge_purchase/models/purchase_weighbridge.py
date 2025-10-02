from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    weighbridge_scale_ids = fields.One2many(
        comodel_name="weighbridge.scale",
        string="Weighbridge Scale",
        inverse_name="purchase_id",
    )

    weighbridge_weighbridge_id = fields.Many2one(
        comodel_name="weighbridge.weighbridge",
        string="Weighbridge",
    )

    weighbridge_scale_count = fields.Integer(
        compute="_compute_weighbridge_scale_count",
    )

    @api.depends("weighbridge_scale_ids")
    def _compute_weighbridge_scale_count(self):
        for rec in self:
            rec.weighbridge_scale_count = len(rec.weighbridge_scale_ids)

    def _create_picking(self):
        if not self.weighbridge_scale_ids:
            return super()._create_picking()

    def action_view_weighbridge_scale(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "wi_base_weighbridge.action_weighbridge_scale_view"
        )
        if len(self.weighbridge_scale_ids) > 1:
            action["views"] = [
                (
                    self.env.ref("wi_base_weighbridge.view_weighbridge_scale_tree").id,
                    "tree",
                )
            ]
            action["domain"] = [("id", "in", self.weighbridge_scale_ids.ids)]
        elif len(self.weighbridge_scale_ids) == 1:
            action["views"] = [
                (
                    self.env.ref("wi_base_weighbridge.view_weighbridge_scale_form").id,
                    "form",
                )
            ]
            action["res_id"] = self.weighbridge_scale_ids.id

        return action

    def button_cancel(self):
        res = super().button_cancel()
        for scale in self.weighbridge_scale_ids:
            if scale.state != "cancel":
                scale.action_draft()
                scale.purchase_id = False
        return res

    def button_confirm(self):
        res = super().button_confirm()
        for scale in self.weighbridge_scale_ids:
            if scale.state == "draft":
                scale.action_post()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company = self.env["res.company"].browse(vals.get("company_id")).sudo()
            weighbridge = (
                self.env["weighbridge.weighbridge"]
                .browse(vals.get("weighbridge_weighbridge_id"))
                .sudo()
            )
            separate = company.separate_purchase_sequence
            if (
                separate
                and vals.get("weighbridge_scale_ids", False)
                and weighbridge.purchase_sequence_id
            ):
                vals["name"] = weighbridge.purchase_sequence_id.next_by_id()
        res = super().create(vals_list)
        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    weighbridge_scale_id = fields.Many2one(
        comodel_name="weighbridge.scale",
        string="Weighbridge Scale",
    )

    net_weight = fields.Float(
        related="weighbridge_scale_id.net_weight",
    )

    quality_control_qty = fields.Float(
        related="weighbridge_scale_id.total_quality_control_qty",
    )

    net_after_quality_control = fields.Float(
        related="weighbridge_scale_id.net_after_quality_control",
    )

    adjustment = fields.Float(
        default="0",
    )

    @api.onchange("adjustment")
    def _onchange_adjustment(self):
        if self.weighbridge_scale_id:
            self.product_qty = self.net_after_quality_control + self.adjustment

    @api.onchange("product_id")
    def onchange_product_id(self):
        res = super().onchange_product_id()
        if self.weighbridge_scale_id:
            self.product_qty = self.net_after_quality_control + self.adjustment
        return res

    def _create_or_update_picking(self):
        if not self.weighbridge_scale_id:
            return super()._create_or_update_picking()

    @api.depends(
        "adjustment",
        "weighbridge_scale_id.state",
        "weighbridge_scale_id.net_after_quality_control",
        "weighbridge_scale_id.return_ids",
        "weighbridge_scale_id.return_ids.total_weight",
        "weighbridge_scale_id.return_ids.state",
    )
    def _compute_qty_received(self):
        res = super()._compute_qty_received()
        for line in self:
            if line.qty_received_method == "stock_moves" and line.weighbridge_scale_id:
                total = 0.0
                scale = line.weighbridge_scale_id
                if scale.state in ["posted", "locked"]:
                    total += scale.net_after_quality_control
                if len(scale.return_ids) > 0:
                    total += sum(scale.return_ids.mapped("total_weight"))
                line._track_qty_received(total)
                line.qty_received = total
        return res
