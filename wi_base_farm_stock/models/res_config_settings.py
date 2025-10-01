from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_wi_base_seal_number_farm = fields.Boolean(
        string="Farm Seal Number",
        help="This module is used to integrate picking with seal number",
    )

    seal_digit = fields.Integer(
        related="company_id.seal_digit",
        readonly=False,
        help="This field is used to set the number of digits for the seal number",
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    seal_digit = fields.Integer(
        default=7,
        readonly=False,
        help="This field is used to set the number of digits for the seal number",
    )
