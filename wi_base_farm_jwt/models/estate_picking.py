from dateutil import parser

from odoo import models


class EstatePicking(models.Model):
    _inherit = "estate.picking"

    def _get_required_fields(self):
        return {
            "ref_id": (int, str),
            "tickets": [
                {"name": str},
            ],
            "loader_ids": [
                {"loader_id": int},
            ],
        }

    def create_picking_data(self, requests, company=None):
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
                        picking_data = self.prepare_picking_data(data)
                        picking = self.sudo().with_company(company).create(picking_data)
                        if picking:
                            success_data.append(
                                self.prepare_response_data(
                                    picking.id,
                                    picking.name,
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
                            None, data["name"], data["ref_id"], "failed", str(e)
                        )
                    )
                    savepoint.rollback()
                    continue
            if len(success_data) == 0:
                code = 400
            response = {"picking": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response
        except Exception as e:
            return 400, str(e), success_data

    def prepare_picking_data(self, data):
        return {
            "name": data.get("name", False),
            "scheduled_date": parser.parse(
                data.get("date", ""), dayfirst=True
            ).strftime("%Y-%m-%d"),
            "partner_id": data.get("partner_id", False),
            "driver": data.get("driver", False),
            "vehicle": data.get("licence", False),
            "harvest_ids": self._prepare_harvest_tickets_data(
                data.get("tickets", False)
            ),
            "loader_ids": self._prepare_loaders_data(data.get("loader_ids", False)),
        }

    def _prepare_harvest_tickets_data(self, data):
        ticket_ids = []
        for ticket in data:
            ticket_id = (
                self.env["estate.harvest"]
                .sudo()
                .search([("name", "=", ticket["name"])])
            )
            if ticket_id:
                ticket_ids.append(ticket_id.id)
            else:
                raise Exception("Ticket Not Found")
        return ticket_ids

    def _prepare_loaders_data(self, data):
        loader_ids = []
        for loader in data:
            loader_id = (
                self.env["hr.employee"]
                .sudo()
                .search([("id", "=", loader["loader_id"])])
            )
            if loader_id:
                loader_ids.append(loader_id.id)
        return loader_ids

    def prepare_response_data(self, system_id, name, ref_id, status, message):
        return {
            "id": system_id,
            "name": name,
            "ref_id": ref_id,
            "status": status,
            "message": message,
        }

    def update_picking_data(self, requests, company=None):
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
                        picking_data = self.prepare_picking_data(data)
                        record_exist.sudo().write(picking_data)
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
                        raise Exception("Record Already Posted")
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
            response = {"picking": success_data + failed_data}
            msg = self.env["auth.jwt.validator"].get_response_status(code)
            return code, msg, response
        except Exception as e:
            return 400, str(e), success_data
