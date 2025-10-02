from dateutil.relativedelta import relativedelta

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    weighbridge_data = fields.Boolean(
        company_dependent=True,
        help="Check this box if this category is a weighbridge data."
        "and you can use this data in weighbridge",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    allow_share_to_wb = fields.Boolean(
        related="categ_id.weighbridge_data",
        string="Allow Share to Weighbridge",
        company_dependent=True,
        store=True,
    )
    weighbridge_data = fields.Boolean(
        company_dependent=True,
        help="Check this box if this category is a weighbridge data."
        "and you can use this data in weighbridge",
    )

    def _compute_nbr_moves(self):
        res = super()._compute_nbr_moves()
        incoming_moves = self.env["stock.move.line"]._read_group(
            [
                ("product_id", "in", self.ids),
                ("state", "=", "done"),
                ("scale_type", "=", "acceptance"),
                ("date", ">=", fields.Datetime.now() - relativedelta(years=1)),
            ],
            ["product_id"],
            ["__count"],
        )
        outgoing_moves = self.env["stock.move.line"]._read_group(
            [
                ("product_id", "in", self.ids),
                ("state", "=", "done"),
                ("scale_type", "=", "shipment"),
                ("date", ">=", fields.Datetime.now() - relativedelta(years=1)),
            ],
            ["product_id"],
            ["__count"],
        )
        res_incoming = {product.id: count for product, count in incoming_moves}
        res_outgoing = {product.id: count for product, count in outgoing_moves}
        for product in self:
            product.nbr_moves_in += res_incoming.get(product.id, 0)
            product.nbr_moves_out += res_outgoing.get(product.id, 0)

        return res
