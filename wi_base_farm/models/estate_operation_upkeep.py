import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class UpkeepLabour(models.Model):
    """
    Maintain work result and its work day(s) equivalent
    """

    _name = "estate.upkeep.labour"
    _description = "Upkeep Labour"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        copy=False, default=lambda self: _("New"), compute="_compute_name", store=True
    )
    estate_operation_id = fields.Many2one(  # prev name is upkeep_id
        comodel_name="estate.operation",
        string="Operation Activity",
        ondelete="cascade",
    )
    afdeling_id = fields.Many2one(
        related="estate_operation_id.afdeling_id",
        store=True,
    )
    account_activity_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        related="estate_operation_id.activity_id",
    )
    operation_date = fields.Date(
        related="estate_operation_id.operation_date",
        store=True,
    )
    currency_id = fields.Many2one(
        related="estate_operation_id.currency_id",
    )
    member_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Team Member",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="estate_operation_id.company_id",
        store=True,
    )

    state = fields.Selection(
        related="estate_operation_id.state",
        store=True,
    )
    is_outside_work_hour = fields.Boolean(default=False)
    quantity = fields.Float(help="Define total work result")
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM",
        # TODO : related='estate_activity_id.uom_id'
    )
    num_of_days = fields.Float(
        string="Workdays",
        default=1.0,
        help="Define total work result",
        aggregator="avg",
    )
    checkout = fields.Boolean(
        compute="_compute_checkout",
        store=True,
    )
    price_amount = fields.Monetary(
        string="Price",
        compute="_compute_price_amount",
        store=True,
    )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Attachment",
        domain="[('res_model', '=', 'estate.upkeep.labour')]",
    )
    calculation = fields.Selection(
        [("daily_salary", "Salary"), ("premi", "Premi")],
        compute="_compute_price_amount",
        store=True,
    )
    total_amount = fields.Monetary(
        default=0.0,
        compute="_compute_total_amount",
        store=True,
    )
    location_id = fields.Many2one(
        "estate.block", "Location", domain="[('estate_id', '=', afdeling_id)]"
    )
    work_note = fields.Text()

    # -------------------- Accounting --------------------
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        related="location_id.analytic_account_id",
    )
    analytic_line_id = fields.Many2one(
        "account.analytic.line",
        string="Analytic Line",
    )

    # -------------------- Planning --------------------
    planning_qty = fields.Float()
    planning_date = fields.Date(related="estate_operation_id.planning_date", store=True)
    planning_state = fields.Selection(related="estate_operation_id.planning_state")

    # -------------------- Dashboard Fields --------------------
    operation_type_id = fields.Many2one(
        comodel_name="estate.operation.type",
        related="estate_operation_id.operation_type_id",
        store=True,
    )
    employee_type = fields.Selection(
        related="member_id.employee_type",
        store=True,
    )
    block_type_id = fields.Many2one(
        related="location_id.type_id",
        store=True,
    )

    @api.depends("quantity", "price_amount", "num_of_days", "calculation")
    def _compute_total_amount(self):
        for rec in self:
            qty = rec.quantity if rec.calculation == "premi" else rec.num_of_days
            rec.total_amount = rec.price_amount * qty

    @api.depends("member_id", "account_activity_id", "location_id")
    def _compute_price_amount(self):
        for rec in self:
            member_exits = rec.check_member_exits()
            premi_applied, force_premi = rec._compute_premi_to_applied()
            if (
                member_exits
                or rec.member_id.employee_type == "freelance"
                or force_premi
                or rec.is_outside_work_hour
            ):
                rec.price_amount = premi_applied.premi_amount or 0.0
                rec.calculation = "premi"
            else:
                rec.price_amount = rec._compute_salary_wage(premi_applied) or 0.0
                rec.calculation = "daily_salary"

    def _compute_salary_wage(self, premi):
        contract_wage = (
            self.member_id.contract_id.wage if self.member_id.contract_id else 0
        )
        daily_wage = contract_wage / 30 if contract_wage else 0

        if premi and premi.minimal_unit > 0 and self.quantity < premi.minimal_unit:
            return 0

        return daily_wage

    def _compute_premi_to_applied(self):
        premi = self.env["estate.premi"].search(
            [
                ("account_activity_id", "=", self.account_activity_id.id),
                ("active", "=", True),
                ("company_id", "=", self.company_id.id),
            ],
            order="id desc",
            limit=1,
        )
        force_premi_amount = premi.force_premi_amount
        condition_to_applied = premi._compute_condition_to_applied(
            self.operation_date, self.member_id
        )

        return (
            premi if not condition_to_applied else condition_to_applied,
            force_premi_amount,
        )

    @api.depends("num_of_days")
    def _compute_checkout(self):
        for rec in self:
            rec.checkout = True if rec.num_of_days > 0 else False

    def action_open_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "wi_base_farm.estate_labour_action_view"
        )
        action["res_id"] = self.id
        return action

    @api.depends("estate_operation_id.activity_id", "location_id", "operation_date")
    def _compute_name(self):
        for rec in self:
            if rec.name == _("New") and rec.location_id:
                activity_code = rec.estate_operation_id.activity_id.code
                block_code = rec.location_id.code or "N/A"
                date_str = rec.operation_date.strftime("%Y/%m/%d")
                rec.name = f"{activity_code}/{block_code}/{date_str}/{rec.id}"

    def check_member_exits(self):
        # Check if the employee has a work record for that day
        return bool(
            self.env["estate.harvest"].search_count(
                [
                    ("member_id", "=", self.member_id.id),
                    ("operation_date", "=", self.operation_date),
                ]
            )
        )

    def write(self, vals):
        if vals.get("premi_amount", False):
            vals["amount"] = 0.0
        if vals.get("amount", False):
            vals["premi_amount"] = 0.0
        res = super().write(vals)
        return res

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
            "amount": self.total_amount,
            "ref": self.name,
            "partner_id": self.member_id.work_contact_id.id or False,
            "unit_amount": self.quantity,
            "operation_type_id": self.operation_type_id.id,
        }
        self.analytic_line_id = self.env["account.analytic.line"].create(localdict)


