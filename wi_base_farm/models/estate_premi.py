from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

PREMI_TYPE = [
    ("non_harvest", "Non-Harvest Work Unit Rates"),
    ("loaded_premi", "Loaded Premi"),
    ("monthly_harvest", "Monthly Harvest Premi"),
]

MONTHLY = [
    ("1", "January"),
    ("2", "Febuary"),
    ("3", "March"),
    ("4", "April"),
    ("5", "May"),
    ("6", "June"),
    ("7", "July"),
    ("8", "August"),
    ("9", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "Descember"),
]

LOADED_TYPE = [("truck", "Dump Truck"), ("fuso", "Fuso")]

CONDITIONAL_PREMI = [
    ("by_day", "By Day"),
    ("by_holidays", "By Holidays"),
]


class EstatePremiConfig(models.Model):
    _name = "estate.premi.config"
    _description = "Estate Premi Configuration"

    estate_id = fields.Many2one("estate.estate", "Estate")
    job_id = fields.Many2one("hr.job", "Job Position", required=True)
    premi_multiplier = fields.Float("Multiplier (%)", default=1.0, required=True)

    _sql_constraints = [
        (
            "estate_job_unique",
            "unique(estate_id, job_id)",
            "Premi Configuration already exists",
        )
    ]


class EstatePremiQualityConfig(models.Model):
    _name = "estate.premi.quality.config"
    _description = "Estate Premi Quality Configuration"

    estate_id = fields.Many2one("estate.estate", "Estate")
    operator_type = fields.Selection(
        string="Operator",
        selection=[
            ("equals", "="),
            ("greater_than", ">"),
            ("greater_than_or_equal", ">="),
            ("less_than", "<"),
            ("less_than_or_equal", "<="),
        ],
        default="equals",
        required=True,
        help="""Comparison type for premi quality

    1. '=' : Harvested Quality is equal to this Percentage.(*Prioritize)
    2. '>' : Harvested Quality is more than this Percentage.
    3. '>=': Harvested Quality is more than or equal to this Percentage.
    4. '<' : Harvested Quality is less than this Percentage.
    5. '<=': Harvested Quality is less than or equal to this Percentage.
    """,
    )

    quality_percentage = fields.Float(string="Percentage", digits=(12, 1))
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    amount_earned = fields.Monetary(
        string="Amount", required=True, default=0, help="Amount Earned by this rule"
    )


class EstatePremi(models.Model):
    _name = "estate.premi"
    _description = "Estate Premi"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    active = fields.Boolean(default=True)
    name = fields.Char(
        required=True,
        default="New",
        copy=False,
        compute="_compute_name",
        store=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        string="Currency", related="company_id.currency_id", readonly=True
    )
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        required=True,
        default=lambda self: self.env.company.country_id,
    )
    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        required=True,
        default=lambda self: self.env.company.state_id,
    )
    qty_uom_id = fields.Many2one(
        "uom.uom",
        string="Quantity Unit of Measure",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit"),
    )
    price_per_qty = fields.Monetary(
        string="Price per Quantity",
        help="Price per Quantity",
        tracking=True,
    )
    premi_type = fields.Selection(PREMI_TYPE, string="Type", tracking=True)

    # Premi Non Harvest
    premi_amount = fields.Float(copy=False, default=False)

    # Premi Loaded
    qty_loaded = fields.Float(string="Quantity Loaded", copy=False, default=False)
    total_days = fields.Integer(default=False, copy=False)

    loaded_premi_type = fields.Selection(
        LOADED_TYPE, string="Loaded Type", default=False, copy=False
    )
    estate_block_id = fields.Many2one(
        "estate.block",
        default=False,
    )
    start_month = fields.Selection(
        MONTHLY,
        default=False,
        copy=False,
    )
    end_month = fields.Selection(MONTHLY, default=False, copy=False)
    other_harvest_premi = fields.Monetary(
        default=0.0,
    )
    planted_year = fields.Char(related="estate_block_id.planting_year", copy=False)
    harvest_base_qty = fields.Float(string="Base Weight", default=False)
    qty_uom = fields.Many2one(
        "uom.uom",
        string="UoM",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit"),
    )
    harvest_result_qty = fields.Float(
        string="Harvest Weight", default=False, help="Harvested Weight per Unit"
    )
    base_extra = fields.Float(string="Extra", default=False)

    account_activity_id = fields.Many2one(
        "account.analytic.account", string="Activity Account"
    )
    use_condition = fields.Boolean(
        default=False,
    )
    premi_quantifier_ids = fields.One2many("estate.premi.quantifier", "premi_id")
    premi_condition_ids = fields.One2many(
        comodel_name="estate.premi.condition",
        inverse_name="premi_id",
        string="Conditions",
    )

    force_premi_amount = fields.Boolean(default=False)
    minimal_unit = fields.Float()

    @api.depends("account_activity_id", "estate_block_id")
    def _compute_name(self):
        for premi in self:
            if premi.premi_type != "monthly_harvest":
                premi.name = premi.account_activity_id.display_name
            else:
                premi.name = (
                    f"{premi.account_activity_id.display_name} - "
                    f"{premi.estate_block_id.code}"
                )

    def _compute_condition_to_applied(self, operation_date, member_id):
        if not self.use_condition:
            return False

        shift_id = member_id.resource_calendar_id

        for condition in self.premi_condition_ids:
            if condition.condition == "by_holidays":
                holiday_ids = self.env["resource.calendar.leaves"].search(
                    [
                        ("resource_id", "=", False),
                        ("date_from", "<=", operation_date),
                        ("date_to", ">=", operation_date),
                        "|",
                        ("calendar_id", "=", False),
                        ("calendar_id", "=", shift_id.id),
                    ]
                )

                if holiday_ids:
                    return condition
            elif condition.condition == "by_day":
                if int(condition.condition_day) == operation_date.isoweekday():
                    return condition

        return False


