from odoo import fields, models


class WeighbridgeWeighbridge(models.Model):
    _inherit = "weighbridge.weighbridge"

    sale_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Sale Orders Sequence",
        check_company=True,
    )

    separate_sale_sequence = fields.Boolean(
        related="company_id.separate_sale_sequence",
    )

    def _compute_show_sequence(self):
        res = super()._compute_show_sequence()
        for rec in self:
            if rec.separate_sale_sequence or res:
                rec.show_sequence = True
        return res
