from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    auto_post_scale_ticket = fields.Boolean(
        string="Auto Posting Scale Ticket",
        readonly=False,
        help="Allow the system to perform auto-posting when "
        "receiving data from the API. This will prevent data "
        "from being updated via the API.",
    )

    allow_update_scale_ticket = fields.Boolean(
        readonly=False,
        help="Allow the system to perform update when "
        "receiving data from the API. This will prevent data "
        "from being updated via the API.",
    )

    def _get_company_details(self):
        res = super()._get_company_details()
        res.update(
            {
                "allow_update_quality_control": self.allow_update_scale_ticket,
            }
        )
        return res
