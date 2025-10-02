from ast import literal_eval
from datetime import date

from odoo import _, api, fields, models

QUALITY_CONTROL_STATE = [
    ("draft", "Draft"),
    ("posted", "Posted"),
    ("locked", "Locked"),
    ("splitted", "Splitted"),
    ("merged", "Merged"),
    ("cancel", "Cancel"),
]

CALCULATION_TYPE = [
    ("per_qty", "Per Quantity"),
    ("per_unit", "Per Unit"),
    ("percentage", "Percentage"),
]


class WeighbridgeQualityControl(models.Model):
    _name = "weighbridge.quality.control"
    _description = "Weighbridge Quality Control"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"

    name = fields.Char(copy=False, default="New")

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    weighbridge_id = fields.Many2one(
        comodel_name="weighbridge.weighbridge",
        string="Weighbridge",
        help="Weighbridge used for this quality control.",
        related="weighbridge_scale_id.weighbridge_id",
    )

    date = fields.Date(
        default=date.today(),
        help="Quality Control Date.",
    )

    delivery_number = fields.Char(
        copy=False,
        default=False,
        tracking=True,
    )

    state = fields.Selection(
        selection=QUALITY_CONTROL_STATE,
        default="draft",
        copy=False,
        help="State of the Quality Control.",
        tracking=True,
    )

    type = fields.Selection(
        copy=False,
        help="Type of the Quality Control.",
        readonly=True,
        related="weighbridge_scale_id.weighbridge_id.type",
    )

    weighbridge_scale_id = fields.Many2one(
        comodel_name="weighbridge.scale",
        string="Weighbridge Scale",
        help="Weighbridge Scale.",
        copy=False,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        related="weighbridge_scale_id.product_id",
        store=True,
    )

    penalty_ids = fields.One2many(
        comodel_name="weighbridge.quality.control.penalty",
        inverse_name="quality_control_id",
        string="Penalty",
    )

    return_ids = fields.One2many(
        comodel_name="weighbridge.quality.control.return",
        inverse_name="quality_control_id",
        string="Return",
    )

    scale_qty = fields.Float(
        string="Scale Quantity",
        copy=False,
        default=0,
        compute="_compute_scale_qty",
        compute_sudo=True,
        store=True,
    )

    penalty_qty_total = fields.Float(
        compute="_compute_penalty_total",
        compute_sudo=True,
        store=True,
    )

    return_qty_total = fields.Float(
        compute="_compute_return_total",
        compute_sudo=True,
        store=True,
    )

    source_id = fields.Many2one(
        comodel_name="weighbridge.quality.control",
        help="""
            If the quality control is splitted,
            this field will be filled with the source id.
        """,
    )

    source_ids = fields.One2many(
        string="Source Quality Controls",
        comodel_name="weighbridge.quality.control",
        inverse_name="merged_to",
        help="""
            If the quality control is merged,
            this field will be filled with the source ids.
        """,
    )

    merged_to = fields.Many2one(
        comodel_name="weighbridge.quality.control",
        help="""
            If the quality control is merged,
            this field will be filled with the merged to id.
        """,
    )

    is_merge = fields.Boolean(
        compute="_compute_is_merge",
    )

    @api.depends("source_ids")
    def _compute_is_merge(self):
        for rec in self:
            rec.is_merge = len(rec.source_ids) > 0

    @api.depends("weighbridge_scale_id", "weighbridge_scale_id.net_weight")
    def _compute_scale_qty(self):
        # Compute Scale Quantity
        for record in self:
            record.scale_qty = record.weighbridge_scale_id.net_weight

    @api.depends("penalty_ids", "penalty_ids.penalty_subtotal")
    def _compute_penalty_total(self):
        # Compute Penalty Total from Penalty Ids
        for record in self:
            record.penalty_qty_total = sum(
                record.penalty_ids.mapped("penalty_subtotal")
            )

    @api.depends("return_ids", "return_ids.return_qty")
    def _compute_return_total(self):
        # Compute Return Total from Return Ids
        for record in self:
            record.return_qty_total = sum(record.return_ids.mapped("return_qty"))

    def action_post(self):
        if self.state == "draft":
            self.write({"state": "posted"})

    def action_lock(self):
        self.write({"state": "locked"})

    def action_unlock(self):
        self.write({"state": "posted"})

    def action_cancel(self):
        if self.state == "posted":
            self.write({"state": "cancel"})

    def action_draft(self):
        self.write({"state": "draft"})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "weighbridge.quality.control"
                )
        return super().create(vals_list)

    def action_splitted_quality_control_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_quality_control_view",
            params="split",
        )

    def action_splitted_from_quality_control_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_quality_control_view",
            params="split_from",
        )

    def action_merged_quality_control_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_quality_control_view",
            params="merge",
        )

    def action_merged_from_quality_control_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_quality_control_view",
            params="merge_from",
        )

    def _get_action(self, action_xmlid, params=False):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action["display_name"] = "Quality Control - %s" % self.name
        context = {
            "default_company_id": self.company_id.id,
        }
        action_context = literal_eval(action["context"])
        context = {**action_context, **context}
        action["context"] = context
        to_view_id = self._get_view_id(params)
        if len(to_view_id) > 1:
            action["domain"] = [("id", "in", to_view_id.ids)]
        elif len(to_view_id) == 1:
            action["views"] = [
                (
                    self.env.ref(
                        "wi_base_weighbridge.view_weighbridge_quality_control_form"
                    ).id,
                    "form",
                )
            ]
            action["res_id"] = to_view_id.id
        return action

    def _get_view_id(self, params):
        qc_object = self.env["weighbridge.quality.control"]
        if params == "split":
            to_view = qc_object.search([("source_id", "=", self.id)])
        elif params == "split_from":
            to_view = qc_object.search([("id", "=", self.source_id.id)])
        elif params == "merge":
            to_view = qc_object.search([("id", "=", self.merged_to.id)])
        elif params == "merge_from":
            to_view = qc_object.search([("id", "in", self.source_ids.ids)])
        return to_view