class EstatePremiQuantifier(models.Model):
    _name = "estate.premi.quantifier"
    _description = "Estate Premi Quantifier"
    _rec_name = "premi_id"

    premi_id = fields.Many2one("estate.premi", "Premi")
    condition_id = fields.Many2one("estate.premi.condition", "Condition")
    quantifier = fields.Float(default=0.0)
    base_quantifier = fields.Float(
        compute="_compute_base_quantifier",
        store=True,
    )
    premi_extra = fields.Monetary(
        default=0.0,
    )

    attendance_premi = fields.Monetary(
        default=0.0,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="premi_id.currency_id",
        store=True,
    )

    @api.depends(
        "premi_id",
        "premi_id.harvest_base_qty",
        "quantifier",
        "condition_id",
        "condition_id.harvest_base_qty",
    )
    def _compute_base_quantifier(self):
        for row in self:
            base_weight = (
                row.premi_id.harvest_base_qty
                if row.premi_id
                else row.condition_id.harvest_base_qty
            )
            row.base_quantifier = base_weight * row.quantifier


class EstatePremiCondition(models.Model):
    _name = "estate.premi.condition"
    _description = "Estate Premi Condition"
    _rec_name = "premi_id"

    premi_id = fields.Many2one("estate.premi", "Estate Premi")

    premi_type = fields.Selection(related="premi_id.premi_type")

    condition = fields.Selection(
        selection=CONDITIONAL_PREMI,
        required=True,
        default="by_day",
    )

    condition_day = fields.Selection(
        selection=[
            ("1", "Monday"),
            ("2", "Tuesday"),
            ("3", "Wednesday"),
            ("4", "Thursday"),
            ("5", "Friday"),
            ("6", "Saturday"),
            ("7", "Sunday"),
        ],
        help="Every week on this day the condition will be applied",
        default=False,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="premi_id.currency_id",
        string="Currency",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        related="premi_id.company_id",
        string="Company",
    )

    brondolan_premi = fields.Monetary(
        currency_field="currency_id",
    )

    harvest_base_qty = fields.Float(
        string="Base Weight",
        default=0.0,
    )

    premi_quantifier_ids = fields.One2many("estate.premi.quantifier", "condition_id")

    premi_amount = fields.Monetary(
        string="Premi", currency_field="currency_id", default=0.0
    )


