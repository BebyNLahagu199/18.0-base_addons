from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _check_company_auto = True

    merge_sale_order = fields.Boolean(
        readonly=False,
        related="company_id.merge_sale_order",
    )

    separate_sale_sequence = fields.Boolean(
        readonly=False,
        related="company_id.separate_sale_sequence",
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    merge_sale_order = fields.Boolean(
        readonly=False,
    )

    separate_sale_sequence = fields.Boolean(
        readonly=False,
    )
