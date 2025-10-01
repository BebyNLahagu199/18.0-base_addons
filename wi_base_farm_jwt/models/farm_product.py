from odoo import models


class ProductCategory(models.Model):
    _inherit = "product.category"

    def get_farm_api_domain(self):
        return [("farm_data", "=", True)]

    def get_farm_product_category_data(self, company=None):
        res = []
        domain = self.get_farm_api_domain()
        data = self.sudo().with_company(company).search(domain)
        if data:
            for category in data:
                res.append(self._prepare_data_category(category))
        return res

    def _prepare_data_category(self, data):
        return {
            "category_id": data.id,
            "parent_category_id": data.parent_id.name or "",
            "original_category_name": data.name or "",
            "display_category_name": data.display_name or "",
            "has_child": True if data.child_id else False,
        }


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_farm_api_domain(self):
        return [("farm_data", "=", True), ("active", "=", True)]

    def get_farm_product_data(self, company=None):
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
            for product in data:
                res.append(self._prepare_data_product(product))
        return res

    def _prepare_data_product(self, data):
        return {
            "item_id": data.id,
            "item_code": data.default_code or "",
            "item_name": data.name,
            "item_display_name": data.display_name or "",
            "category_id": data.categ_id.id or 0,
            "description": data.description or "",
            "uom": data.uom_id.name or "",
            "saleable": data.sale_ok,
            "purchaseable": data.purchase_ok,
        }
