from odoo import fields, models

HARVEST_COUNT = [("by_unit", "By Unit"), ("by_weight", "By Weight")]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    farm_data = fields.Boolean(
        company_dependent=True,
        help="Check this box if this category is a farm data."
        "and you can use this data in farm",
    )

    harvest_by = fields.Selection(
        selection=HARVEST_COUNT,
        string="Harvest Count by",
        default="by_weight",
        copy=False,
        help="""If product is harvested, count stock quantity with:
        By Unit : stock quantity will be counted from Harvest Qty Unit.
        By Weight : stock quantity will be counted from Harvest Qty Weight.
        """,
    )


class ProductCategory(models.Model):
    _inherit = "product.category"

    farm_data = fields.Boolean(
        company_dependent=True,
        help="Check this box if this category is a farm data."
        "and you can use this data in farm",
    )
