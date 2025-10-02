from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_wi_base_weighbridge_purchase = fields.Boolean(
        string="Weighbridge Purchase",
        help="This module is used to integrate weighbridge with purchase module",
    )

    module_wi_base_weighbridge_sale = fields.Boolean(
        string="Weighbridge Sale",
        help="This module is used to integrate weighbridge with sale module",
    )

    module_wi_base_weighbridge_jwt = fields.Boolean(
        string="Weighbridge API with JWT Token",
        help="This module is used to authenticate API with JWT Token",
    )

    module_wi_base_sale_requisition_weighbridge = fields.Boolean(
        string="Weighbridge Sale Requisition",
        help="This module is used to integrate weighbridge with "
        "sale requisition module",
    )

    module_wi_base_purchase_requisition_weighbridge = fields.Boolean(
        string="Weighbridge Purchase Requisition",
        help="This module is used to integrate weighbridge with "
        "purchase requisition module",
    )

    module_wi_base_seal_number_weighbridge = fields.Boolean(
        string="Weighbridge Seal Number",
        help="This module is used to integrate weighbridge with seal number",
    )

    module_wi_base_weighbridge_inter_company_rules = fields.Boolean(
        string="Manage Weighbridge Inter Company"
    )

    seal_digit = fields.Integer(
        related="company_id.seal_digit",
        readonly=False,
        help="This field is used to set the number of digits for the seal number",
    )

    group_shrinkage = fields.Boolean(
        string="Shrinkage",
        implied_group="wi_base_weighbridge.group_shrinkage",
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    seal_digit = fields.Integer(
        default=7,
        readonly=False,
        help="This field is used to set the number of digits for the seal number",
    )
