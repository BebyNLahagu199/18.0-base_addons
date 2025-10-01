from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_farm_api_domain(self):
        return [("farm_data", "=", True), ("active", "=", True)]

    def get_farm_partner_data(self, company=None):
        res = []
        domain = self.get_farm_api_domain()
        if company:
            company_domain = [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", company),
            ]
            domain.extend(company_domain)
        data = self.sudo().with_company(company).search(domain)
        if data:
            for partner in data:
                res.append(self._prepare_farm_data_partner(partner))
        return res

    def _prepare_farm_data_partner(self, data):
        return {"id": data.id, "name": data.name}