class EstatePremiOperationDaily(models.Model):
    _name = "estate.premi.operation.daily"
    _description = "Daily Premi Operation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "operation_date desc"

    name = fields.Char(copy=False, default="New", required=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        copy=False,
    )

    operation_date = fields.Date(
        tracking=True,
        required=True,
        help="Date of the premi to compute",
    )

    estate_id = fields.Many2one(
        "estate.estate",
        string="Estate",
        required=True,
        domain="[('location_type', '!=', 'afdeling')]",
    )

    employee_id = fields.Many2one(
        "hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Employee",
        required=True,
        tracking=True,
    )

    job_id = fields.Many2one(
        "hr.job",
        related="employee_id.job_id",
        string="Job Position",
        readonly=True,
        store=True,
    )

    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )

    reference = fields.Char(
        required=True, compute="_compute_reference", store=True, readonly=False
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )

    source_ids = fields.One2many(
        "estate.premi.operation.daily.source",
        "operation_id",
        string="Sources",
        compute="_compute_source_ids",
        store=True,
    )

    premi_total = fields.Monetary(
        string="Total Premi",
        currency_field="currency_id",
        compute="_compute_premi_total",
        store=True,
    )

    additional_premi = fields.Monetary(
        currency_field="currency_id",
        default=0.0,
    )

    penalty_deduction = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        default=0.0,
    )

    premi_multiplier = fields.Float(
        default=1.0,
        required=True,
    )

    work_as = fields.Selection(
        selection=[
            ("foreman", "Foreman"),
            ("extra_foreman", "Foreman I"),
            ("clerk", "Clerk"),
            ("recorder", "Recorder"),
        ],
        default=False,
    )

    def _get_activity_domain(self):
        harvest_operation = self.env["estate.operation.type"].search(
            [("type_operation", "=", "harvest")]
        )

        return [
            ("state", "in", ["posted", "done"]),
            ("operation_type_id", "in", harvest_operation.ids),
            ("operation_date", "=", self.operation_date),
            ("afdeling_id", "in", self.estate_id.child_ids.ids),
        ]

    def get_operation_ids(self, domain, field_name):
        return self.env["estate.operation"].search(
            domain + [(field_name, "=", self.employee_id.id)]
        )

    @api.onchange("estate_id", "employee_id")
    def _onchange_estate_id(self):
        if self.estate_id:
            self.premi_multiplier = self.estate_id.premi_ids.filtered(
                lambda x: x.job_id.id == self.job_id.id
            ).premi_multiplier

    @api.depends("employee_id", "operation_date", "work_as", "estate_id")
    def _compute_source_ids(self):
        for record in self:
            record.source_ids = [Command.clear()]

            operation_ids = record.env["estate.operation"]
            domain = record._get_activity_domain()
            data = []
            penalty_deduction = 0

            if record.work_as in ["foreman", "clerk", "recorder"]:
                operation_field_map = {
                    "foreman": "foreman_id",
                    "clerk": "clerk_id",
                    "recorder": "recorder_id",
                }
                operation_ids = record.get_operation_ids(
                    domain, operation_field_map[record.work_as]
                )
                harvest = operation_ids.mapped("estate_harvest_ids")

                penalty_field_map = {
                    "foreman": "foreman_total_penalty",
                    "clerk": "recorder_total_penalty",
                    "recorder": False,
                }
                penalty_deduction = (
                    sum(operation_ids.mapped(penalty_field_map[record.work_as]))
                    if penalty_field_map[record.work_as]
                    else 0
                )

                for employee in harvest.mapped("member_id"):
                    premi = sum(
                        harvest.filtered(lambda x: x.member_id == employee).mapped(
                            "total_premi"
                        )
                    )
                    data.append(
                        Command.create(
                            {
                                "employee_id": employee.id,
                                "total_premi": premi,
                            }
                        )
                    )
            elif record.work_as == "extra_foreman":
                operation_ids = record.get_operation_ids(domain, "foreman_extra_id")
                foreman_ids = operation_ids.mapped("foreman_id")
                daily_premi_ids = record.search(
                    [
                        ("operation_date", "=", record.operation_date),
                        ("employee_id", "in", foreman_ids.ids),
                        ("state", "!=", "cancel"),
                    ]
                )
                penalty_deduction = sum(
                    operation_ids.mapped("extra_foreman_total_penalty")
                )
                for premi in daily_premi_ids:
                    data.append(
                        Command.create(
                            {
                                "employee_id": premi.employee_id.id,
                                "total_premi": premi.premi_total,
                            }
                        )
                    )

            record.write({"source_ids": data, "penalty_deduction": penalty_deduction})

    @api.depends(
        "source_ids", "premi_multiplier", "source_ids.total_premi", "additional_premi"
    )
    def _compute_premi_total(self):
        for record in self:
            record.premi_total = record.additional_premi or 0.0
            divider_count = len(record.source_ids)
            source_premi = sum(record.source_ids.mapped("total_premi"))
            if divider_count and source_premi and record.premi_multiplier:
                record.premi_total = (
                    (source_premi / divider_count) * (record.premi_multiplier / 100)
                    + record.additional_premi
                    - record.penalty_deduction
                )

    @api.depends("estate_id", "employee_id", "operation_date")
    def _compute_reference(self):
        formated_date_cache = {}
        for record in self.filtered(lambda p: p.employee_id and p.operation_date):
            lang = self.env.user.lang
            context = {"lang": lang}
            reference = _("Daily Premi")
            del context

            record.reference = "%(reference)s - %(employee_id)s - %(dates)s" % {
                "reference": reference,
                "employee_id": record.employee_id.name,
                "dates": record._get_period_name(formated_date_cache),
            }

    def _get_period_name(self, cache):
        operation_date = self.operation_date
        return self._format_date_cached(cache, operation_date, "dd MMMM Y")

    def _format_date_cached(self, cache, date, date_format=False):
        key = (date, date_format)
        if key not in cache:
            lang = self.env.user.lang
            cache[key] = format_date(
                env=self.env, value=date, lang_code=lang, date_format=date_format
            )
        return cache[key]

    def action_post(self):
        for record in self:
            record.state = "posted"

    def action_done(self):
        for record in self:
            record.state = "done"

    def action_cancel(self):
        for record in self:
            record.state = "cancel"

    def action_draft(self):
        for record in self:
            record.state = "draft"

    def action_unlock(self):
        for record in self:
            record.state = "posted"

    def unlink(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("You cannot delete a posted or locked record"))
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("estate.daily.premi") or "New"
                )
        return super().create(vals_list)


