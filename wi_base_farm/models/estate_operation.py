from ast import literal_eval
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OperationType(models.Model):
    _name = "estate.operation.type"
    _description = "Estate Operation Type"

    name = fields.Char(required=True, string="Type of Operation")
    color = fields.Integer()
    code = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    required_validation = fields.Boolean(
        related="company_id.required_operation_validation",
        string="Required Validation",
        readonly=True,
    )
    active = fields.Boolean(default=True)
    type_operation = fields.Selection(
        [
            ("harvest", "Harvest"),
            ("upkeep", "Upkeep"),
        ]
    )

    # Overview Fields
    count_draft = fields.Integer(compute="_compute_count")
    count_validate = fields.Integer(compute="_compute_count")

    def _compute_count(self):
        domains = {
            "count_draft": [("state", "=", "draft")],
            "count_validate": [("state", "=", "validate")],
        }
        for field in domains:
            data = self.env["estate.operation"].read_group(
                domains[field]
                + [
                    ("operation_type_id", "in", self.ids),
                ],
                ["operation_type_id"],
                ["operation_type_id"],
            )

            count = {
                x["operation_type_id"][0]: x["operation_type_id_count"]
                for x in data
                if x["operation_type_id"]
            }
            for rec in self:
                rec[field] = count.get(rec.id, 0)

    # Overview Actions
    def _get_action(self, action_xmlid, params=False, reports=False):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action["display_name"] = self.name
        context = {
            "search_default_operation_type_id": [self.id],
            "default_operation_type_id": self.id,
            "default_company_id": self.company_id.id,
            "is_harvest": self.type_operation == "harvest",
        }
        action_context = literal_eval(action["context"])
        context = {**action_context, **context}
        action["context"] = context
        domain = self._compute_action_domain(action, params, reports)
        action["domain"] = domain
        return action

    def _compute_action_domain(self, action, params=None, reports=False):
        action_domain = literal_eval(action["domain"]) if action["domain"] else []
        if reports:
            domain = ("estate_operation_id.operation_type_id", "=", self.id)
            action_domain.append(domain)
        if params:
            domain_state = [("state", "=", params), ("operation_type_id", "=", self.id)]
            action_domain.extend(domain_state)
        return action_domain

    def action_create_new(self):
        return {
            "name": _("Create New"),
            "type": "ir.actions.act_window",
            "res_model": "estate.operation",
            "view_mode": "form",
            "view_id": False,
            "target": "new",
            "context": {
                "default_operation_type_id": self.id,
                "default_company_id": self.company_id.id,
            },
        }

    def action_operation(self):
        return self._get_action("wi_base_farm.action_estate_operation_view")

    def action_draft_operation(self):
        return self._get_action(
            "wi_base_farm.action_estate_operation_view", params="draft"
        )

    def action_validate_operation(self):
        return self._get_action(
            "wi_base_farm.action_estate_operation_view", params="validate"
        )

    def action_posted_operation(self):
        return self._get_action(
            "wi_base_farm.action_estate_operation_view", params="posted"
        )

    def action_cancel_operation(self):
        return self._get_action(
            "wi_base_farm.action_estate_operation_view", params="cancel"
        )

    def action_done_operation(self):
        return self._get_action(
            "wi_base_farm.action_estate_operation_view", params="done"
        )

    def action_report_harvest(self):
        return self._get_action("wi_base_farm.harvesting_report_action", reports=True)

    def action_report_upkeep(self):
        return self._get_action("wi_base_farm.upkeeping_report_action", reports=True)


