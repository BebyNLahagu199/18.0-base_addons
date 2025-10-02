from dateutil import parser

from odoo import fields, models


class WeighbridgeQualityControl(models.Model):
    _inherit = "weighbridge.quality.control"

    def _get_required_fields(self):
        return {
            "ref_id": (int, str),
            "name": str,
            "scale_no": str,
            "delivery_no": str,
            "penalty_info": list,
        }

    def create_quality_control_data(self, requests, company=None):
        try:
            success_data = []
            failed_data = []
            code = 201
            savepoint = self.env.cr.savepoint()
            for data in requests:
                try:
                    rec_exist = self.sudo().search([("name", "=", data["name"])])
                    if not rec_exist:
                        savepoint = self.env.cr.savepoint()
                        qc_data = self.prepare_quality_control_data(data)
                        if qc_data:
                            quality = self.sudo().with_company(company).create(qc_data)
                            quality._auto_posting()
                            name = "%(qc_name)s - %(scale_name)s" % {
                                "qc_name": quality.name,
                                "scale_name": quality.weighbridge_scale_id.name,
                            }
                            success_data.append(
                                self.prepare_response_data(
                                    quality.id,
                                    name,
                                    data.get("ref_id"),
                                    "success",
                                    "Record Created Successfully",
                                )
                            )
                        else:
                            exist = (
                                self.env["quality.control.json"]
                                .sudo()
                                .search([("name", "=", data["name"])])
                            )
                            if not exist:
                                json_qc = (
                                    self.env["quality.control.json"]
                                    .sudo()
                                    .create({"name": data["name"], "json": data})
                                )
                                success_data.append(
                                    self.prepare_response_data(
                                        json_qc.id,
                                        "{} - {}".format(
                                            data["name"], data["scale_no"]
                                        ),
                                        data["ref_id"],
                                        "success",
                                        "Data is Kept",
                                    )
                                )
                            else:
                                failed_data.append(
                                    self.prepare_response_data(
                                        exist.id,
                                        exist.name,
                                        data.get("ref_id"),
                                        "failed",
                                        (
                                            f"Record with the name '{data['name']}' "
                                            f"already exists (ID: {exist.id})."
                                        ),
                                    )
                                )
                    else:
                        name = (
                            f"{rec_exist.name} - {rec_exist.weighbridge_scale_id.name}"
                        )
                        failed_data.append(
                            self.prepare_response_data(
                                rec_exist.id,
                                name,
                                data.get("ref_id"),
                                "failed",
                                "Record Already Exists",
                            )
                        )
                except Exception as e:
                    code = 206
                    failed_data.append(
                        self.prepare_response_data(
                            None,
                            "{} - {}".format(data["name"], data["scale_no"]),
                            data["ref_id"],
                            "failed",
                            str(e),
                        )
                    )
                    savepoint.rollback()
                    continue
            if len(success_data) == 0:
                code = 400
            response = {"quality_control": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response
        except Exception as e:
            return 400, str(e), success_data

    def update_quality_control_data(self, requests, company=None):
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
                        qc_data = self.prepare_quality_control_data(data)
                        if qc_data:
                            if record_exist.penalty_ids:
                                record_exist.penalty_ids.unlink()
                            if record_exist.return_ids:
                                record_exist.return_ids.unlink()
                            record_exist.sudo().write(qc_data)
                            name = "%(qc_name)s - %(scale_name)s" % {
                                "qc_name": record_exist.name,
                                "scale_name": record_exist.weighbridge_scale_id.name,
                            }
                            success_data.append(
                                self.prepare_response_data(
                                    record_exist.id,
                                    name,
                                    data.get("ref_id"),
                                    "success",
                                    "Record Updated Successfully",
                                )
                            )
                        else:
                            raise Exception("Invalid Scale No")
                    elif record_exist and record_exist.state != "draft":
                        raise Exception("Record Already Posted")
                    else:
                        exist = (
                            self.env["quality.control.json"]
                            .sudo()
                            .search([("name", "=", data["name"])])
                        )
                        if exist:
                            exist.sudo().write({"json": data})
                            success_data.append(
                                self.prepare_response_data(
                                    exist.id,
                                    exist.name,
                                    data.get("ref_id"),
                                    "success",
                                    "Kept Data is Updated Successfully",
                                )
                            )
                        else:
                            raise Exception("Record Not Found")
                except Exception as e:
                    code = 206
                    failed_data.append(
                        self.prepare_response_data(
                            None,
                            "{} - {}".format(data["name"], data["scale_no"]),
                            data["ref_id"],
                            "failed",
                            str(e),
                        )
                    )
                    savepoint.rollback()
                    continue
            if len(success_data) == 0:
                code = 400
            response = {"quality_control": success_data + failed_data}
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

    def prepare_quality_control_data(self, data):
        penalty_ids = []
        return_ids = []
        scale_no = data.get("scale_no", "")
        scale_id = (
            self.env["weighbridge.scale"].sudo().search([("name", "=", scale_no)])
        )
        if not scale_id:
            return False
        if "penalty_info" in data:
            penalty_ids = self._prepare_penalty_info(data["penalty_info"])
        if "return_info" in data:
            return_ids = self._prepare_return_info(data["return_info"])
        return {
            "name": data.get("name", ""),
            "date": parser.parse(data.get("date", ""), dayfirst=True).strftime(
                "%Y-%m-%d"
            ),
            "weighbridge_scale_id": scale_id.id,
            "delivery_number": data.get("delivery_no", ""),
            "penalty_ids": penalty_ids,
            "return_ids": return_ids,
        }

    def _prepare_penalty_info(self, penalty_info):
        penalty_ids = []
        for penalty in penalty_info:
            penalty_ids.append(
                (
                    0,
                    0,
                    {
                        "penalty_id": penalty["penalty_id"],
                        "penalty_qty": penalty["penalty_qty"],
                    },
                )
            )

        return penalty_ids

    def _prepare_return_info(self, return_info):
        return_ids = []
        for return_data in return_info:
            return_ids.append(
                (
                    0,
                    0,
                    {
                        "return_id": return_data["return_id"],
                        "return_qty": return_data["return_qty"],
                    },
                )
            )

        return return_ids

    def _auto_posting(self):
        for quality in self:
            if quality.company_id.auto_post_scale_ticket:
                quality.action_post()


class QualityControlJson(models.Model):
    _name = "quality.control.json"
    _description = "Quality Control Json"

    name = fields.Char()
    json = fields.Json()

    def upload_qc_json(self):
        data = self.search([])
        for qc in data:
            qc_sudo = self.env["weighbridge.quality.control"].sudo()
            qc_data = qc_sudo.prepare_quality_control_data(qc.json)
            if qc_data:
                record_exist = qc_sudo.search([("name", "=", qc_data["name"])])
                if not record_exist:
                    res = qc_sudo.create(qc_data)
                    res._auto_posting()
                    qc.unlink()
