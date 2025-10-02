from odoo import api, fields, models

PARTNER_TYPE = [("internal", "Internal"), ("external", "External")]


class WeighbridgePartner(models.Model):
    _inherit = "res.partner"

    partner_type = fields.Selection(selection=PARTNER_TYPE, default="external")

    weighbridge_data = fields.Boolean(
        company_dependent=True,
        help="Check this box if this contact is a weighbridge data."
        "and you can use this data in weighbridge",
    )
    weighbridge_customer = fields.Boolean(
        string="Customer",
        company_dependent=True,
        help="Check this box if this contact is a weighbridge customer.",
    )
    weighbridge_vendor = fields.Boolean(
        string="Vendor",
        company_dependent=True,
        help="Check this box if this contact is a weighbridge customer.",
    )

    @api.onchange("weighbridge_data")
    def _onchange_weighbridge_data(self):
        self.weighbridge_customer = False
        self.weighbridge_vendor = False
