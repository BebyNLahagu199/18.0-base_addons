from odoo import models


class WeighbridgePartner(models.Model):
    _inherit = "res.partner"

    def get_weighbridge_api_domain(self):
        return [
            ("weighbridge_data", "=", True),
            "|",
            ("active", "=", True),
            ("active", "=", False),
        ]

    def get_weighbridge_partner_data(self, company=None):
        res = []
        domain = self.get_weighbridge_api_domain()
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
                res.append(self._prepare_weighbridge_data_partner(partner))
        return res

    def _prepare_weighbridge_data_partner(self, data):
        return {
            "id": data.id,
            "active": data.active,
            "customer": data.weighbridge_customer,
            "vendor": data.weighbridge_vendor,
            "name": data.name,
            "parent": data.parent_id.name,
            "display_name": data.display_name,
            "type": data.type,
            "contact_type": data.partner_type,
            "street": data.street,
            "street2": data.street2,
            "city": data.city,
            "state_id": data.state_id.name,
            "zip": data.zip,
            "country_id": data.country_id.name,
            "categories": [
                {
                    "id": category.id,
                    "name": category.name,
                    "display_name": category.display_name,
                    "parent_id": category.parent_id.name,
                }
                for category in data.category_id
            ],
        }

    def _get_required_fields(self):
        return {
            "ref_id": (int, str),
            "name": str,
            "contact_type": str,
        }

    def create_partner_data(self, requests, company=None):
        try:
            success_data = []
            failed_data = []
            code = 201
            savepoint = self.env.cr.savepoint()
            for data in requests:
                try:
                    record_exist = self.sudo().search([("phone", "=", data["phone"])])
                    if not record_exist:
                        savepoint = self.env.cr.savepoint()
                        partner_data = self.prepare_partner_data(data)
                        partner = self.sudo().with_company(company).create(partner_data)
                        success_data.append(
                            self.prepare_response_data(
                                partner.id,
                                partner.name,
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
                                data["ref_id"],
                                "failed",
                                (
                                    f"A partner with the phone '{data['phone']}' "
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
            response = {"partner": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response
        except Exception as e:
            return 400, str(e), success_data

    def prepare_partner_data(self, data):
        return {
            "name": data.get("name", ""),
            "weighbridge_data": True,
            "weighbridge_customer": data.get("customer", False),
            "weighbridge_vendor": data.get("vendor", False),
            "type": data.get("type", "contact"),
            "partner_type": data.get("contact_type", "external"),
            "street": data.get("street", ""),
            "parent_id": data.get("parent_id", False),
            "phone": data.get("phone", ""),
            "mobile": data.get("mobile", ""),
            "email": data.get("email", ""),
            "company_type": data.get("company_type", "company"),
        }

    def prepare_response_data(self, system_id, name, ref_id, status, message):
        return {
            "id": system_id,
            "name": name,
            "ref_id": ref_id,
            "status": status,
            "message": message,
        }