class FarmOperationActivity(models.Model):
    _name = "estate.operation"
    _description = "Estate Operation Activity"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(readonly=True, default=lambda self: _("New"), copy=False)
    color = fields.Integer()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validate", "Validated"),
            ("posted", "Posted"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        copy=False,
    )

    currency_id = fields.Many2one(
        "res.currency", string="Currency", related="company_id.currency_id", store=True
    )

    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    user_id = fields.Many2one(
        "res.users",
        string="Activity Representative",
        index=True,
        tracking=True,
        default=lambda self: self.env.user,
        check_company=True,
    )

    validate_uid = fields.Many2one(
        "res.users",
        string="Validate By",
        index=True,
        help="The user who validate the operation.",
    )

    required_validation = fields.Boolean(
        related="company_id.required_operation_validation",
        string="Required Validation",
        readonly=True,
    )

    picking_policy = fields.Selection(
        [("direct", "As soon as possible"), ("one", "When all products are ready")],
        string="Shipping Policy",
        required=True,
        readonly=True,
        default="direct",
    )

    comment = fields.Text("Remark")

    # ----------------------------------------------------------------

    foreman_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Harvest Foreman",
        tracking=True,
    )

    foreman_extra_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Extra Foreman",
        tracking=True,
    )

    assistant_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Assistant",
        tracking=True,
    )

    recorder_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Recorder",
        tracking=True,
    )

    foreman_total_penalty = fields.Monetary(
        "Foreman Penalty",
        compute="_compute_penalty_supervisor",
        help="Foreman penalty amount.",
        compute_sudo=True,
        store=True,
    )

    extra_foreman_total_penalty = fields.Monetary(
        "Foreman 1 Penalty",
        compute="_compute_penalty_supervisor",
        help="Foreman 1 penalty amount.",
        compute_sudo=True,
        store=True,
    )

    recorder_total_penalty = fields.Monetary(
        "Clerk Penalty",
        compute="_compute_penalty_supervisor",
        help="Clerk penalty amount.",
        compute_sudo=True,
        store=True,
    )
    total_cost = fields.Monetary(
        compute="_compute_amount_all",
        store=True,
        help="Sum of labour wage and material cost.",
        compute_sudo=True,
    )

    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        related="estate_id.warehouse_id",
        required=True,
        readonly=True,
        check_company=True,
    )
    code_ref = fields.Char(string="Reference Code")

    afdeling_id = fields.Many2one(
        comodel_name="estate.estate", string="Afdeling", tracking=True
    )

    estate_id = fields.Many2one(
        comodel_name="estate.estate", string="Estate", related="afdeling_id.parent_id"
    )

    operation_date = fields.Date(required=True, tracking=True, default=date.today())

    operation_type_id = fields.Many2one(
        "estate.operation.type",
        required=True,
        help="Type of operation activity",
    )
    type_operation = fields.Selection(
        related="operation_type_id.type_operation",
    )

    stock_location_id = fields.Many2one(
        "stock.location",
        required=True,
        string="Stock Location",
        related="warehouse_id.lot_stock_id",
        help="Location is set in Warehouse technical Information location stock",
    )

    block_location_ids = fields.Many2many(
        "estate.block",
        compute="_compute_block_location",
        string="Block Locations",
        copy=False,
        store=True,
    )

    procurement_group_id = fields.Many2one(
        "procurement.group", "Procurement Group", copy=False
    )

    activity_id = fields.Many2one(
        "account.analytic.account",
        string="Account Activity",
        domain=lambda self: self._compute_activity_domain(),
    )

    def _compute_activity_domain(self):
        """
        Efficiently filters Account Activity based on selected Operation Type.
        This ensures that only relevant records are shown dynamically.
        """
        return "[('plan_id.operation_type_id', '=', operation_type_id)]"

    labour_amount = fields.Monetary(
        "Labour Wage",
        store=True,
        compute="_compute_amount_all",
        help="Sum of labour's wage.",
        compute_sudo=True,
    )

    material_amount = fields.Monetary(
        "Material Cost",
        store=True,
        compute="_compute_amount_all",
        help="Sum of material's cost.",
        compute_sudo=True,
    )

    labour_line_ids = fields.One2many(
        comodel_name="estate.upkeep.labour",
        string="Upkeep Labour Line",
        inverse_name="estate_operation_id",
    )

    material_line_ids = fields.One2many(
        comodel_name="estate.upkeep.material",
        string="Upkeep Material Line",
        inverse_name="estate_operation_id",
    )

    estate_harvest_ids = fields.One2many(
        comodel_name="estate.harvest",
        inverse_name="estate_operation_id",
        tracking=True,
        copy=False,
    )

    # ------------------------ Harvesting Field ------------------------
    harvest_product_id = fields.Many2one(
        comodel_name="product.product",
        compute="_compute_afdeling_id",
        store=True,
        help="Harvest product set in Harvest Product Estate",
    )

    harvest_product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        compute="_compute_afdeling_id",
        store=True,
        help="Unit of Measure for Harvest Product",
    )

    harvest_other_product_id = fields.Many2one(
        comodel_name="product.product",
        compute="_compute_afdeling_id",
        store=True,
        help="Other product set in Harvest Product Estate",
    )

    harvest_other_product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        compute="_compute_afdeling_id",
        store=True,
        help="Unit of Measure for Other Harvest Product",
    )

    harvest_product_weight = fields.Float(
        string="Total Harvest Weight",
        default=False,
        copy=False,
        compute="_compute_total_weight",
        compute_sudo=True,
        store=True,
    )
    other_harvest_product_weight = fields.Float(
        string="Total Other Harvest Weight",
        default=False,
        copy=False,
        compute="_compute_total_weight",
        compute_sudo=True,
        store=True,
    )
    harvest_uom_qty = fields.Float(
        string="Total Harvest Stock",
        default=False,
        copy=False,
        compute="_compute_total_weight",
        compute_sudo=True,
        store=True,
    )

    clerk_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Clerk Production",
        tracking=True,
    )

    total_abnormal_unit = fields.Integer(
        string="Abnormal Qty Total",
        compute="_compute_total_weight",
        compute_sudo=True,
        store=True,
    )

    total_harvest_unit = fields.Integer(
        string="Harvest Unit Total",
        compute="_compute_total_weight",
        compute_sudo=True,
        store=True,
    )

    clerk_user_id = fields.Many2one(comodel_name="res.users", string="Recorder User")

    posted_date = fields.Datetime(tracking=True)

    team_id = fields.Many2one(comodel_name="estate.harvest.team")

    # -------------------- Planning --------------------
    planning_date = fields.Date(required=True, tracking=True, default=date.today())
    is_planned = fields.Boolean(
        compute="_compute_is_planned",
        default=False,
        store=True,
    )
    planning_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirmed"),
        ],
        default="draft",
    )
    source_data = fields.Selection(
        [
            ("manual", "Manual"),
            ("mobile", "Mobile"),
        ],
        default="manual",
    )

    @api.depends(
        "estate_harvest_ids",
        "estate_harvest_ids.planning_qty",
        "labour_line_ids",
        "labour_line_ids.planning_qty",
    )
    def _compute_is_planned(self):
        for rec in self:
            rec.is_planned = any(
                [
                    sum(rec.estate_harvest_ids.mapped("planning_qty")),
                    sum(rec.labour_line_ids.mapped("planning_qty")),
                ]
            )

    def action_confirm_plan(self):
        for rec in self:
            rec.planning_state = "confirm"

    # -----------------------------------------------------

    @api.onchange("team_id")
    def _onchange_team_id(self):
        if self.team_id:
            self.foreman_id = self.team_id.foreman_id
            self.foreman_extra_id = self.team_id.manager_id
            self.assistant_id = self.team_id.assistant_id
            self.recorder_id = self.team_id.recorder_id
            self.clerk_id = self.team_id.clerk_id
            if self.type_operation == "upkeep":
                self.labour_line_ids = [(5, 0, 0)]
                self.write(
                    {
                        "labour_line_ids": [
                            (0, 0, {"member_id": x.id}) for x in self.team_id.labour_ids
                        ]
                    }
                )
            elif self.type_operation == "harvest":
                self.estate_harvest_ids = [(5, 0, 0)]
                self.write(
                    {
                        "estate_harvest_ids": [
                            (0, 0, {"member_id": x.id, "estate_operation_id": self.id})
                            for x in self.team_id.labour_ids
                        ]
                    }
                )

    @api.depends("afdeling_id")
    def _compute_afdeling_id(self):
        if self.afdeling_id:
            self.harvest_product_id = self.afdeling_id.harvest_product_id.id
            self.harvest_product_uom_id = self.afdeling_id.harvest_product_uom_id.id
            self.harvest_other_product_id = self.afdeling_id.harvest_other_product_id.id
            self.harvest_other_product_uom_id = (
                self.afdeling_id.harvest_other_product_uom_id.id
            )

    def action_post(self):
        for record in self:
            if record.required_validation and record.state == "draft":
                raise UserError(_("Operation must be validated first!"))
            record._action_posted()

    def _action_posted(self):
        self.write(
            {
                "state": "posted",
                "posted_date": date.today(),
            }
        )
        if self.operation_type_id.type_operation == "harvest":
            self._generate_stock_move() if self.harvest_product_id else False
            self._estate_harvest_post()
        else:
            (
                self._compute_entire_block(self.labour_line_ids)
                if self.labour_line_ids
                else False
            )
            (
                self._compute_entire_block(self.material_line_ids)
                if self.material_line_ids
                else False
            )
            self._upkeep_labour_post()
        context = self._context.copy()
        context.pop("default_name", None)

    def _compute_entire_block(self, lines):
        for line in lines:
            vals = {
                "block_id": line.location_id,
                "amount": (
                    line.total_amount
                    if lines == self.labour_line_ids
                    else line.price_total
                ),
            }
            self._compute_seed_value(vals)

    def _compute_seed_value(self, vals):
        batch_ids = self.env["estate.seed.batch"].search(
            [("block_id", "=", vals["block_id"].id), ("state", "=", "active")]
        )
        if len(batch_ids) > 0:
            divided_amount = vals["amount"] / len(batch_ids)
            for batch in batch_ids:
                batch.batch_value += divided_amount
        vals["block_id"]._compute_block_values()

    def _estate_harvest_post(self):
        seq = 1
        for rec in self.estate_harvest_ids:
            rec.create_analytic_item()
            rec.is_posted = True
            if not rec.name:
                rec.name = self.name, " - ", seq
                seq += 1

    def _upkeep_labour_post(self):
        for rec in self.labour_line_ids:
            rec.create_analytic_item()

    def _get_stock_location(self):
        source_location_id = self.afdeling_id.harvest_location_id
        destination_location_id = self.afdeling_id.stock_location_id
        return source_location_id, destination_location_id

    def _generate_stock_move(self):
        source_loc_id, dest_loc_id = self._get_stock_location()
        move_vals = self._prepare_move_values(source_loc_id, dest_loc_id)
        for move_val in move_vals:
            move_id = (
                self.env["stock.move"]
                .sudo()
                .with_context(inventory_mode=False)
                .create(move_val)
            )
            move_id._action_done(cancel_backorder=False)

    def _prepare_move_values(self, src_location, dest_location, cancel=False):
        self.ensure_one()

        products = [
            {
                "product_id": self.harvest_product_id,
                "product_uom_qty": self.harvest_product_weight,
                "type": "main",
            },
            {
                "product_id": self.harvest_other_product_id,
                "product_uom_qty": self.other_harvest_product_weight,
                "type": "other",
            },
        ]
        data = []
        for product in products:
            product_qty = product["product_uom_qty"]
            if product["type"] == "main":
                product_qty = product["product_uom_qty"]
                if product["product_id"].harvest_by == "by_unit":
                    product_qty = self.total_harvest_unit
            if product_qty > 0:
                data.append(
                    {
                        "name": _("Harvesting (%(product_name)s): %(name)s")
                        % {
                            "product_name": product["product_id"].name,
                            "name": self.name,
                        },
                        "product_id": self.harvest_product_id.id,
                        "product_uom": self.harvest_product_id.uom_id.id,
                        "product_uom_qty": product_qty,
                        "origin": self.name,
                        "company_id": self.company_id.id,
                        "state": "confirmed",
                        "location_id": src_location.id,
                        "location_dest_id": dest_location.id,
                        "is_inventory": True,
                        "picked": True,
                        "move_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "product_id": self.harvest_product_id.id,
                                    "product_uom_id": self.harvest_product_id.uom_id.id,
                                    "quantity": product_qty,
                                    "location_id": src_location.id,
                                    "location_dest_id": dest_location.id,
                                    "company_id": self.company_id.id,
                                },
                            )
                        ],
                    }
                )
        return data

    def action_locked(self):
        self.write({"state": "done"})

    def action_validate(self):
        for record in self:
            record.write(
                {
                    "state": "validate",
                    "validate_uid": self.env.uid,
                }
            )

            record.message_post(
                body=_("Operation has been validated by %s") % self.env.user.name
            )

    def action_cancel(self):
        if self.operation_type_id.type_operation == "harvest":
            self._cancel_stock_move()
            for line in self.estate_harvest_ids:
                line.is_canceled = True
                if line.analytic_line_id:
                    line.analytic_line_id.unlink()
        else:
            for line in self.labour_line_ids:
                if line.analytic_line_id:
                    line.analytic_line_id.unlink()
        self.write({"state": "cancel"})

    def _cancel_stock_move(self):
        dest_loc_id, source_loc_id = self._get_stock_location()
        move_vals = self._prepare_move_values(source_loc_id, dest_loc_id, cancel=True)
        for move_val in move_vals:
            move_id = (
                self.env["stock.move"]
                .sudo()
                .with_context(inventory_mode=False)
                .create(move_val)
            )
            move_id._action_done(cancel_backorder=False)

    def action_reset_draft(self):
        self.write({"state": "draft"})

    @api.depends("estate_harvest_ids", "estate_harvest_ids.penalty_harvest_ids")
    def _compute_penalty_supervisor(self):
        for rec in self:
            rec.foreman_total_penalty = 0.0
            rec.extra_foreman_total_penalty = 0.0
            rec.recorder_total_penalty = 0.0
            tot_foreman_penal = 0
            tot_extra_foreman_penal = 0
            tot_recorder_penal = 0
            if rec.estate_harvest_ids:
                for harvest in rec.estate_harvest_ids:
                    for penalty in harvest.penalty_harvest_ids:
                        tot_foreman_penal += penalty.total_penalty_foreman
                        tot_extra_foreman_penal += penalty.total_penalty_extra_foreman
                        tot_recorder_penal += penalty.total_penalty_recorder
            rec.foreman_total_penalty = tot_foreman_penal
            rec.extra_foreman_total_penalty = tot_extra_foreman_penal
            rec.recorder_total_penalty = tot_recorder_penal

    @api.depends(
        "estate_harvest_ids",
        "estate_harvest_ids.total_include_penalty",
        "labour_line_ids",
        "labour_line_ids.total_amount",
        "material_line_ids",
        "material_line_ids.price_total",
    )
    def _compute_amount_all(self):
        for rec in self:
            rec.labour_amount = sum(rec.labour_line_ids.mapped("total_amount"))
            rec.material_amount = sum(rec.material_line_ids.mapped("price_total"))
            rec.total_cost = (
                sum(rec.estate_harvest_ids.mapped("total_include_penalty"))
                if rec.type_operation == "harvest"
                else rec.labour_amount + rec.material_amount
            )

    @api.depends(
        "estate_harvest_ids",
        "estate_harvest_ids.harvest_qty_weight",
        "estate_harvest_ids.harvest_qty_unit",
    )
    def _compute_total_weight(self):
        for rec in self:
            rec.harvest_product_weight = (
                sum(rec.estate_harvest_ids.mapped("harvest_qty_weight"))
                if rec.estate_harvest_ids
                else 0.0
            )
            rec.total_harvest_unit = (
                sum(rec.estate_harvest_ids.mapped("harvest_qty_unit"))
                if rec.estate_harvest_ids
                else 0.0
            )
            rec.total_abnormal_unit = (
                sum(rec.estate_harvest_ids.mapped("abnormal_unit"))
                if rec.estate_harvest_ids
                else 0.0
            )
            rec.other_harvest_product_weight = (
                sum(rec.estate_harvest_ids.mapped("other_harvest_stock_qty"))
                if rec.estate_harvest_ids
                else 0.0
            )
            rec.harvest_uom_qty = (
                rec.harvest_product_weight + rec.other_harvest_product_weight
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            op_type = self.env["estate.operation.type"].search(
                [("id", "=", vals["operation_type_id"])]
            )
            typeActivity = "UPKP/" if op_type.type_operation == "upkeep" else "HRVS/"
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    typeActivity
                    + op_type.name
                    + self.env["ir.sequence"].next_by_code("estate.operation.name")
                ) or _("New")
        return super().create(vals_list)

    def action_add_harvest_labour(self):
        context = {
            "default_harvest_operation": self.id,
        }
        return {
            "name": "Add Harvest Labour",
            "type": "ir.actions.act_window",
            "res_model": "harvest.labour.lines",
            "view_mode": "form",
            "target": "new",
            "context": context,
        }

    def unlink(self):
        for rec in self:
            if rec.state in ["posted", "done"]:
                raise UserError(
                    _("Cannot delete a operation that is in either posted or locked")
                )
            else:
                if rec.type_operation == "harvest":
                    for hrvs in rec.estate_harvest_ids:
                        [
                            rec.remv_list(x)
                            for x in [hrvs.penalty_harvest_ids, hrvs.penalty_logging]
                        ]
                        hrvs.unlink()
                else:
                    [
                        rec.remv_list(x)
                        for x in [rec.labour_line_ids, rec.material_line_ids]
                    ]
                return super().unlink()

    def remv_list(self, o_list):
        for obj in o_list:
            obj.unlink()

    @api.depends("labour_line_ids")
    def _compute_block_location(self):
        for rec in self:
            rec.block_location_ids = rec.labour_line_ids.mapped("location_id")