class EstatePremiOperationDailySource(models.Model):
    _name = "estate.premi.operation.daily.source"
    _description = "Daily Premi Operation Source"
    _rec_name = "employee_id"

    operation_id = fields.Many2one("estate.premi.operation.daily", "Operation")
    employee_id = fields.Many2one(
        "hr.employee",
        "Employee",
        domain=[("job_id.farm_data", "=", True)],
        required=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        related="employee_id.job_id",
        string="Job Position",
        readonly=True,
        store=True,
    )
    total_premi = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="operation_id.currency_id",
        readonly=True,
    )


class EstatePremiOperationMonthly(models.Model):
    _name = "estate.premi.operation.monthly"
    _description = "Monthly Premi Operation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "operation_date desc"

    name = fields.Char(copy=False, default="New", required=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        copy=False,
    )

    operation_date = fields.Date(
        tracking=True,
        required=True,
        default=fields.Date.today,
        help="Date of the premi to compute",
    )

    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )

    date_from = fields.Date(
        string="From",
        readonly=False,
        required=True,
        compute="_compute_date_from",
        store=True,
        precompute=True,
    )
    date_to = fields.Date(
        string="To",
        readonly=False,
        required=True,
        compute="_compute_date_to",
        store=True,
        precompute=True,
    )

    note = fields.Text()

    reference = fields.Char(
        required=True, compute="_compute_reference", store=True, readonly=False
    )

    estate_id = fields.Many2one(
        "estate.estate",
        string="Estate",
        required=True,
        domain="[('location_type', '!=', 'afdeling')]",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )

    afdeling_premi_ids = fields.One2many(
        "estate.premi.operation.line",
        inverse_name="operation_id",
        string="Afdeling Premi",
        domain=[("line_type", "=", "afdeling")],
    )

    estate_premi_ids = fields.One2many(
        "estate.premi.operation.line",
        inverse_name="operation_id",
        string="Estate Premi",
        domain=[("line_type", "=", "estate")],
    )

    afdeling_premi_total = fields.Monetary(
        compute="_compute_premi_total",
        string="Total Afdeling Premi",
        compute_sudo=True,
        store=True,
    )

    deduction_total = fields.Monetary(
        string="Deduction",
        compute="_compute_premi_total",
        compute_sudo=True,
        store=True,
    )

    estate_premi_total = fields.Monetary(
        compute="_compute_premi_total",
        string="Total Estate Premi",
        compute_sudo=True,
        store=True,
    )

    premi_total = fields.Monetary(
        compute="_compute_premi_total",
        string="Total Premi",
        compute_sudo=True,
        store=True,
    )

    @api.depends("afdeling_premi_ids", "estate_premi_ids")
    def _compute_premi_total(self):
        for record in self:
            record.afdeling_premi_total = sum(
                record.afdeling_premi_ids.mapped("employee_premi")
            )
            record.estate_premi_total = sum(
                record.estate_premi_ids.mapped("employee_premi")
            )
            record.deduction_total = -sum(record.afdeling_premi_ids.mapped("deduction"))
            record.premi_total = record.afdeling_premi_total + record.estate_premi_total

    @api.depends("estate_id")
    def _compute_date_from(self):
        for record in self:
            record.date_from = date.today().replace(day=1)

    @api.depends("date_from", "estate_id")
    def _compute_date_to(self):
        for record in self:
            record.date_to = record.date_from and record.date_from + relativedelta(
                months=1, days=-1
            )

    @api.depends("estate_id", "date_from", "date_to")
    def _compute_reference(self):
        formated_date_cache = {}
        for record in self.filtered(
            lambda p: p.estate_id and p.date_from and p.date_to
        ):
            lang = self.env.user.lang
            context = {"lang": lang}
            reference = _("Monthly Premi")
            del context

            record.reference = "%(reference)s - %(estate_name)s - %(dates)s" % {
                "reference": reference,
                "estate_name": record.estate_id.name,
                "dates": record._get_period_name(formated_date_cache),
            }

    def _get_period_name(self, cache):
        start_date = self.date_from
        return self._format_date_cached(cache, start_date, "MMMM Y")

    def _format_date_cached(self, cache, date, date_format=False):
        key = (date, date_format)
        if key not in cache:
            lang = self.env.user.lang
            cache[key] = format_date(
                env=self.env, value=date, lang_code=lang, date_format=date_format
            )
        return cache[key]

    def action_compute_premi(self):
        for record in self:
            record.afdeling_premi_ids.action_compute_premi()
            record.estate_premi_ids.action_compute_premi()
            record._compute_premi_total()

    def action_post(self):
        for record in self:
            record.state = "posted"

    def action_done(self):
        for record in self:
            record.state = "done"

    def action_cancel(self):
        for record in self:
            record.state = "cancel"

    def action_draft(self):
        for record in self:
            record.state = "draft"

    def action_unlock(self):
        for record in self:
            record.state = "posted"

    def unlink(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("You cannot delete a posted or locked record"))
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("estate.monthly.premi")
                    or "New"
                )
        return super().create(vals_list)


