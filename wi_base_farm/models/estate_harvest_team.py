from odoo import fields, models


class HarvestTeam(models.Model):
    _name = "estate.harvest.team"
    _description = "Harvest Team"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Team Name", required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.user.company_id
    )
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.user)
    manager_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
    )
    foreman_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
    )
    clerk_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
    )
    assistant_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
    )

    recorder_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
    )

    labour_ids = fields.Many2many(
        comodel_name="hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        string="Teams member",
        help="Team member that work on this activity",
    )
