from odoo import fields, models


class FarmIssueImage(models.Model):
    _name = "farm.issue.image"
    _description = "Farm Issue Image"

    name = fields.Char()
    image = fields.Image()
    issue_id = fields.Many2one("farm.issue", ondelete="cascade")
