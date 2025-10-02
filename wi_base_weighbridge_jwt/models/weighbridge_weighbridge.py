from odoo import models


class WeighbridgeWeighbridge(models.Model):
    _inherit = "weighbridge.weighbridge"

    def get_weighbridge_api_domain(self):
        return []

    def get_weighbridge_data(self, company=None):
        res = []
        domain = self.get_weighbridge_api_domain()
        if company:
            company_domain = [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", company),
            ]
            domain.extend(company_domain)
        data = self.sudo().search(domain)
        if data:
            for weighbridge in data:
                res.append(self._prepare_weighbridge_data(weighbridge))
        return res

    def _prepare_weighbridge_data(self, data):
        return {
            "id": data.id,
            "name": data.name,
            "code": data.code,
            "company_id": data.company_id.id,
            "partner_id": data.partner_id.id,
        }

    def _get_required_fields(self):
        return {
            "ref_id": (int, str),
            "name": str,
            "code": str,
            "partner_id": int,
        }

    def create_weighbridge_data(self, requests, company=None):
        try:
            success_data = []
            failed_data = []
            code = 201
            savepoint = self.env.cr.savepoint()
            for data in requests:
                try:
                    record_exist = self.sudo().search(
                        [("code", "=", data["code"])], limit=1
                    )

                    if not record_exist:
                        savepoint = self.env.cr.savepoint()
                        weighbridge_data = self.prepare_weighbridge_data(data)
                        weighbridge = (
                            self.sudo().with_company(company).create(weighbridge_data)
                        )
                        success_data.append(
                            self.prepare_response_data(
                                weighbridge.id,
                                weighbridge.name,
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
                                    f"A weighbridge with the code '{data['code']}' "
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
            response = {"weighbridge": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response
        except Exception as e:
            return 400, str(e), success_data

    def prepare_weighbridge_data(self, data):
        return {
            "name": data.get("name", ""),
            "code": data.get("code", ""),
            "partner_id": data.get("partner_id", False),
            "type": "weighbridge",
        }

    def prepare_response_data(self, system_id, name, ref_id, status, message):
        return {
            "id": system_id,
            "name": name,
            "ref_id": ref_id,
            "status": status,
            "message": message,
        }
