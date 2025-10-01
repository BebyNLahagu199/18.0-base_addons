import logging

from dateutil import parser

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class EstateOperation(models.Model):
    _inherit = "estate.operation"

    assigned_to = fields.Many2many(
        "res.users",
        "estate_operation_assigned_users_rel",
        "operation_id",
        "user_id",
    )

    mobile_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_mobile_users",
        store=False,
    )

    def _compute_mobile_users(self):
        for record in self:
            record.mobile_user_ids = self.env["res.users"].search(
                [("mobile_user", "=", True)]
            )

    # Add and Update Data from API
    def _get_labour_required_fields(self):
        return {
            "member_id": int,
            "block_id": int,
        }

    def _get_required_fields(self):
        return {
            "ref_id": (int, str),
            "type_id": int,
            "name": str,
            "afdeling_id": int,
            "foreman_id": int,
            "foreman_extra_id": int,
            "assistant_id": int,
            "labour_ids": [
                self._get_labour_required_fields(),
            ],
        }

    def _get_required_harvest_fields(self):
        fields = self._get_required_fields()
        fields["clerk_id"] = int
        return fields

    def _get_required_upkeep_fields(self):
        fields = self._get_required_fields()
        fields["activity_id"] = int
        return fields

    def create_operation_data(self, requests, params=None, company=None):
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
                        operation_data = self.prepare_operation_data(data, params)
                        operation = (
                            self.sudo().with_company(company).create(operation_data)
                        )
                        if operation:
                            success_data.append(
                                self.prepare_response_data(
                                    operation.id,
                                    operation.name,
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
                                "Record Already Exists",
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
            response = {params: success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response
        except Exception as e:
            return 400, str(e), success_data

    def create_harvest_data(self, requests, company=None):
        return self.create_operation_data(requests, "harvest", company)

    def create_upkeep_data(self, requests, company=None):
        return self.create_operation_data(requests, "upkeep", company)

    def prepare_operation_data(self, data, params=None):
        if params == "harvest":
            return self.prepare_harvest_data(data)
        elif params == "upkeep":
            return self.prepare_upkeep_data(data)
        return False

    def _prepare_operation_data(self, data):
        return {
            "name": data.get("name", _("New")),
            "operation_date": parser.parse(
                data.get("date", ""), dayfirst=True
            ).strftime("%Y-%m-%d"),
            "operation_type_id": data.get("type_id", False),
            "afdeling_id": data.get("afdeling_id", False),
            "activity_id": data.get("activity_id", False),
            "team_id": data.get("team_id", False),
            "foreman_id": data.get("foreman_id", False),
            "foreman_extra_id": data.get("foreman_extra_id", False),
            "assistant_id": data.get("assistant_id", False),
            "recorder_id": data.get("recorder_id", False),
            "clerk_id": data.get("clerk_id", False),
            "assigned_to": data.get(
                "assigned_to", []
            ),  # Ensure assigned users are included
            "source_data": "mobile",
        }

    def prepare_harvest_data(self, data):
        fields = self._prepare_operation_data(data)
        harvest_fields = {
            "estate_harvest_ids": self._prepare_harvest_labour_data(
                data.get("labour_ids", False)
            ),
        }
        fields.update(harvest_fields)
        return fields

    def prepare_upkeep_data(self, data):
        fields = self._prepare_operation_data(data)
        labour_ids, materials = self._prepare_upkeep_labour_data(
            data.get("labour_ids", False)
        )
        upkeep_fields = {
            "labour_line_ids": labour_ids,
            "material_line_ids": self._prepare_upkeep_material_data(materials),
        }
        fields.update(upkeep_fields)
        return fields

    def prepare_response_data(self, system_id, name, ref_id, status, message):
        return {
            "id": system_id,
            "name": name,
            "ref_id": ref_id,
            "status": status,
            "message": message,
        }

    def _prepare_upkeep_material_data(self, data):
        material_ids = []
        for material in data:
            material_ids.append(
                (
                    0,
                    0,
                    {
                        "product_id": material.get("product_id", False),
                        "location_id": material.get("block_id", False),
                        "product_qty": material.get("qty", 0),
                    },
                )
            )
        return material_ids

    def _prepare_material_grouped(self, data):
        res = {}
        for material in data:
            fkey = "%s_%s" % (
                material.get("product_id", False),
                material.get("block_id", False),
            )
            res[fkey] = material.get("qty", 0) + res.get(fkey, 0)

        result = []
        for key, value in res.items():
            product_id, block_id = key.split("_")
            result.append(
                {
                    "product_id": int(product_id),
                    "block_id": int(block_id),
                    "qty": value,
                }
            )
        return result

    def _prepare_upkeep_labour_data(self, data):
        labour_ids = []
        materials = []
        for labour in data:
            material = labour.get("material_ids", [])
            if material:
                materials.extend(material)
            photo_ids = self._prepare_labour_photo_data(labour, "estate.upkeep.labour")
            labour_ids.append(
                (
                    0,
                    0,
                    {
                        "name": labour.get("name", _("New")),
                        "member_id": labour.get("member_id", False),
                        "location_id": labour.get("block_id", False),
                        "quantity": labour.get("qty", 0),
                        "planning_qty": labour.get("planning_qty", False),
                        "num_of_days": labour.get("workday", False),
                        "work_note": labour.get("work_note", False),
                        "attachment_ids": photo_ids,
                    },
                )
            )
        grouped_materials = self._prepare_material_grouped(materials)
        return labour_ids, grouped_materials

    def _prepare_harvest_labour_data(self, data):
        labour_ids = []
        for labour in data:
            penalty_ids = self._prepare_labour_penalty_data(labour)
            photo_ids = self._prepare_labour_photo_data(labour, "estate.harvest")
            labour_ids.append(
                (
                    0,
                    0,
                    {
                        "name": labour.get("name", _("New")),
                        "member_id": labour.get("member_id", False),
                        "block_id": labour.get("block_id", False),
                        "tph_code": labour.get("tph_code", False),
                        "harvest_qty_unit": labour.get("qty", False),
                        "planning_qty": labour.get("planning_qty", False),
                        "other_harvest_qty": labour.get("other_qty", False),
                        "harvest_area": labour.get("harvest_area", False),
                        "work_note": labour.get("work_note", False),
                        "penalty_harvest_ids": penalty_ids,
                        "attachment_ids": photo_ids,
                    },
                )
            )
        return labour_ids

    def _prepare_labour_penalty_data(self, labour):
        penalty_data = labour.get("penalty_ids", [])
        penalty_ids = []
        for penalty in penalty_data:
            penalty_ids.append(
                (
                    0,
                    0,
                    {
                        "penalty_type_id": penalty.get("penalty_id", False),
                        "penalty_qty": penalty.get("penalty_qty", False),
                    },
                )
            )
        return penalty_ids

    def _prepare_labour_photo_data(self, labour, model):
        photo_data = labour.get("photos", [])
        photo_ids = []
        for photo in photo_data:
            photo_ids.append(
                (
                    0,
                    0,
                    {
                        "name": photo.get("name", _("New")),
                        "datas": photo.get("image", False),
                        "type": "binary",
                        "res_model": model,
                    },
                )
            )
        return photo_ids

    def update_operation_data(self, requests, params=None, company=None):
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
                        operation_data = self.prepare_operation_data(data, params)
                        if record_exist.estate_harvest_ids:
                            record_exist.estate_harvest_ids.unlink()
                        if record_exist.labour_line_ids:
                            record_exist.labour_line_ids.unlink()
                        if record_exist.material_line_ids:
                            record_exist.material_line_ids.unlink()
                        record_exist.sudo().write(operation_data)
                        success_data.append(
                            self.prepare_response_data(
                                record_exist.id,
                                record_exist.name,
                                data.get("ref_id"),
                                "success",
                                "Record Updated Successfully",
                            )
                        )
                    elif record_exist and record_exist.state != "draft":
                        raise Exception(
                            "Record Already %(state)s"
                            % {"state": record_exist.state.capitalize()}
                        )
                    else:
                        raise Exception("Record Not Found")
                except Exception as e:
                    code = 206
                    failed_data.append(
                        self.prepare_response_data(
                            None, data["name"], data["ref_id"], "failed", str(e)
                        )
                    )
                    savepoint.rollback()
                    continue
            if len(success_data) == 0:
                code = 400
            response = {params: success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response
        except Exception as e:
            return 400, str(e), success_data

    def update_harvest_data(self, requests, company=None):
        return self.update_operation_data(requests, "harvest")

    def update_upkeep_data(self, requests, company=None):
        return self.update_operation_data(requests, "upkeep")

    # Get Data from API
    def get_api_domain(self, params=None):
        return [
            ("type_operation", "=", params),
            ("state", "=", "draft"),
            ("is_planned", "=", True),
            ("planning_state", "=", "confirm"),
        ]

    def get_planning_harvest_data(self, company=None):
        res = []

        domain = self.get_api_domain(params="harvest")

        if company:
            domain.append(("company_id", "=", company))

        current_user = self.env.user
        domain.append(("assigned_to", "in", [current_user.id]))

        records = self.sudo().search(domain)

        for rec in records:
            res.append(self._prepare_data_harvest(rec))
        return res

    def get_planning_upkeep_data(self, company=None):
        res = []

        domain = self.get_api_domain(params="upkeep")

        if company:
            domain.append(("company_id", "=", company))

        current_user = self.env.user
        domain.append(("assigned_to", "in", [current_user.id]))

        records = self.sudo().search(domain)

        for rec in records:
            res.append(self._prepare_data_upkeep(rec))
        return res

    def _prepare_data_operation(self, data):
        localdict = {
            "id": data.id,
            "name": data.name,
            "operation_date": data.operation_date.strftime("%Y/%m/%d"),
            "planning_date": data.planning_date.strftime("%Y/%m/%d"),
            "state": dict(self._fields["state"].selection).get(data.state),
            "type_id": data.operation_type_id.id or 0,
            "afdeling_id": data.afdeling_id.id or 0,
            "activity_id": data.activity_id.id or 0,
            "team_id": data.team_id.id or 0,
            "foreman_id": data.foreman_id.id or 0,
            "foreman_extra_id": data.foreman_extra_id.id or 0,
            "clerk_id": data.clerk_id.id or 0,
            "assistant_id": data.assistant_id.id or 0,
            "recorder_id": data.recorder_id.id or 0,
            "assigned_to": [
                {"id": user.id, "name": user.name} for user in data.assigned_to
            ]
            if data.assigned_to
            else [],
        }
        return localdict

    def _prepare_data_harvest(self, data):
        localdict = self._prepare_data_operation(data)
        localdict["member_ids"] = self._prepare_harvest_member_data(
            data.estate_harvest_ids
        )
        return localdict

    def _prepare_harvest_member_data(self, data):
        res = []
        for member in data:
            res.append(
                {
                    "id": member.id,
                    "name": member.name,
                    "member_id": member.member_id.id or 0,
                    "block_id": member.block_id.id or 0,
                    "tph_code": member.tph_code or "",
                    "planning_qty": member.planning_qty or 0,
                }
            )
        return res

    def _prepare_data_upkeep(self, data):
        localdict = self._prepare_data_operation(data)
        localdict["member_ids"] = self._prepare_upkeep_member_data(data.labour_line_ids)
        return localdict

    def _prepare_upkeep_member_data(self, data):
        res = []
        for member in data:
            res.append(
                {
                    "id": member.id,
                    "name": member.name,
                    "member_id": member.member_id.id or 0,
                    "block_id": member.location_id.id or 0,
                    "planning_qty": member.planning_qty or 0,
                    "workday": member.num_of_days or 1,
                }
            )
        return res


class OperationType(models.Model):
    _inherit = "estate.operation.type"

    def get_api_domain(self):
        return [("active", "=", True)]

    def get_operation_type_data(self, company=None):
        res = []
        domain = self.get_api_domain()
        data = self.sudo().search(domain)
        if data:
            for op_type in data:
                res.append(self._prepare_operation_type_data(op_type))
        return res

    def _prepare_operation_type_data(self, data):
        return {
            "id": data.id,
            "name": data.name,
            "code": data.code,
            "type": data.type_operation,
        }