class UpkeepMaterial(models.Model):
    """
    Record material usage for upkeep activity
    Limit activity domain based on upkeep's activities and locations
    """

    _name = "estate.upkeep.material"
    _description = "Upkeep Material"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name")
    estate_operation_id = fields.Many2one(
        # prev name is upkeep_id
        comodel_name="estate.operation",
        string="Upkeep Activity",
        ondelete="cascade",
    )
    operation_date = fields.Date(
        related="estate_operation_id.operation_date",
        store=True,
    )
    company_id = fields.Many2one(related="estate_operation_id.company_id")
    currency_id = fields.Many2one(related="estate_operation_id.currency_id")
    location_id = fields.Many2one(
        comodel_name="estate.block",
        string="Location",
        domain="[('estate_id', '=', afdeling_id)]",
    )
    afdeling_id = fields.Many2one(
        related="estate_operation_id.afdeling_id",
        store=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Material",
        tracking=True,
        domain=[("farm_data", "=", True)],
    )
    state = fields.Selection(related="estate_operation_id.state", store=True)
    is_mto = fields.Boolean(
        # TODO : compute="_compute_is_mto"
    )
    qty_delivered_method = fields.Selection(
        [
            ("manual", "Manual"),
            ("analytic", "Analytic From Expenses"),
            ("stock_move", "Stock Moves"),
        ],
        string="Method to update delivered qty",
        # TODO : compute="_compute_qty_delivered_method",
        compute_sudo=True,
        store=True,
        readonly=True,
        help="According to product configuration, the delivered quantity "
        "can be automatically computed by mechanism :\n"
        "  - Manual: the quantity is set manually on the line\n"
        "  - Analytic From expenses: the quantity is the "
        "quantity sum from posted expenses\n"
        "  - Timesheet: the quantity is the sum of hours recorded "
        "on tasks linked to this sale line\n"
        "  - Stock Moves: the quantity comes from confirmed pickings\n",
    )
    product_uom = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    product_uom_readonly = fields.Boolean(compute="_compute_product_uom_readonly")
    product_uom_category_id = fields.Many2one(
        related="product_id.uom_id.category_id", readonly=True
    )
    product_qty = fields.Float(
        string="Quantity", digits="Product Unit of Measure", required=True
    )
    product_uom_qty = fields.Float(
        string="Total Quantity",
        compute="_compute_product_uom_qty",
        store=True,
    )
    product_standard_price = fields.Float()
    price_total = fields.Monetary(
        compute="_compute_amount",
        string="Total",
        store=True,
    )

    @api.depends("product_id")
    def _compute_name(self):
        for record in self:
            record.name = record.product_id.name

    @api.depends("state")
    def _compute_product_uom_readonly(self):
        for line in self:
            line.product_uom_readonly = line.state not in ["draft"]

    @api.depends("product_qty", "product_uom", "product_id.uom_id")
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom:
                line.product_uom_qty = line.product_uom._compute_quantity(
                    line.product_qty, line.product_id.uom_id
                )
            else:
                line.product_uom_qty = line.product_qty

    @api.depends("product_qty", "product_standard_price")
    def _compute_amount(self):
        for line in self:
            line.update(
                {
                    "price_total": line.product_standard_price * line.product_qty,
                }
            )
