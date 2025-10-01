from odoo import models


class HarvestTeam(models.Model):
    _inherit = "estate.harvest.team"

    def get_api_domain(self):
        domain = [("active", "=", True)]
        return domain

    def get_team_data(self, company=None):
        res = []
        domain = self.get_api_domain()
        if company:
            domain.append(("company_id", "=", company))
        data = self.sudo().with_company(company).search(domain)
        if data:
            for team in data:
                res.append(self._prepare_data_response(team))
        return res

    def _prepare_data_response(self, data):
        return {
            "id": data.id,
            "name": data.name,
            "manager_id": data.manager_id.id or 0,
            "foreman_id": data.foreman_id.id or 0,
            "clerk_id": data.clerk_id.id or 0,
            "assistant_id": data.assistant_id.id or 0,
            "recorder_id": data.recorder_id.id or 0,
            "labour_ids": [labour.id for labour in data.labour_ids] or [],
        }
