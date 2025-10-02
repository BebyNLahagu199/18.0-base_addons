from ast import literal_eval
from datetime import date, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

SCALE_STATE = [
    ("draft", "Draft"),
    ("posted", "Posted"),
    ("locked", "Locked"),
    ("splitted", "Splitted"),
    ("merged", "Merged"),
    ("cancel", "Cancel"),
]

DELIVERY_TYPE = [("shipment", "Shipment"), ("acceptance", "Acceptance")]


class WeighbridgeScale(models.Model):
    _name = "weighbridge.scale"
    _description = "Weighbridge Scale"
    _inherit = ["portal.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "date desc, id asc, name asc"

    name = fields.Char(copy=False, default="New", required=True)

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        copy=False,
        readonly=True,
    )

    weighbridge_id = fields.Many2one(
        comodel_name="weighbridge.weighbridge",
        string="Weighbridge",
        help="Weighbridge used for this ticket.",
        copy=False,
        required=True,
    )

    quality_control_ids = fields.One2many(
        comodel_name="weighbridge.quality.control",
        inverse_name="weighbridge_scale_id",
        string="Quality Control",
        copy=False,
    )

    penalty_ids = fields.One2many(
        comodel_name="weighbridge.quality.control.penalty",
        inverse_name="weighbridge_scale_id",
        string="Penalty",
        readonly=True,
        copy=False,
    )

    source_id = fields.Many2one(
        comodel_name="weighbridge.scale",
        help="If the ticket is return, this field will be filled with the source id.",
    )

    source_type = fields.Selection(
        selection=[("split", "Split"), ("return", "Return")],
        compute="_compute_source_type",
    )

    source_ids = fields.One2many(
        string="Source Tickets",
        comodel_name="weighbridge.scale",
        inverse_name="merged_to",
        help="""
            If the ticket is merged,
            this field will be filled with the source ids.
        """,
    )

    merged_to = fields.Many2one(
        comodel_name="weighbridge.scale",
        help="""
            If the ticket is merged,
            this field will be filled with the merged to id.
        """,
    )

    return_ids = fields.One2many(
        comodel_name="weighbridge.scale",
        inverse_name="source_id",
        domain=[("is_return", "=", True)],
        help="If there is a return, this field will be filled with the return id.",
    )

    return_count = fields.Integer(
        compute="_compute_return_count",
    )

    date = fields.Date(
        default=date.today(),
        help="Ticket Date.",
        required=True,
    )

    delivery_number = fields.Char(
        copy=False,
        default=False,
        tracking=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        help="Delivered/Received Product.",
        tracking=True,
        required=True,
    )

    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM",
        tracking=True,
        related="product_id.uom_id",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        tracking=True,
        required=True,
        copy=False,
    )

    transporter_id = fields.Many2one(
        comodel_name="res.partner",
        string="Transporter",
        tracking=True,
    )

    driver_name = fields.Char(
        string="Driver",
    )

    driver_identity_no = fields.Char(
        string="ID Card",
    )

    licence_plate = fields.Char()

    state = fields.Selection(
        selection=SCALE_STATE,
        default="draft",
        help="State of the ticket.",
        tracking=True,
    )

    is_transfer = fields.Boolean(
        string="Ticket Transfer",
        default=False,
        help="Is this ticket for a transfer transaction?",
    )

    is_return = fields.Boolean(
        string="Return Ticket",
        default=False,
        copy=False,
        help="Is this ticket for a return transaction?",
    )

    quantity = fields.Float(
        tracking=True,
        help="Quantity of product received/delivered",
    )

    weight_in = fields.Float(
        help="Weight of transportation when arriving.",
        tracking=True,
        copy=False,
    )

    weight_out = fields.Float(
        help="Weight of transportation when leaving.", tracking=True, copy=False
    )

    net_weight = fields.Float(
        compute="_compute_net_weight",
        compute_sudo=True,
        store=True,
        help="Net Weigth of product received/delivered",
        tracking=True,
        readonly=True,
    )

    vehicle_in = fields.Datetime(string="Vehicle Time In", default=datetime.now())

    vehicle_out = fields.Datetime(string="Vehicle Time Out", default=datetime.now())

    vehicle_duration = fields.Float(
        string="Duration",
        compute="_compute_count_duration",
        store=True,
    )

    unload_in = fields.Float(
        compute="_compute_unload_qty",
        compute_sudo=True,
        store=True,
        readonly=False,
        tracking=True,
    )

    unload_out = fields.Float(
        compute="_compute_unload_qty",
        compute_sudo=True,
        store=True,
        readonly=False,
        tracking=True,
    )

    unload_date = fields.Datetime(tracking=True)

    additional_unload = fields.Float(default=0)

    net_unload_after = fields.Float(
        compute="_compute_netto_unload_after_qty",
        store=True,
        readonly=True,
    )

    net_unload = fields.Float(
        compute="_compute_netto_unload_qty",
        store=True,
    )

    delivery_type = fields.Selection(
        selection=DELIVERY_TYPE,
        default=False,
        compute="_compute_net_weight",
        compute_sudo=True,
        store=True,
    )

    remark = fields.Text()

    shrinkage = fields.Float(
        compute="_compute_shrinkage",
        store=True,
        compute_sudo=True,
        copy=False,
    )

    shrinkage_percentage = fields.Float(
        compute="_compute_shrinkage",
        string="Percentage (%)",
        store=True,
        compute_sudo=True,
    )

    move_ids = fields.One2many(
        comodel_name="stock.move",
        string="Stock Move",
        inverse_name="scale_id",
    )

    gross_quality_control = fields.Float(
        copy=False,
        default=0,
        help="Quality Control Weight before quality control data",
    )

    total_quality_control_qty = fields.Float(
        compute="_compute_net_after_quality_control",
        compute_sudo=True,
        store=True,
    )

    net_after_quality_control = fields.Float(
        compute="_compute_net_after_quality_control",
        compute_sudo=True,
        store=True,
    )

    total_weight = fields.Float(
        compute="_compute_net_after_quality_control",
        compute_sudo=True,
        store=True,
    )

    is_merge = fields.Boolean(
        compute="_compute_is_merge",
    )

    load_ids = fields.One2many(
        comodel_name="weighbridge.load",
        inverse_name="scale_id",
        string="Load",
    )
    seal_number = fields.Char()

    @api.depends("source_ids")
    def _compute_is_merge(self):
        for rec in self:
            rec.is_merge = len(rec.source_ids) > 0

    @api.onchange("partner_id")
    def _onchange_partner(self):
        if self.partner_id == self.company_id.partner_id:
            self.is_transfer = True

    @api.depends("weight_in", "weight_out")
    def _compute_net_weight(self):
        # Compute Net Weight and Delivery Type
        for rec in self:
            net_weight = rec.weight_in - rec.weight_out
            vals = {"net_weight": abs(net_weight)}
            if net_weight > 0:
                vals["delivery_type"] = "acceptance"
            elif net_weight < 0:
                vals["delivery_type"] = "shipment"
            else:
                vals["delivery_type"] = False
            rec.write(vals)

    @api.depends("vehicle_in", "vehicle_out")
    def _compute_count_duration(self):
        # Compute Vehicle Duration
        for rec in self:
            if rec.vehicle_in and rec.vehicle_out:
                if rec.vehicle_in > rec.vehicle_out:
                    raise UserError(
                        _("Vehicle Time Out cannot be earlier than Vehicle Time In.")
                    )
                rec.vehicle_duration = (
                    rec.vehicle_out - rec.vehicle_in
                ).total_seconds() / 3600

    @api.depends("weight_in", "weight_out")
    def _compute_unload_qty(self):
        # Compute Unload Qty
        for rec in self:
            if rec.unload_in == 0:
                rec.unload_in = rec.weight_out
            if rec.unload_out == 0:
                rec.unload_out = rec.weight_in

    @api.depends("unload_in", "unload_out")
    def _compute_netto_unload_qty(self):
        # Compute Netto Unload Qty
        for rec in self:
            if rec.unload_in and rec.unload_out:
                rec.net_unload = abs(rec.unload_in - rec.unload_out)

    @api.depends("net_unload", "additional_unload")
    def _compute_netto_unload_after_qty(self):
        # Compute Netto Unload After Qty
        for rec in self:
            rec.net_unload_after = rec.net_unload - rec.additional_unload

    @api.depends(
        "net_weight",
        "penalty_ids.quality_control_id",
        "penalty_ids.quality_control_id.penalty_qty_total",
        "state",
        "gross_quality_control",
        "shrinkage",
        "is_return",
    )
    def _compute_net_after_quality_control(self):
        for rec in self:
            if rec.penalty_ids.quality_control_id:
                quality_control = rec.penalty_ids.quality_control_id.filtered(
                    lambda x: x.state != "cancel"
                )
                quality_control_qty = sum(quality_control.mapped("penalty_qty_total"))
                net_weight = rec.net_weight - quality_control_qty
                rec.total_quality_control_qty = quality_control_qty
                rec.net_after_quality_control = net_weight
            else:
                rec.total_quality_control_qty = rec.gross_quality_control
                rec.net_after_quality_control = (
                    rec.net_weight - rec.gross_quality_control
                )
            total = rec.net_after_quality_control + rec.shrinkage
            rec.total_weight = (
                abs(rec.net_after_quality_control) if not rec.is_return else -total
            )

    @api.depends("net_weight", "net_unload")
    def _compute_shrinkage(self):
        for rec in self:
            vals = {
                "shrinkage": abs(rec.net_weight - rec.net_unload),
                "shrinkage_percentage": abs(rec.net_weight - rec.net_unload)
                / rec.net_weight
                * 100
                if rec.net_weight
                else 0,
            }
            rec.write(vals)

    def _compute_source_type(self):
        for rec in self:
            if rec.source_id.return_count != 0:
                rec.source_type = "return"
            elif rec.source_id:
                rec.source_type = "split"
            else:
                rec.source_type = False

    def _compute_return_count(self):
        for rec in self:
            rec.return_count = len(rec.return_ids)

    def action_post(self):
        err_msg = "Cannot post delivery, There's no net weight for this delivery."
        # Raise error if there's no net weight
        for rec in self:
            if rec.net_weight == 0:
                raise UserError(_(err_msg))
            if rec.state == "draft":
                rec.write({"state": "posted"})
                rec._generate_stock_move()
                for quality_control in rec.quality_control_ids:
                    quality_control.action_post()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("weighbridge.scale")
        return super().create(vals_list)

    def action_cancel(self):
        self.write({"state": "cancel"})
        if self.state != "draft":
            self.move_ids.mapped(lambda move: move.write({"scale_id": False}))
            self._cancel_stock_move()
        for quality_control in self.quality_control_ids:
            quality_control.action_cancel()

    def action_lock(self):
        if self.state == "posted":
            self.write({"state": "locked"})
            for quality_control in self.quality_control_ids:
                quality_control.action_lock()

    def action_unlock(self):
        if self.state == "locked":
            self.write({"state": "posted"})
            for quality_control in self.quality_control_ids:
                quality_control.action_unlock()

    def action_draft(self):
        self.write({"state": "draft"})
        for quality_control in self.quality_control_ids:
            quality_control.action_draft()

    def action_return(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "wi_base_weighbridge.weighbridge_scale_return_action"
        )
        return action

    def _generate_stock_move(self):
        source_loc_id, dest_loc_id = self._get_stock_location()
        move_vals = self._prepare_move_values(source_loc_id, dest_loc_id)
        move_id = (
            self.move_ids.sudo().with_context(inventory_mode=False).create(move_vals)
        )
        move_id._action_done(cancel_backorder=False)

    def _prepare_move_values(self, src_location, dest_location, cancel=False):
        self.ensure_one()
        return {
            "name": "Acceptance: " + self.name
            if self.delivery_type == "acceptance"
            else "Shipment: " + self.name,
            "product_id": self.product_id.id,
            "product_uom": self.uom_id.id,
            "product_uom_qty": self.net_after_quality_control,
            "origin": self.name,
            "company_id": self.company_id.id,
            "state": "confirmed",
            "location_id": src_location.id,
            "location_dest_id": dest_location.id,
            "is_inventory": True,
            "scale_id": self.id if not cancel else False,
            "picked": True,
            "move_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product_id.id,
                        "product_uom_id": self.uom_id.id,
                        "quantity": self.net_after_quality_control,
                        "location_id": src_location.id,
                        "location_dest_id": dest_location.id,
                        "company_id": self.company_id.id,
                    },
                )
            ],
        }

    def _get_stock_location(self):
        source_location_id = (
            self.partner_id.property_stock_supplier
            if self.delivery_type == "acceptance"
            else self.weighbridge_id.location_stock_id
        )
        destination_location_id = (
            self.weighbridge_id.location_stock_id
            if self.delivery_type == "acceptance"
            else self.partner_id.property_stock_customer
        )
        return source_location_id, destination_location_id

    def _cancel_stock_move(self):
        dest_loc_id, source_loc_id = self._get_stock_location()
        move_vals = self._prepare_move_values(source_loc_id, dest_loc_id, cancel=True)
        move_id = (
            self.move_ids.sudo().with_context(inventory_mode=False).create(move_vals)
        )
        move_id._action_done(cancel_backorder=False)

    def action_return_weighbridge_scale_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_scale_view",
            params="return",
        )

    def action_return_from_weighbridge_scale_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_scale_view",
            params="return_from",
        )

    def action_splitted_weighbridge_scale_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_scale_view",
            params="split",
        )

    def action_splitted_from_weighbridge_scale_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_scale_view",
            params="split_from",
        )

    def action_merged_weighbridge_scale_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_scale_view",
            params="merge",
        )

    def action_merged_from_weighbridge_scale_tree(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_scale_view",
            params="merge_from",
        )

    def _get_action(self, action_xmlid, params=False):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action["display_name"] = "Scale - %s" % self.name
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
                    self.env.ref("wi_base_weighbridge.view_weighbridge_scale_form").id,
                    "form",
                )
            ]
            action["res_id"] = to_view_id.id
        return action

    def _get_view_id(self, params):
        scale_object = self.env["weighbridge.scale"]
        if params == "split":
            to_view = scale_object.search([("source_id", "=", self.id)])
        elif params == "split_from":
            to_view = scale_object.search(
                [("id", "=", self.source_id.id), ("is_return", "!=", True)]
            )
        elif params == "return":
            to_view = scale_object.search([("id", "in", self.return_ids.ids)])
        elif params == "return_from":
            to_view = scale_object.search(
                [("id", "=", self.source_id.id), ("return_count", "!=", 0)]
            )
        elif params == "merge":
            to_view = scale_object.search([("id", "=", self.merged_to.id)])
        elif params == "merge_from":
            to_view = scale_object.search([("id", "in", self.source_ids.ids)])
        return to_view

    def _compute_access_url(self):
        res = super()._compute_access_url()
        for order in self:
            order.access_url = "/my/weighbridge/%s" % (order.id)
        return res

    def _get_report_base_filename(self):
        self.ensure_one()
        return "%s" % (self.name)

    def action_preview_portal(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": self.get_portal_url(),
        }


class StockMove(models.Model):
    _inherit = "stock.move"

    scale_id = fields.Many2one(
        comodel_name="weighbridge.scale",
        string="Weighbridge Scale",
    )


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    scale_id = fields.Many2one(
        related="move_id.scale_id",
        string="Weighbridge Scale",
    )

    scale_type = fields.Selection(
        related="scale_id.delivery_type",
        string="Scale Type",
    )
