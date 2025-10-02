from dateutil import parser

from odoo import models


class WeighbridgeScale(models.Model):
    _inherit = "weighbridge.scale"

    def _get_required_fields(self):
        return {
            "ref_id": (int, str),
            "name": str,
            "weighbridge_id": int,
            "product_id": int,
            "partner_id": int,
            "weight_in": (float, int),
            "weight_out": (float, int),
        }

    def create_scale_data(self, requests, company=None):
        try:
            success_data = []
            failed_data = []
            code = 201
            savepoint = self.env.cr.savepoint()
            for data in requests:
                try:
                    record_exist = self.sudo().search([("name", "=", data["name"])])
                    if not record_exist:
                        savepoint = self.env.cr.savepoint()
                        scale_data = self.prepare_weighbridge_scale_data(data)
                        scale = self.sudo().with_company(company).create(scale_data)
                        if scale:
                            scale._auto_posting()
                            success_data.append(
                                self.prepare_response_data(
                                    scale.id,
                                    scale.name,
                                    data["ref_id"],
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
                                    f"A scale with the name '{data['name']}' "
                                    f"already exists (ID: {record_exist.id})."
                                ),
                            )
                        )
                except Exception as e:
                    code = 206
                    failed_data.append(
                        self.prepare_response_data(
                            False,
                            data["name"],
                            data["ref_id"],
                            "failed",
                            str(e),
                        )
                    )
                    savepoint.rollback()
                    continue
            if len(success_data) == 0:
                code = 400
            response = {"scale_ticket": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response

        except Exception as e:
            return 400, str(e), success_data

    def update_scale_data(self, requests, company=None):
        try:
            success_data = []
            failed_data = []
            code = 201
            savepoint = self.env.cr.savepoint()
            for data in requests:
                try:
                    record_exist = self.sudo().search([("name", "=", data["name"])])
                    if record_exist and record_exist.state == "draft":
                        savepoint = self.env.cr.savepoint()
                        scale_data = self.prepare_weighbridge_scale_data(data)
                        # unlink existing quality control
                        if record_exist.quality_control_ids:
                            record_exist.quality_control_ids.unlink()
                        record_exist.sudo().write(scale_data)
                        if record_exist:
                            success_data.append(
                                self.prepare_response_data(
                                    record_exist.id,
                                    record_exist.name,
                                    data["ref_id"],
                                    "success",
                                    "Record Updated Successfully",
                                )
                            )
                    elif record_exist and record_exist.state != "draft":
                        raise Exception("Record Already Posted")
                    else:
                        raise Exception("Record Not Found")
                except Exception as e:
                    code = 206
                    failed_data.append(
                        self.prepare_response_data(
                            False, data["name"], data["ref_id"], "failed", str(e)
                        )
                    )
                    savepoint.rollback()
                    continue
            if len(success_data) == 0:
                code = 400
            response = {"scale_ticket": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response

        except Exception as e:
            return 400, str(e), success_data

    def prepare_response_data(self, system_id, name, ref_id, status, message):
        return {
            "id": system_id,
            "name": name,
            "ref_id": ref_id,
            "status": status,
            "message": message,
        }

    def prepare_weighbridge_scale_data(self, data):
        quality_control_ids = []
        load_ids = []
        source_id = False
        partner_id = data.get("partner_id", "")
        if "penalty_info" in data:
            quality_control_ids = self._prepare_quality_control_data(data)
        if "product_quality_info" in data:
            load_ids = self._prepare_load_data(data)
        if "is_return" in data:
            if data.get("source_id", ""):
                source_id = self.search([("id", "=", data.get("source_id", ""))])
                if source_id:
                    quantity = source_id.quantity
                    partner_id = source_id.partner_id.id

        return {
            "name": data.get("name", ""),
            "date": parser.parse(data.get("date", ""), dayfirst=True).strftime(
                "%Y-%m-%d"
            ),
            "weighbridge_id": data.get("weighbridge_id", ""),
            "delivery_number": data.get("delivery_no", ""),
            "product_id": data.get("product_id", ""),
            "driver_name": data.get("driver_name", ""),
            "driver_identity_no": data.get("driver_identity_no", ""),
            "licence_plate": data.get("licence_plate", ""),
            "partner_id": partner_id,
            "weight_in": data.get("weight_in", ""),
            "weight_out": data.get("weight_out", ""),
            "unload_in": data.get("unload_in", data.get("weight_out", "")),
            "unload_out": data.get("unload_out", data.get("weight_in", "")),
            "quantity": data.get("quantity", 0) if not source_id else quantity,
            "remark": data.get("remark", ""),
            "vehicle_in": parser.parse(data.get("vehicle_in"), dayfirst=True).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if data.get("vehicle_in")
            else False,
            "vehicle_out": parser.parse(
                data.get("vehicle_out"), dayfirst=True
            ).strftime("%Y-%m-%d %H:%M:%S")
            if data.get("vehicle_out")
            else False,
            "quality_control_ids": [quality_control_ids] if quality_control_ids else [],
            "load_ids": load_ids if load_ids else False,
            "seal_number": data.get("seal_number", ""),
            "is_return": data.get("is_return", False),
            "source_id": data.get("source_id", ""),
            "transporter_id": data.get("transporter_id", ""),
        }

    def _prepare_quality_control_data(self, data):
        penalty_info = self._prepare_penalty_info(data["penalty_info"])
        return (
            0,
            0,
            {
                "name": data["name"],
                "date": parser.parse(data["date"], dayfirst=True).strftime("%Y-%m-%d"),
                "delivery_number": data["delivery_no"],
                "penalty_ids": penalty_info,
            },
        )

    def _prepare_penalty_info(self, data):
        penalty_info = []
        for penalty in data:
            penalty_info.append(
                (
                    0,
                    0,
                    {
                        "penalty_id": penalty["penalty_id"],
                        "penalty_qty": penalty["penalty_qty"],
                    },
                )
            )
        return penalty_info

    def _prepare_load_data(self, data):
        load_info = []
        for load in data["product_quality_info"]:
            load_info.append(
                (
                    0,
                    0,
                    {
                        "type_id": load.get("type_id", ""),
                        "partner": load.get("partner_value", 0),
                        "company": load.get("company_value", 0),
                    },
                )
            )
        return load_info

    def _auto_posting(self):
        for scale in self:
            if scale.company_id.auto_post_scale_ticket:
                scale.action_post()
