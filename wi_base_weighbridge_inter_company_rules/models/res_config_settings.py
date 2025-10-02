from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wb_rule_type = fields.Selection(related="company_id.wb_rule_type", readonly=False)
    wb_intercompany_user_id = fields.Many2one(
        related="company_id.wb_intercompany_user_id", readonly=False, required=True
    )
    wb_rules_company_id = fields.Many2one(related="company_id", readonly=True)
    wb_intercompany_transaction_message = fields.Char(
        compute="_compute_wb_intercompany_transaction_message"
    )

    @api.depends("wb_rule_type", "company_id")
    def _compute_wb_intercompany_transaction_message(self):
        for record in self:
            if record.wb_rule_type == "weighbridge_scale":
                record.wb_intercompany_transaction_message = _(
                    "Generate a Shore Calculation when a company "
                    "confirms an Shore Calculation for %s. ",
                    record.company_id.name,
                )
            else:
                record.wb_intercompany_transaction_message = ""
