from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    farm_data = fields.Boolean(
        company_dependent=True,
        help="Check this box if this category is a farm data."
        "and you can use this data in farm",
    )
