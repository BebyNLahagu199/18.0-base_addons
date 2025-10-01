from odoo import fields, models


class EstateType(models.Model):
    _name = "estate.type"
    _description = "Estate Type"

    name = fields.Char(required=True)
    code = fields.Char(required=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique!"),
    ]


class EstateTypography(models.Model):
    _name = "estate.typography"
    _description = "Estate Typography"

    name = fields.Char(required=True)
    code = fields.Char(required=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique!"),
    ]


class EstateAreaType(models.Model):
    _name = "estate.area.type"
    _description = "Estate Area Type"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        default=lambda self: self.env.company.area_uom_id,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique!"),
    ]


class EstateTreeType(models.Model):
    _name = "estate.tree.type"
    _description = "Estate Tree Type"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        default=lambda self: self.env.company.area_uom_id,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique!"),
    ]


class EstateBlockState(models.Model):
    _name = "estate.planting.state"
    _description = "Planting State"

    name = fields.Char(required=True)
    display_name = fields.Char(compute="_compute_display_name", store=True, index=True)
    code = fields.Char(required=True)

    def _compute_display_name(self):
        names = dict(self.name_get())
        for record in self:
            record.display_name = names.get(record.id, False)

    def name_get(self):
        res = []
        for record in self:
            name = "%s  (%s)" % (record.name, record.code)
            res.append((record.id, name))
        return res


class EstateLand(models.Model):
    _name = "estate.land"
    _description = "Land"

    name = fields.Char(required=True)
    display_name = fields.Char(compute="_compute_display_name", store=True, index=True)
    code = fields.Char(required=True)

    def _compute_display_name(self):
        names = dict(self.name_get())
        for record in self:
            record.display_name = names.get(record.id, False)

    def name_get(self):
        res = []
        for record in self:
            name = "%s  (%s)" % (record.name, record.code)
            res.append((record.id, name))
        return res


class EstateStandardProduction(models.Model):
    _name = "estate.standard.production"
    _description = "Standard Production"

    seeds_id = fields.Many2one(
        "product.product",
        "Seeds",
        required=True,
    )
    land_id = fields.Many2one(
        "estate.land",
        required=True,
    )
    age = fields.Integer(
        required=True,
    )
    hectare = fields.Float(
        digits=(18, 6),
        required=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )


class EstateActivityPenalty(models.Model):
    _name = "estate.activity.penalty"
    _description = "Estate Penalty"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "display_name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    display_name = fields.Char(compute="_compute_display_name", store=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        string="Currency", related="company_id.currency_id", readonly=True
    )
    penalty_position_ids = fields.One2many(
        comodel_name="estate.activity.penalty.position",
        inverse_name="penalty_id",
        string="Penalty Position",
    )
    note = fields.Text("Additional Information")


class EstateActivityPenaltyPosition(models.Model):
    _name = "estate.activity.penalty.position"
    _description = "Estate Penalty Position"

    penalty_id = fields.Many2one("estate.activity.penalty", "Penalty")
    job_id = fields.Many2one(
        "hr.job",
        "Job Position",
        required=True,
    )
    amount = fields.Monetary(string="Penalty Amount")
    currency_id = fields.Many2one(
        string="Currency", related="penalty_id.company_id.currency_id", readonly=True
    )
