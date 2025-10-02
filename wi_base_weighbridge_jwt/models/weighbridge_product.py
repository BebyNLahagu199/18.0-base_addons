from odoo import models


class ProductCategory(models.Model):
    _inherit = "product.category"

    def get_api_domain(self):
        return [("weighbridge_data", "=", True)]

    def get_weighbridge_product_categories_data(self, company=None):
        res = []
        domain = self.get_api_domain()
        data = self.sudo().with_company(company).search(domain)

        if data:
            for category in data:
                res.append(self._prepare_data_category(category))
        return res

    def _prepare_data_category(self, data):
        return {
            "category_id": data.id,
            "parent_category_id": data.parent_id.id,
            "original_category_name": data.name,
            "display_category_name": data.display_name,
            "has_child": True if data.child_id else False,
        }


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_api_domain(self):
        return [
            ("allow_share_to_wb", "=", True),
            ("weighbridge_data", "=", True),
            "|",
            ("active", "=", True),
            ("active", "=", False),
        ]

    def get_weighbridge_product_data(self, company=None):
        res = []
        domain = self.get_api_domain()
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
                res.append(self._prepare_wb_data_product(product))
        return res

    def _prepare_wb_data_product(self, data):
        return {
            "id": data.id,
            "active": data.active,
            "code": data.default_code,
            "name": data.name,
            "display_name": data.display_name,
            "category_id": data.categ_id.id,
            "description": data.description,
            "uom": data.uom_id.name,
            "saleable": data.sale_ok,
            "purchaseable": data.purchase_ok,
        }


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_required_fields(self):
        return {
            "ref_id": (int, str),
            "name": str,
            "category_id": int,
            "code": str,
        }

    def create_product_data(self, requests, company=None):
        try:
            success_data = []
            failed_data = []
            code = 201
            savepoint = self.env.cr.savepoint()
            for data in requests:
                try:
                    record_exist = self.sudo().search(
                        [("default_code", "=", data["code"])], limit=1
                    )

                    if not record_exist:
                        savepoint = self.env.cr.savepoint()
                        product_data = self.prepare_product_data(data)
                        product = self.sudo().with_company(company).create(product_data)
                        product.product_variant_id.sudo().write(
                            {"weighbridge_data": True}
                        )
                        success_data.append(
                            self.prepare_response_data(
                                product.id,
                                product.name,
                                data.get("ref_id"),
                                "success",
                                "Record Created Successfully",
                            )
                        )
                    else:
                        failed_data.append(
                            self.prepare_response_data(
                                record_exist.id,
                                record_exist.name,
                                data.get("ref_id"),
                                "failed",
                                (
                                    f"A product with the code '{data['code']}' "
                                    f"already exists (ID: {record_exist.id})."
                                ),
                            )
                        )
                except Exception as e:
                    code = 206
                    failed_data.append(
                        self.prepare_response_data(
                            False,
                            data.get("name"),
                            data.get("ref_id"),
                            "failed",
                            str(e),
                        )
                    )
                    savepoint.rollback()
                    continue
            if len(success_data) == 0:
                code = 400
            response = {"product": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response
        except Exception as e:
            return 400, str(e), success_data

    def prepare_product_data(self, data):
        return {
            "name": data.get("name", ""),
            "default_code": data.get("code", ""),
            "categ_id": data.get("category_id", False),
        }

    def prepare_response_data(self, system_id, name, ref_id, status, message):
        return {
            "id": system_id,
            "name": name,
            "ref_id": ref_id,
            "status": status,
            "message": message,
        }
