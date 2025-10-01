from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_company_details(self):
        return {
            "id": self.id,
            "name": self.name,
            "partner_id": self.partner_id.id,
            "parent_id": self.parent_id.id or 0,
            "company_registry": self.company_registry or "",
            "company_logo": str(self.logo.decode("utf-8")) if self.logo else "",
        }

    def get_company_data(self, company=None):
        res = []
        data = self.sudo().search([], order="id asc")
        if data:
            for company_data in data:
                res.append(company_data._get_company_details())
        return res
