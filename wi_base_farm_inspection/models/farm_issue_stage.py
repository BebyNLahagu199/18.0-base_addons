from odoo import fields, models


class FarmIssueStage(models.Model):
    _name = "farm.issue.stage"
    _description = "Description"

    sequence = fields.Integer(default=1)
    name = fields.Char()
    state = fields.Selection(
        [
            ("not_bkm", "Not BKM"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
        ],
        default="not_bkm",
    )
