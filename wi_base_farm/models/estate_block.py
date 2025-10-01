from datetime import date

from dateutil import relativedelta

from odoo import _, api, fields, models


class EstateBlock(models.Model):
    _name = "estate.block"
    _description = "Estate Block"
    _inherit = ["mail.thread", "mail.activity.mixin", "qr.code.mixin"]
    _order = "display_name"

    name = fields.Char(required=True)
    code = fields.Char(copy=False)
    color = fields.Integer(string="Color Index")
    note = fields.Text()
    display_name = fields.Char(compute="_compute_display_name", store=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    estate_id = fields.Many2one(
        comodel_name="estate.estate",
        string="Afdeling",
        tracking=True,
    )
    planting_state_id = fields.Many2one(
        comodel_name="estate.planting.state",
        string="Block State",
        tracking=True,
    )
    planting_year = fields.Char(
        tracking=True,
    )
    type_id = fields.Many2one(
        comodel_name="estate.type",
        required=True,
        tracking=True,
    )
    typography_id = fields.Many2one(
        comodel_name="estate.typography",
        required=True,
        tracking=True,
    )
    land_id = fields.Many2one(
        comodel_name="estate.land",
        string="Land",
        tracking=True,
    )
    planting_date = fields.Date(
        tracking=True,
    )
    harvesting_date = fields.Date(
        tracking=True,
    )

    def _domain_analytic_account_id(self):
        plan = self.env.ref("wi_base_farm.analytic_plan_block")
        return [("plan_id", "child_of", plan.id)]

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        tracking=True,
        domain=lambda self: self._domain_analytic_account_id(),
    )
    analytic_balance = fields.Monetary(
        string="Balance Amount",
        related="analytic_account_id.balance",
    )

    estate_area_ids = fields.One2many(
        comodel_name="estate.area",
        inverse_name="block_id",
        string="Estate Area",
    )
    estate_tree_ids = fields.One2many(
        comodel_name="estate.tree",
        inverse_name="block_id",
        string="Estate Tree",
    )
    total_tree = fields.Integer(
        compute="_compute_total_tree",
        store=True,
    )
    product_ids = fields.One2many(
        comodel_name="estate.product",
        inverse_name="block_id",
        string="Farm Product",
    )

    # Block and Batch Cost value
    block_value = fields.Monetary(
        help="All Plant Value in this block", default=0, copy=False, tracking=True
    )

    bjr_ids = fields.One2many(
        comodel_name="estate.bjr",
        inverse_name="block_id",
        string="BJR",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )

    # from Ui view
    area_uom_id = fields.Many2one(
        related="company_id.area_uom_id",
    )

    # Summary Section
    total_area = fields.Integer(
        compute="_compute_total_area",
        store=True,
    )

    total_harvest_uom_qty = fields.Float(
        string="Harvest UoM Quantity",
        compute="_compute_harvest_summary",
        help="Overall Harvest Quantity, based on the last month",
        digits="Product Unit of Measure",
    )

    total_harvest_qty = fields.Float(
        string="Harvest Quantity",
        compute="_compute_harvest_summary",
        help="Overall Harvest Quantity, based on the last six month",
        digits="Product Unit of Measure",
    )

    average_weight = fields.Float(
        compute="_compute_harvest_summary",
        help="Overall Average Weight, based on the last six month",
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique!"),
    ]

    @api.depends("estate_area_ids")
    def _compute_total_area(self):
        for record in self:
            record.total_area = sum(record.estate_area_ids.mapped("amount"))

    @api.depends("estate_tree_ids")
    def _compute_total_tree(self):
        for record in self:
            record.total_tree = sum(record.estate_tree_ids.mapped("amount"))

    @api.depends("name", "code", "estate_id")
    def _compute_display_name(self):
        names = dict(self.name_get())
        for record in self:
            record.display_name = names.get(record.id, False)

    def _compute_harvest_summary(self):
        for record in self:
            average_weight = record.bjr_ids.filtered(
                lambda x: x.harvesting_date
                >= date.today() - relativedelta.relativedelta(months=6)
            )
            record.total_harvest_uom_qty = sum(average_weight.mapped("harvest_uom_qty"))
            record.total_harvest_qty = sum(average_weight.mapped("harvest_qty"))
            record.average_weight = 0
            if record.total_harvest_uom_qty > 0:
                record.average_weight = (
                    record.total_harvest_uom_qty / record.total_harvest_qty
                )

    def name_get(self):
        res = []
        for record in self:
            name = record.name or ""
            if record.estate_id:
                name = "%s, %s" % (record.sudo().estate_id.name, record.name)
            else:
                name = record.name
            res.append((record.id, name))
        return res

    def _compute_block_values(self):
        for record in self:
            record.block_value = 0
            labour = self.env["estate.upkeep.labour"].search(
                [("location_id", "=", record.id)]
            )
            material = self.env["estate.upkeep.material"].search(
                [("location_id", "=", record.id)]
            )
            for operation in labour:
                if operation:
                    record.block_value += operation.total_amount
            for operation in material:
                if operation:
                    record.block_value += operation.price_total

    @api.depends(
        "name",
        "code",
        "type_id",
        "qr_version",
        "qr_error_correction",
        "qr_box_size",
        "qr_border",
        "qr_logo",
        "qr_key",
    )
    def _compute_qr_code(self):
        res = super()._compute_qr_code()
        return res

    def prepare_qr_value(self):
        name = self.name
        code = self.code
        block_type = self.type_id.name
        qr_value = "%s - %s (%s)" % (name, code, block_type)
        return qr_value

    def action_view_analytic(self):
        self.ensure_one()
        block = self.env.ref("wi_base_farm.analytic_plan_block")
        block_column = block._column_name()
        return {
            "type": "ir.actions.act_window",
            "name": _("Analytic Balance of %s" % self.name),
            "domain": [(block_column, "=", self.analytic_account_id.id)],
            "res_model": "account.analytic.line",
            "view_id": False,
            "view_mode": "list,form",
            "context": {("default_%s" % block_column): self.id},
        }


class EstateArea(models.Model):
    _name = "estate.area"
    _description = "Estate Area"

    type = fields.Many2one(
        comodel_name="estate.area.type",
        string="Area Type",
        required=True,
    )
    code = fields.Char(related="type.code")
    amount = fields.Float()
    block_id = fields.Many2one(
        comodel_name="estate.block",
        string="Block",
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        related="type.uom_id",
    )


class EstateTree(models.Model):
    _name = "estate.tree"
    _description = "Estate Tree"

    type = fields.Many2one(
        comodel_name="estate.tree.type",
        string="Tree Type",
        required=True,
    )
    code = fields.Char(related="type.code")
    amount = fields.Integer()
    block_id = fields.Many2one(
        comodel_name="estate.block",
        string="Block",
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        related="type.uom_id",
    )
