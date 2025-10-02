from odoo import models


class FactoryQualityType(models.Model):
    _inherit = "factory.quality.type"

    def get_api_domain(self):
        return []

    def get_product_quality_type(self, company=None):
        res = []
        domain = self.get_api_domain()
        data = self.sudo().search(domain)
        if data:
            for qtype in data:
                res.append(self._prepare_data_prod_categ(qtype))
        return res

    def _prepare_data_prod_categ(self, data):
        return {
            "id": data.id,
            "active": data.active,
            "name": data.name,
            "description": data.description,
            "unit": data.unit,
        }
