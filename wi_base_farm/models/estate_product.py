from odoo import fields, models


class FarmProduct(models.Model):
    _name = "estate.product"
    _description = "Farm Product"

    block_id = fields.Many2one(
        comodel_name="estate.block",
        string="Block",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain="[('farm_data', '=', True)]",
        help="Product used in the Farm.",
    )
    categ_id = fields.Many2one(
        comodel_name="product.category",
        related="product_id.categ_id",
        readonly=True,
        string="Category",
    )
    amount = fields.Float(
        required=True,
        default=0.0,
    )