class WeighbridgeQualityControlPenalty(models.Model):
    _name = "weighbridge.quality.control.penalty"
    _description = "Weighbridge Quality Control Penalty"

    quality_control_id = fields.Many2one(
        comodel_name="weighbridge.quality.control",
        string="Quality Control",
        ondelete="cascade",
        copy=False,
    )

    weighbridge_scale_id = fields.Many2one(
        comodel_name="weighbridge.scale",
        string="Weighbridge Scale",
        help="Weighbridge Scale.",
        related="quality_control_id.weighbridge_scale_id",
    )

    penalty_id = fields.Many2one(
        comodel_name="weighbridge.quality.type",
        string="Penalty",
        domain="[('categories','in',['deduction','quality'])]",
        copy=False,
    )

    penalty_qty = fields.Float(
        string="Quantity",
        copy=False,
        help="""Penalty calculation based on calculation type,
        1. Per Quantity: Quantity Unit.
        2. Percentage: Scale Quantity * (Quantity/100).
        """,
    )

    calculation_type = fields.Selection(
        selection=CALCULATION_TYPE,
        compute="_compute_calculation_type",
        store=True,
        readonly=True,
    )

    penalty_subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_penalty_subtotal",
        compute_sudo=True,
        store=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    @api.depends("penalty_id")
    def _compute_calculation_type(self):
        # Compute Calculation Type
        for record in self:
            if record.penalty_id and not record.calculation_type:
                record.calculation_type = record.penalty_id.calculation_type

    @api.depends("penalty_id", "penalty_qty", "calculation_type")
    def _compute_penalty_subtotal(self):
        # Compute Penalty Subtotal
        for record in self:
            if record.penalty_id and record.penalty_qty:
                scale_qty = record.quality_control_id.scale_qty
                if record.calculation_type == "per_qty":
                    record.penalty_subtotal = record.penalty_qty
                elif record.calculation_type == "per_unit":
                    record.penalty_subtotal = 0
                elif record.calculation_type == "percentage":
                    record.penalty_subtotal = scale_qty * (record.penalty_qty / 100)


class WeighbridgeQualityControlReturn(models.Model):
    _name = "weighbridge.quality.control.return"
    _description = "Weighbridge Quality Control Return"

    quality_control_id = fields.Many2one(
        comodel_name="weighbridge.quality.control",
        string="Quality Control",
        ondelete="cascade",
        copy=False,
    )

    weighbridge_scale_id = fields.Many2one(
        comodel_name="weighbridge.scale",
        string="Weighbridge Scale",
        help="Weighbridge Scale.",
        related="quality_control_id.weighbridge_scale_id",
    )

    return_id = fields.Many2one(
        comodel_name="weighbridge.quality.type",
        string="Return",
        domain="[('categories','in',['return','fraction'])]",
        copy=False,
    )

    return_qty = fields.Float(
        string="Quantity",
        copy=False,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )
