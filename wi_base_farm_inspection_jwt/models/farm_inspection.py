import logging
from datetime import datetime, timedelta

from odoo import _, models

_logger = logging.getLogger(__name__)


class FarmInspection(models.Model):
    _inherit = "farm.inspection"

    def _get_required_fields(self):
        return {
            "ref_id": (int, str),
            "inspection": str,
            "name": str,
            "inspection_start": str,
            "inspection_end": str,
        }

    def create_inspection_data(self, data, company=None):
        _logger.info("Received inspection data: %s", data)
        try:
            success_data = []
            failed_data = []
            code = 201

            if isinstance(data, dict):
                inspections = data.get("inspection") or data.get("inspections") or []
            elif isinstance(data, list):
                inspections = data
            else:
                inspections = []

            if not inspections:
                code = 400
                msg = "No inspection data provided"
                return code, msg, {"inspection": []}

            for item in inspections:
                try:
                    record_exist = self.sudo().search([("name", "=", item.get("name"))])
                    if not record_exist:
                        savepoint = self.env.cr.savepoint()
                        inspection_data = self.prepare_farm_inspection(item)
                        inspection = (
                            self.sudo().with_company(company).create(inspection_data)
                        )
                        if inspection:
                            success_data.append(
                                self.prepare_response_data(
                                    inspection.id,
                                    inspection.name,
                                    item.get("ref_id"),
                                    "success",
                                    "Record Created Successfully",
                                )
                            )
                    else:
                        failed_data.append(
                            self.prepare_response_data(
                                record_exist.id,
                                record_exist.name,
                                item.get("ref_id"),
                                "failed",
                                "Record Already Exists",
                            )
                        )
                except Exception as e:
                    code = 206
                    failed_data.append(
                        self.prepare_response_data(
                            False,
                            item.get("name"),
                            item.get("ref_id"),
                            "failed",
                            str(e),
                        )
                    )
                    savepoint.rollback()
                    continue

            if len(success_data) == 0 and len(failed_data) > 0:
                code = 400

            response = {"inspection": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response

        except Exception as e:
            return 400, str(e), {"inspection": []}

    def prepare_farm_inspection(self, data):
        return {
            "name": data.get("name", _("new")),
            "inspection": data.get("inspection"),
            "employee_id": data.get("employee_id", False),
            "inspection_start": datetime.strptime(
                data.get("inspection_start", "").strip(), "%d-%m-%Y %H:%M:%S"
            )
            + timedelta(hours=-7),
            "inspection_end": datetime.strptime(
                data.get("inspection_end", "").strip(), "%d-%m-%Y %H:%M:%S"
            )
            + timedelta(hours=-7),
            "step": int(data.get("step", 0)),
            "coordinate_ids": self.prepare_data_coordinate_ids(
                data.get("coordinates", [])
            ),
            "issue_ids": self.prepare_data_issue_ids(data.get("issues", [])),
        }

    def prepare_data_coordinate_ids(self, coordinates):
        coordinate_data = []
        for coord in coordinates:
            coordinate_data.append(
                (
                    0,
                    0,
                    {
                        "date": datetime.strptime(
                            coord.get("date", "").strip(), "%d-%m-%Y %H:%M:%S"
                        )
                        + timedelta(hours=-7),
                        "latitude": coord.get("latitude"),
                        "longitude": coord.get("longitude"),
                        "speed": coord.get("speed"),
                        "accuracy": coord.get("accuracy"),
                        "state": "true" if coord.get("status") else "false",
                    },
                )
            )
        return coordinate_data

    def prepare_data_issue_ids(self, issues):
        issue_data = []
        for issue in issues:
            images = []
            for img_data in issue.get("images", []):
                if img_data.get("image"):
                    image_value = img_data.get("image")
                    images.append(
                        (
                            0,
                            0,
                            {
                                "name": img_data.get("name", "image"),
                                "image": image_value,
                            },
                        )
                    )
            issue_data.append(
                (
                    0,
                    0,
                    {
                        "date": datetime.strptime(
                            issue.get("date", "").strip(), "%d-%m-%Y %H:%M:%S"
                        )
                        + timedelta(hours=-7),
                        "subject": issue.get("subject"),
                        "description": issue.get("description"),
                        "latitude": issue.get("latitude"),
                        "longitude": issue.get("longitude"),
                        "block_id": issue.get("block_id"),
                        "detail_location": issue.get("detail_location"),
                        "image_ids": images,
                    },
                )
            )
        return issue_data

    def prepare_response_data(self, system_id, name, ref_id, status, message):
        return {
            "id": system_id,
            "name": name,
            "ref_id": ref_id,
            "status": status,
            "message": message,
        }
