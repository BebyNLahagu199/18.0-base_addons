from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EstateHarvest(models.Model):
    _name = "estate.harvest"
    _description = "Farm activity harvest"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        copy=False, default=lambda self: _("New"), compute="_compute_name", store=True
    )
    estate_operation_id = fields.Many2one(
        "estate.operation",
        required=True,
        ondelete="cascade",
    )

    # -------------------- Base Information --------------------
    member_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Teams Member",
        help="Team member that work on this activity",
    )
    block_id = fields.Many2one(
        comodel_name="estate.block",
        string="Block",
        help="Estate block that occur this activity",
    )
    tph_code = fields.Char(
        string="Code TPH",
    )
    avg_weight = fields.Float(
        help="Set in Estate Block in field BJR, System will get BJR of the same year",
        compute="_compute_average_weight",
        store=True,
    )
    other_avg_weight = fields.Float(
        help="Set in Estate Block in field BJR, System will get BJR of the same year",
        compute="_compute_average_weight",
        store=True,
    )
    planted_year = fields.Char(
        related="block_id.planting_year",
        help="Set in Estate Block in field planted year",
    )
    harvest_rates = fields.Float(help="Rates of this activity Harvest")

    # -------------------- Harvest Information --------------------
    harvest_main_product_id = fields.Many2one(
        related="estate_operation_id.harvest_product_id",
        string="Main Product",
        help="Main product of this activity",
        store=True,
    )
    harvest_other_product_id = fields.Many2one(
        related="estate_operation_id.harvest_other_product_id",
        string="Other Product",
        help="Other product of this activity",
        store=True,
    )
    harvest_qty_unit = fields.Integer(help="Harvest Qty per unit")
    harvest_uom_id = fields.Many2one(
        related="estate_operation_id.harvest_product_uom_id"
    )
    harvest_qty_weight = fields.Float(
        help="Harvest Qty Weight from Harvest Qty * BJR Aktual",
        compute="_compute_harvest_weight",
        compute_sudo=True,
        store=True,
        default=0,
        readonly=False,
    )
    harvest_stock_uom_id = fields.Many2one(related="harvest_main_product_id.uom_id")
    base_extra_weight = fields.Float(
        "Extra Base Weight",
        help="Total Extra Weight compare to Base Weight,"
        " Harvest Qty Weight - Base Weight",
        compute="_compute_harvest_weight",
        compute_sudo=True,
        store=True,
        default=0,
        readonly=False,
    )
    harvest_area = fields.Float(
        "Harvested Area(Ha)", help="Block Harvested Area by Employee"
    )

    other_harvest_qty = fields.Float()
    other_harvest_uom_id = fields.Many2one(
        related="estate_operation_id.harvest_other_product_uom_id"
    )
    other_harvest_stock_qty = fields.Float(
        compute="_compute_other_harvest_stock_qty", store=True, readonly=False
    )
    other_harvest_stock_uom_id = fields.Many2one(
        string="Other Harvest Stock UOM", related="harvest_other_product_id.uom_id"
    )

    # -------------------- Premi Computation --------------------

    premi_id = fields.Many2one(
        "estate.premi",
        string="Premi Applied",
        help="Premi Configuration",
        compute="_compute_premi_applied",
        store=True,
        readonly=False,
    )
    base_weight = fields.Float(
        help="Base Weight set in premi base weight",
        compute="_compute_premi_total",
        compute_sudo=True,
        store=True,
    )
    premi_base_extra = fields.Monetary(
        tracking=True,
        help="Premi from calculate field"
        " base extra weight * field Extra Base in premi configuration",
        compute="_compute_premi_total",
        compute_sudo=True,
        store=True,
        readonly=False,
    )
    attendance_premi = fields.Monetary(
        tracking=True,
        help="Premi set in premi configuration Attendance Premi",
        compute="_compute_premi_total",
        compute_sudo=True,
        store=True,
        readonly=False,
    )
    other_harvest_premi = fields.Monetary(
        tracking=True,
        help="Premi set in premi configuration Other Harvest Premi",
        compute="_compute_premi_total",
        compute_sudo=True,
        store=True,
        readonly=False,
    )
    total_premi = fields.Monetary(
        tracking=True,
        help="Sum of all premi",
        compute="_compute_premi_total",
        compute_sudo=True,
        store=True,
        readonly=False,
    )

    # -------------------- Employee Wages --------------------
    daily_wages = fields.Monetary(
        "Daily Wage",
        tracking=True,
        compute="_compute_total_exclude_penalty",
        store=True,
        help="Daily Wages of the employee."
        " Set the wages values in the employee contract and will be divided by 30",
        readonly=False,
    )
    total_exclude_penalty = fields.Monetary(
        "Total Wages(Exclude Penalty)",
        tracking=True,
        help="Total employee daily wage + total premi without penalty",
        compute="_compute_total_exclude_penalty",
        store=True,
        readonly=False,
    )

    # -------------------- Other --------------------
    state = fields.Selection(
        related="estate_operation_id.state",
        store=True,
        tracking=True,
        copy=False,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", related="estate_operation_id.currency_id"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="estate_operation_id.company_id",
        store=True,
    )
    operation_date = fields.Date(
        related="estate_operation_id.operation_date", store=True
    )
    is_posted = fields.Boolean(default=False)
    is_canceled = fields.Boolean(default=False)

    abnormal_unit = fields.Integer(
        compute="_compute_total",
        string="Abnormal Qty Unit",
        help="Total of abnormal Qty Unit",
        compute_sudo=True,
        store=True,
    )

    afdeling_id = fields.Many2one(
        "estate.estate", related="estate_operation_id.afdeling_id", store=True
    )

    work_note = fields.Text()

    # -------------------- Total Penalty --------------------
    penalty_total = fields.Monetary(
        compute="_compute_total",
        string="Total Penalty",
        store=True,
        readonly=True,
        currency_field="currency_id",
        help="Sum of all subtotal in penalty",
    )

    total_include_penalty = fields.Monetary(
        "Total Wages(Include Penalty)",
        tracking=True,
        help="Total employee wages include Penalty",
        compute="_compute_total_wages",
        compute_sudo=True,
        store=True,
    )

    # -------------------- Penalty Page --------------------
    penalty_harvest_ids = fields.One2many(
        "estate.harvest.penalty",
        "estate_harvest_id",
        string="Harvest Penalty",
        help="All Penalty for harvest activity",
    )

    # -------------------- Penalty Logging Page --------------------
    penalty_logging = fields.One2many(
        string="Penalty Log",
        comodel_name="estate.penalty.log",
        inverse_name="estate_harvest_id",
    )

    # -------------------- Accounting --------------------
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        related="block_id.analytic_account_id",
    )
    analytic_line_id = fields.Many2one(
        "account.analytic.line",
        string="Analytic Line",
    )

    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Attachment",
        domain="[('res_model', '=', 'estate.harvest')]",
    )

    # -------------------- Planning --------------------
    planning_qty = fields.Integer()
    planning_qty_uom = fields.Float(compute="_compute_planning_qty_uom", store=True)
    planning_date = fields.Date(related="estate_operation_id.planning_date", store=True)
    planning_state = fields.Selection(related="estate_operation_id.planning_state")

    @api.depends("avg_weight", "planning_qty")
    def _compute_planning_qty_uom(self):
        for rec in self:
            rec.planning_qty_uom = rec.avg_weight * rec.planning_qty

    def _check_attendance(self, member_id, operation_date):
        estate_harvest_list = self.env["estate.harvest"].search(
            [
                ("member_id", "=", member_id.id),
                ("operation_date", "=", operation_date),
                ("harvest_qty_unit", ">", 0),
                ("id", "!=", self._origin.id),
            ],
        )
        if estate_harvest_list and self not in estate_harvest_list:
            return True
        else:
            return False

    def _get_premi_harvest(self, block_id, operation_month):
        premi_ids = self.env["estate.premi"].search(
            [
                ("estate_block_id", "=", block_id.id),
                ("premi_type", "=", "monthly_harvest"),
                ("active", "=", True),
            ]
        )
        for premi_id in premi_ids:
            if (
                int(premi_id.start_month)
                <= int(operation_month)
                <= int(premi_id.end_month)
            ):
                return premi_id

    def _get_base_weight(self):
        for rec in self:
            rec.base_weight = rec.premi_id.harvest_base_qty
            if rec._check_attendance_condition():
                rec.reduce_base_weight()

    def _compute_other_harvest_stock(self):
        # convert other harvest qty to stock uom with odoo function
        return self.other_harvest_uom_id._compute_quantity(
            self.other_harvest_qty, self.other_harvest_stock_uom_id, round=False
        )

    def _calculate_premi(self, condition_applied):
        if not self.premi_id:
            return

        other_harvest_premi = (
            self.premi_id.other_harvest_premi * self.other_harvest_stock_qty
        )

        premi_applied = self.premi_id if not condition_applied else condition_applied
        activity_harvest = self.get_harvest_activity(
            self.member_id, self.operation_date
        )
        harvested_qty = (
            sum(activity_harvest.mapped("harvest_qty_weight"))
            if activity_harvest
            else 0
        )
        premi_rules = premi_applied.premi_quantifier_ids.filtered(
            lambda x: x.base_quantifier <= harvested_qty
        ).sorted("base_quantifier", reverse=True)

        premi_earned = (
            self._calculate_premi_by_step_calculation(premi_rules, harvested_qty)
            if premi_rules
            else {"premi_base_extra": 0, "attendance_premi": 0}
        )

        attendance_condition = self._check_attendance_condition()
        if attendance_condition:
            premi_earned["attendance_premi"] = 0

        self.write(
            {
                "premi_base_extra": premi_earned["premi_base_extra"],
                "attendance_premi": premi_earned["attendance_premi"],
                "other_harvest_premi": other_harvest_premi,
                "total_premi": premi_earned["premi_base_extra"]
                + premi_earned["attendance_premi"]
                + other_harvest_premi,
            }
        )

    def _check_attendance_condition(self):
        if not self.member_id:
            return False

        activity_harvest = self.get_harvest_activity(
            self.member_id, self.operation_date
        )
        total_data = len(activity_harvest) + (self not in activity_harvest)

        if total_data > 1:
            first_harvest = activity_harvest[0]

            return first_harvest != self

        return False

    def _calculate_premi_by_step_calculation(self, premi_rules, harvested_qty):
        total_qty = harvested_qty
        premi_base_extra = 0

        for premi in premi_rules:
            net_weight = max(harvested_qty - premi.base_quantifier, 0)
            premi_base_extra += premi.premi_extra * net_weight
            harvested_qty -= net_weight

        price_per_weight = premi_base_extra / total_qty if total_qty > 0 else 0
        distributed_amount = price_per_weight * self.harvest_qty_weight

        return {
            "premi_base_extra": distributed_amount,
            "attendance_premi": premi_rules[0].attendance_premi if premi_rules else 0,
        }

    def get_harvest_activity(self, member_id, operation_date):
        return self.env["estate.harvest"].search(
            [
                ("member_id", "=", member_id.id),
                ("operation_date", "=", operation_date),
            ],
            order="id ASC",
        )

    def reduce_base_weight(self):
        base_weight = self.base_weight
        estate_harvest = self.get_harvest_activity(self.member_id, self.operation_date)
        for rec in estate_harvest:
            if rec.id == self.id:
                break
            base_weight -= rec.harvest_qty_weight

        if base_weight < 0:
            base_weight = 0

        self.base_weight = base_weight

    def _get_other_average_weight(self):
        if self.harvest_qty_unit > 0:
            # to do get average by picking value
            self.other_avg_weight = self.other_harvest_uom_id.factor_inv
        else:
            self.other_avg_weight = self.other_harvest_uom_id.factor_inv

    def _get_bjr_amount(self, block_id):
        self.avg_weight = 0.0  # Default value if no BJR found
        if block_id and block_id.bjr_ids:
            operation_year = self.operation_date.year
            bjr = block_id.bjr_ids.filtered(
                lambda r: int(r.harvesting_date.year) == operation_year
            )
            if bjr:
                self.avg_weight = bjr[0].bjr

    # Section Compute
    @api.depends("penalty_harvest_ids", "penalty_total", "abnormal_unit")
    def _compute_total(self):
        for rec in self:
            total_amount = total_abnormal = 0
            for line in rec.penalty_harvest_ids:
                total_amount += line.penalty_subtotal
                total_abnormal += line.penalty_qty
            rec.penalty_total = total_amount
            rec.abnormal_unit = total_abnormal

    @api.depends("block_id", "operation_date")
    def _compute_premi_applied(self):
        for rec in self:
            if rec.block_id and rec.operation_date:
                operation_month = rec.operation_date.strftime("%m")
                rec.premi_id = rec._get_premi_harvest(
                    rec.block_id, int(operation_month)
                )

    @api.depends("avg_weight", "harvest_qty_unit")
    def _compute_harvest_weight(self):
        for rec in self:
            rec.harvest_qty_weight = rec.avg_weight * rec.harvest_qty_unit

    @api.depends(
        "member_id",
        "block_id",
        "premi_id",
        "harvest_qty_weight",
        "other_harvest_stock_qty",
    )
    def _compute_premi_total(self):
        for rec in self:
            rec._get_base_weight()
            rec.harvest_qty_weight = rec.avg_weight * rec.harvest_qty_unit
            extra_base_weight = rec.harvest_qty_weight - rec.base_weight
            if extra_base_weight > 0:
                rec.base_extra_weight = extra_base_weight
                condition_to_applied = rec.premi_id._compute_condition_to_applied(
                    rec.operation_date, rec.member_id
                )
                rec._calculate_premi(condition_to_applied)
            else:
                rec.base_extra_weight = 0
                rec.premi_base_extra = 0
                rec.attendance_premi = 0

    @api.depends("other_harvest_qty")
    def _compute_other_harvest_stock_qty(self):
        for rec in self:
            rec.other_harvest_stock_qty = rec._compute_other_harvest_stock()

    @api.depends("avg_weight", "harvest_qty_unit")
    def _compute_harvest_weight(self):
        for rec in self:
            rec.harvest_qty_weight = rec.avg_weight * rec.harvest_qty_unit

    @api.depends("member_id", "block_id", "total_premi")
    def _compute_total_exclude_penalty(self):
        for rec in self:
            member_contract = rec.member_id.contract_id
            if member_contract:
                if member_contract.state == "open":
                    check_attendance = rec._check_attendance(
                        rec.member_id, rec.operation_date
                    )
                    rec.daily_wages = (
                        member_contract.wage / 30 if not check_attendance else 0.0
                    )
                else:
                    raise UserError(_("Employee contract is not active"))
            rec.total_exclude_penalty = rec.total_premi + rec.daily_wages
            rec._compute_total_wages()

    @api.depends("penalty_total", "total_exclude_penalty")
    def _compute_total_wages(self):
        for rec in self:
            rec.total_include_penalty = rec.total_exclude_penalty - rec.penalty_total

    @api.depends("block_id", "operation_date", "estate_operation_id.harvest_product_id")
    def _compute_name(self):
        for rec in self:
            if rec.name == _("New") and rec.block_id:
                product_code = (
                    rec.estate_operation_id.harvest_product_id.default_code or "N/A"
                )
                block_code = rec.block_id.code
                date_str = rec.operation_date.strftime("%Y/%m/%d")
                rec.name = f"{product_code}/{block_code}/{date_str}/{rec.id}"

    @api.depends("block_id")
    def _compute_average_weight(self):
        for rec in self:
            rec._get_bjr_amount(rec.block_id) if rec.block_id else False
            rec._get_other_average_weight()

    def action_edit_harvest_labour(self):
        prev_penalty_ids = self.penalty_harvest_ids
        prev_penalty_data = [
            (x.penalty_type_id.id, x.penalty_qty) for x in prev_penalty_ids
        ]

        action = self.env["ir.actions.actions"]._for_xml_id(
            "wi_base_farm.action_harvest_labour_line"
        )

        context = {
            "default_harvest_operation": self.estate_operation_id.id,
            "default_harvest_id": self.id,
            "default_prev_member_team": self.member_id.id,
            "default_prev_block": self.block_id.id,
            "default_team_member": self.member_id.id,
            "default_block": self.block_id.id,
            "default_code_TPH": self.tph_code,
            "default_harvest_qty_unit": self.harvest_qty_unit,
            "default_other_harvest_qty": self.other_harvest_qty,
            "default_harvest_rates": self.harvest_rates,
            "default_harvest_area": self.harvest_area,
            "default_planning_qty": self.planning_qty,
            "default_work_note": self.work_note,
            "prev_penalty": prev_penalty_data,
        }

        action_context = literal_eval(action["context"])
        context = {**action_context, **context}
        action["context"] = context
        action["target"] = "new"

        return action

    def action_remove_harvest_labour(self):
        self.ensure_one()
        member_id = self.member_id
        self.unlink()
        labour_list = self.env["estate.harvest"].search(
            [
                ("member_id", "=", member_id.id),
            ],
            order="id ASC",
        )
        self.recompute_labour(labour_list)

    def recompute_labour(self, labour_ids):
        for labour in labour_ids:
            labour.write(
                {
                    "harvest_qty_unit": labour.harvest_qty_unit,
                }
            )

    def action_view_activity_hrvs(self):
        return {
            "name": "View Harvest Labour",
            "type": "ir.actions.act_window",
            "res_model": "estate.harvest",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def create_analytic_item(self):
        block = self.env.ref("wi_base_farm.analytic_plan_block")
        block_column = block._column_name()
        activity = self.env.ref("wi_base_farm.analytic_plan_activities")
        activity_column = activity._column_name()
        localdict = {
            "name": self.name,
            "date": self.operation_date,
            "company_id": self.company_id.id,
            block_column: self.analytic_account_id.id,
            activity_column: self.estate_operation_id.activity_id.id,
            "amount": self.total_include_penalty,
            "ref": self.name,
            "partner_id": self.member_id.work_contact_id.id or False,
            "unit_amount": self.harvest_qty_unit,
            "operation_type_id": self.estate_operation_id.operation_type_id.id,
        }
        self.analytic_line_id = self.env["account.analytic.line"].create(localdict)


class FarmHarvestPenalty(models.Model):
    _name = "estate.harvest.penalty"
    _description = "Farm harvest penalty"

    estate_harvest_id = fields.Many2one(
        comodel_name="estate.harvest",
        string="Harvest Activity",
        ondelete="cascade",
    )

    penalty_type_id = fields.Many2one(
        comodel_name="estate.activity.penalty", help="Type of penalty"
    )

    penalty_qty = fields.Float(
        string="Qty",
        help="Penalty Qty",
    )

    penalty_price = fields.Monetary(
        string="Penalty/Qty",
        help="Penalty Price set in penalty amount in Penalty Configuration",
        compute="_compute_penalty_price",
        compute_sudo=True,
        store=True,
    )

    # Penalty for Foreman 1, Harvest Foreman and Recorder
    total_penalty_foreman = fields.Monetary(
        "Total Penalty Harvest Foreman",
        help="Total penalty for Harvest Foreman",
        compute="_compute_penalty_other",
        compute_sudo=True,
        store=True,
    )

    penalty_subtotal = fields.Monetary(
        compute="_compute_amount",
        string="Subtotal",
        store=True,
        readonly=True,
        currency_field="currency_id",
        help="Penalty Total from multiplying Penalty Qty * Penalty Price",
    )

    total_penalty_extra_foreman = fields.Monetary(
        "Total Penalty Foreman 1",
        help="Total penalty for Foreman 1",
        compute="_compute_penalty_other",
        compute_sudo=True,
        store=True,
    )

    total_penalty_recorder = fields.Monetary(
        help="Total penalty for Recorder",
        compute="_compute_penalty_other",
        compute_sudo=True,
        store=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="estate_harvest_id.currency_id",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="estate_harvest_id.company_id",
        store=True,
    )

    comment = fields.Text()

    @api.depends("penalty_type_id")
    def _compute_penalty_price(self):
        for rec in self:
            worker = rec.estate_harvest_id.member_id
            rec.penalty_price = rec._compute_penalty_by_position(
                worker, rec.penalty_type_id
            )

    def _compute_penalty_by_position(self, worker, penalty_type_id):
        job_position = worker.job_id.id
        if not job_position:
            raise UserError(_("Job Position for employee: %s is not set") % worker.name)
        penalty_record = penalty_type_id.penalty_position_ids.filtered(
            lambda r: r.job_id.id == job_position
        )
        if penalty_record:
            return penalty_record[-1].amount
        return 0

    @api.depends("penalty_qty", "penalty_price")
    def _compute_amount(self):
        for rec in self:
            rec.penalty_subtotal = rec.penalty_qty * rec.penalty_price

    @api.depends("penalty_type_id", "penalty_qty")
    def _compute_penalty_other(self):
        for record in self:
            foreman_amount = record._compute_penalty_by_position(
                record.estate_harvest_id.estate_operation_id.foreman_id,
                record.penalty_type_id,
            )
            extra_amount = record._compute_penalty_by_position(
                record.estate_harvest_id.estate_operation_id.foreman_extra_id,
                record.penalty_type_id,
            )
            recorder_amount = (
                record._compute_penalty_by_position(
                    record.estate_harvest_id.estate_operation_id.clerk_id,
                    record.penalty_type_id,
                )
                if record.estate_harvest_id.estate_operation_id.clerk_id
                else 0
            )
            record.total_penalty_foreman = foreman_amount * record.penalty_qty
            record.total_penalty_extra_foreman = extra_amount * record.penalty_qty
            record.total_penalty_recorder = recorder_amount * record.penalty_qty


class FarmPenaltyLog(models.Model):
    _name = "estate.penalty.log"
    _description = "Farm penalty log"

    estate_harvest_id = fields.Many2one(
        comodel_name="estate.harvest",
        string="Harvest Activity",
        required=True,
        ondelete="cascade",
    )

    # Amount
    old_amount = fields.Float(required=True)
    new_amount = fields.Float(required=True)

    # Adjustment
    adjustment_qty = fields.Float(help="The adjustment quantity amount")
    adjustment_type = fields.Selection(
        [
            ("none", "None"),
            ("plus", "Addition"),
            ("subtraction", "Subtraction"),
            ("alter", "Alteration"),
        ],
        default=False,
    )

    comment = fields.Text(copy=False)
