from odoo import api, fields, models


class EstateBlockBjr(models.Model):
    _name = "estate.bjr"
    _description = "Estate BJR"
    _order = "harvesting_date desc"

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
    )
    description = fields.Char()
    block_id = fields.Many2one(
        comodel_name="estate.block",
        string="Block",
        required=True,
    )
    harvesting_date = fields.Date(
        required=True,
        default=fields.Date.today,
    )
    planting_year = fields.Char(
        related="block_id.planting_year",
        readonly=True,
        store=True,
    )
    harvest_qty = fields.Float(
        string="Quantity",
        required=True,
        default=0.0,
    )
    harvest_uom_qty = fields.Float(
        string="Stock",
        required=True,
        default=0.0,
    )
    bjr = fields.Float(
        compute="_compute_weight",
        store=True,
        readonly=False,
        required=True,
        default=0.0,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "block_product_harvesting_date_uniq",
            "unique(block_id,product_id,harvesting_date)",
            "BJR already exists",
        ),
    ]

    @api.depends("harvesting_date")
    def _compute_harvesting_year(self):
        for record in self:
            record.harvesting_year = record.harvesting_date.year

    @api.depends("block_id", "harvesting_date")
    def _compute_name(self):
        names = dict(self.name_get())
        for record in self:
            record.name = names.get(record.id, False)

    @api.depends("harvest_qty", "harvest_uom_qty")
    def _compute_weight(self):
        for record in self:
            record.bjr = record.harvest_uom_qty / record.harvest_qty

    def name_get(self):
        res = []
        for record in self:
            name = record._get_name(record)
            res.append((record.id, name))
        return res

    def _get_name(self, record):
        if record.harvesting_date and record.block_id:
            return "%s, %s" % (record.block_id.name, record.harvesting_date)
        else:
            return "New"
