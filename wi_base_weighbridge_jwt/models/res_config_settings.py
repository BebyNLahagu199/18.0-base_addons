from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _check_company_auto = True

    auto_post_scale_ticket = fields.Boolean(
        string="Auto Posting Scale Ticket",
        readonly=False,
        help="Allow the system to perform auto-posting when "
        "receiving data from the API. This will prevent data "
        "from being updated via the API.",
        related="company_id.auto_post_scale_ticket",
    )

    allow_update_scale_ticket = fields.Boolean(
        readonly=False,
        help="Allow the system to perform update when receiving data from the API.",
        related="company_id.allow_update_scale_ticket",
    )

    @api.onchange("auto_post_scale_ticket")
    def onchange_auto_post_scale_ticket(self):
        if self.auto_post_scale_ticket:
            self.allow_update_scale_ticket = False

    @api.onchange("allow_update_scale_ticket")
    def onchange_allow_update_scale_ticket(self):
        if self.allow_update_scale_ticket:
            self.auto_post_scale_ticket = False
