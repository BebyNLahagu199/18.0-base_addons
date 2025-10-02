from odoo import fields, models

FRUIT_CATEGORIES = [
    ("quality", "Quality"),
    ("return", "Return"),
    ("deduction", "Deduction"),
    ("fraction", "Fraction"),
]

CALCULATION_TYPE = [
    ("per_qty", "Per Quantity"),
    ("per_unit", "Per Unit"),
    ("percentage", "Percentage"),
]


class WeighbridgeQualityType(models.Model):
    _name = "weighbridge.quality.type"
    _description = "Weighbridge Quality Type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True)

    categories = fields.Selection(
        selection=FRUIT_CATEGORIES,
        string="Category",
        default="quality",
        help="""
            Quality: The fruit is good and can be sold.
            Return: The fruit is not good and can be returned to the supplier.
            Deduction: The fruit is not good and cannot be returned to the supplier.
            Fraction: The fruit's maturity.
        """,
    )

    calculation_type = fields.Selection(
        selection=CALCULATION_TYPE,
        default="per_qty",
        tracking=True,
    )

    remark = fields.Text(
        string="Additional Information",
    )


class FactoryQualityType(models.Model):
    _name = "factory.quality.type"
    _description = "Factory Quality"
    _order = "name"

    name = fields.Char(required=True)
    description = fields.Char(required=True)
    unit = fields.Char()
    active = fields.Boolean(default=True)
