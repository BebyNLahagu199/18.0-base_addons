from odoo import models


class EstateBlock(models.Model):
    _inherit = "estate.block"

    def get_api_domain(self):
        return [("active", "=", True)]

    def get_block_data(self, company=None):
        res = []
        domain = self.get_api_domain()
        if company:
            domain.append(("company_id", "=", company))
        data = self.sudo().with_company(company).search(domain)
        if data:
            for block in data:
                res.append(self._prepare_data_block(block))
        return res

    def _prepare_data_block(self, data):
        return {
            "id": data.id,
            "name": data.name,
            "code": data.code,
            "afdeling_id": data.estate_id.id or 0,
            "harvest_uom": data.estate_id.harvest_product_uom_id.name or "",
            "other_uom": data.estate_id.harvest_other_product_uom_id.name or "",
            "planting_state": data.planting_state_id.name or "",
            "planting_year": data.planting_year or "",
        }