class EstatePremiOperationLine(models.Model):
    _name = "estate.premi.operation.line"
    _description = "Premi Operation Line"
    _order = "employee_id"

    operation_id = fields.Many2one("estate.premi.operation.monthly", "Afdeling Premi")
    employee_id = fields.Many2one(
        "hr.employee",
        "Employee",
        domain=[("job_id.farm_data", "=", True)],
        required=True,
    )
    line_type = fields.Selection(
        selection=[
            ("afdeling", "Afdeling"),
            ("estate", "Estate"),
        ],
        string="Type",
    )
    job_id = fields.Many2one(
        "hr.job",
        related="employee_id.job_id",
        string="Job Position",
        readonly=True,
        store=True,
    )
    date_from = fields.Date(string="From", related="operation_id.date_from")
    date_to = fields.Date(string="To", related="operation_id.date_to")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="operation_id.currency_id",
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="operation_id.company_id",
        readonly=True,
    )
    estate_id = fields.Many2one(
        "estate.estate",
        string="Estate",
    )
    planned_optimal = fields.Float(string="Optimal", default=0.0, required=True)
    planned_maximum = fields.Float(string="Maximum", default=0.0, required=True)

    actual_harvest = fields.Float(
        string="Actual Qty", compute="_compute_actual_harvest", store=True
    )
    harvest_quality = fields.Float(
        string="Quality(%)", help="Quality Percentage of afdeling"
    )
    premi_multiplier = fields.Float(
        string="Multiplier(%)",
    )
    deduction = fields.Monetary(
        help="Deduction for this employee", currency_field="currency_id"
    )
    employee_premi = fields.Monetary(
        string="Premi",
        help="Total amount earned by this employee",
        currency_field="currency_id",
        compute="_compute_employee_premi",
        store=True,
    )

    def _compute_operation_id(self):
        for record in self:
            record.operation_id = (
                record.operation_afdeling_id or record.operation_estate_id
            )

    def action_compute_premi(self):
        for record in self:
            record._compute_actual_harvest()
            record._compute_employee_premi()

    @api.depends(
        "employee_id", "estate_id", "date_from", "date_to", "operation_id.estate_id"
    )
    def _compute_actual_harvest(self):
        for record in self:
            record.planned_optimal = (
                record.operation_id.estate_id.planned_optimal or 0.0
            )
            record.planned_maximum = (
                record.operation_id.estate_id.planned_maximum or 0.0
            )
            record.premi_multiplier = record.operation_id.estate_id.premi_ids.filtered(
                lambda x: x.job_id.id == record.job_id.id
            ).premi_multiplier
            record.actual_harvest = 0.0
            if (
                record.employee_id
                and record.estate_id
                and record.date_from
                and record.date_to
                and record.line_type == "afdeling"
            ):
                record.actual_harvest = sum(
                    record.env["estate.operation"]
                    .search(
                        [
                            ("assistant_id", "=", record.employee_id.id),
                            ("operation_date", ">=", record.date_from),
                            ("operation_date", "<=", record.date_to),
                            ("afdeling_id", "=", record.estate_id.id),
                            ("state", "in", ["posted", "done"]),
                        ]
                    )
                    .mapped("harvest_uom_qty")
                )

    @api.depends(
        "employee_id",
        "actual_harvest",
        "premi_multiplier",
        "planned_optimal",
        "planned_maximum",
        "harvest_quality",
        "deduction",
    )
    def _compute_employee_premi(self):
        for record in self:
            record.employee_premi = 0
            if record.line_type == "afdeling":
                record._calculate_premi_afdeling()
            else:
                record._calculate_premi_estate()

    def _calculate_premi_estate(self):
        premi_afdeling = self.operation_id.afdeling_premi_ids.filtered(
            lambda x: x.line_type == "afdeling"
        )
        afdeling_count = 0
        afdeling_count = len(premi_afdeling)
        if afdeling_count:
            self.employee_premi = (
                sum(premi_afdeling.mapped("employee_premi")) / afdeling_count
            ) * (self.premi_multiplier / 100)

    def _calculate_premi_afdeling(self):
        if (
            self.employee_id
            and self.planned_optimal
            and self.planned_maximum
            and self.actual_harvest
        ):
            multiplier = self.premi_multiplier / 100
            achivement_reward = (
                self.operation_id.estate_id.premi_maximum
                if self.actual_harvest >= self.planned_maximum
                else self.estate_id.parent_id.premi_optimal
            )

            if self.actual_harvest >= self.planned_maximum:
                quantity = (
                    (self.actual_harvest - self.planned_maximum) * 2
                ) + achivement_reward
            else:
                quantity = (
                    self.actual_harvest / self.planned_optimal
                ) * achivement_reward

            quality = self.calculate_quality_amount(self.harvest_quality)
            self.employee_premi = ((quantity + quality) * multiplier) - self.deduction

    def calculate_quality_amount(self, compared_values):
        quality_reward = 0

        for quality in self.operation_id.estate_id.premi_quality_ids:
            if (
                quality.operator_type == "equals"
                and quality.quality_percentage == compared_values
            ):
                return quality.amount_earned
            elif (
                quality.operator_type == "greater_than"
                and quality.quality_percentage < compared_values
            ):
                quality_reward = quality.amount_earned
            elif (
                quality.operator_type == "greater_than_or_equal"
                and quality.quality_percentage <= compared_values
            ):
                quality_reward = quality.amount_earned
            elif (
                quality.operator_type == "less_than"
                and quality.quality_percentage > compared_values
            ):
                quality_reward = quality.amount_earned
            elif (
                quality.operator_type == "less_than_or_equal"
                and quality.quality_percentage >= compared_values
            ):
                quality_reward = quality.amount_earned

        employee_start_date = self.employee_id.first_contract_date
        if employee_start_date >= self.date_to:
            return False
        elif employee_start_date >= self.date_from:
            date_interval = (self.date_to - employee_start_date).days + 2
            return (quality_reward / 30) * date_interval

        return quality_reward
