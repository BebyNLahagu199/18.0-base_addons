from odoo import models


class EstateEstate(models.Model):
    _inherit = "estate.estate"

    def get_api_domain(self, params=None):
        domain = [("location_type", "=", params), ("active", "=", True)]
        return domain

    def get_estate_data(self, company=None):
        res = []
        domain = self.get_api_domain("estate")
        if company:
            domain.append(("company_id", "=", company))
        data = self.sudo().with_company(company).search(domain)
        if data:
            for estate in data:
                response = self._prepare_data_response(estate)
                response.update(
                    {
                        "company_partner_id": estate.company_id.partner_id.id or 0,
                        "company_id": estate.company_id.id or 0,
                        "partner_id": estate.partner_id.id or 0,
                    }
                )
                res.append(response)
        return res

    def get_afdeling_data(self, company=None):
        res = []
        domain = self.get_api_domain("afdeling")
        if company:
            domain.append(("company_id", "=", company))
        data = self.sudo().with_company(company).search(domain)
        if data:
            for estate in data:
                response = self._prepare_data_response(estate)
                response.update(
                    {
                        "estate_id": estate.parent_id.id or 0,
                        "partner_id": estate.partner_id.id or 0,
                    }
                )
                res.append(response)
        return res

    def _prepare_data_response(self, data):
        return {
            "id": data.id,
            "name": data.display_name,
            "code": data.code,
        }
