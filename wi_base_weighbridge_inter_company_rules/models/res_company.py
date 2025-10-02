from odoo import SUPERUSER_ID, _, api, fields, models


class res_company(models.Model):
    _inherit = "res.company"

    wb_rule_type = fields.Selection(
        [
            ("not_synchronize", "Do not synchronize"),
            ("weighbridge_scale", "Synchronize Weighbridge Scale"),
        ],
        help="Select the type to setup inter company rules in selected company.",
        default="not_synchronize",
    )
    wb_intercompany_user_id = fields.Many2one(
        "res.users",
        default=SUPERUSER_ID,
        domain=["|", ["active", "=", True], ["id", "=", SUPERUSER_ID]],
        help="Responsible user for creation of documents "
        "triggered by intercompany rules.",
    )
    wb_intercompany_transaction_message = fields.Char(
        compute="_compute_wb_intercompany_transaction_message"
    )

    @api.depends("wb_rule_type", "name")
    def _compute_wb_intercompany_transaction_message(self):
        for record in self:
            if record.wb_rule_type == "weighbridge_scale":
                record.wb_intercompany_transaction_message = _(
                    "Generate a weighbridge scale when a company "
                    "confirms an weighbridge scale for %s. ",
                    record.name,
                )
            else:
                record.wb_intercompany_transaction_message = ""
