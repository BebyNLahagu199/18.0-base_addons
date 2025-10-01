from odoo import fields, models


class InheritEstateOperation(models.Model):
    _inherit = "estate.operation"

    name = fields.Char()
    farm_issue_id = fields.Many2one("farm.issue")

    def action_post(self):
        res = super().action_post()

        state_done = self.env["farm.issue.stage"].search(
            [("state", "=", "done")], limit=1
        )

        for operation in self:
            if (
                operation.state == "posted"
                and operation.farm_issue_id
                and operation.farm_issue_id.states_id
                and operation.farm_issue_id.states_id.state == "confirmed"
                and state_done
            ):
                operation.farm_issue_id.states_id = state_done

        return res
