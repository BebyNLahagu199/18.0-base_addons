from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _check_company_auto = True

    purchase_to_parent_company = fields.Boolean(
        related="company_id.purchase_to_parent_company", readonly=False
    )

    merge_purchase_order = fields.Boolean(
        readonly=False,
        related="company_id.merge_purchase_order",
    )

    separate_purchase_sequence = fields.Boolean(
        readonly=False,
        related="company_id.separate_purchase_sequence",
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    merge_purchase_order = fields.Boolean(
        readonly=False,
    )

    separate_purchase_sequence = fields.Boolean(
        readonly=False,
    )

    purchase_to_parent_company = fields.Boolean(
        help="""Ensures that purchase orders
        are automatically directed to the parent company""",
    )
