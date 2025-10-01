import base64
import binascii
import json
from datetime import timedelta

from odoo import http
from odoo.http import request


class GeoLocation(http.Controller):
    @http.route("/geo/location/data", type="json", auth="user", website=True)
    def get_company_geojson(self, company_id):
        try:
            company_id = int(company_id)
        except (TypeError, ValueError):
            return {"geojson": None, "error": "Invalid company_id"}
        company = (
            request.env["estate.estate"]
            .sudo()
            .search(
                [
                    ("company_id", "=", company_id),
                    ("location_type", "=", "estate"),
                ]
            )
        )

        geojson_list = []
        for estate in company:
            if not estate.geo_location:
                continue
            try:
                geojson_str = base64.b64decode(estate.geo_location).decode("utf-8")
                geojson_obj = json.loads(geojson_str)
                geojson_list.append(
                    {"id": estate.id, "name": estate.name, "geojson": geojson_obj}
                )
            except (binascii.Error, json.JSONDecodeError):
                continue

        return {"estates": geojson_list}


class GetInspection(http.Controller):
    @http.route("/get/inspection/location/data", type="json", auth="user", website=True)
    def inspections_json(self, company_id=None):
        domain = []
        if company_id:
            domain = [("company_id", "=", company_id)]

        inspections = (
            request.env["farm.inspection"]
            .sudo()
            .search_read(
                domain=domain,
                fields=[
                    "name",
                    "employee_id",
                    "inspection_start",
                    "inspection_end",
                    "coordinate_ids",
                    "issue_ids",
                    "step",
                    "start_battery_percentage",
                    "end_battery_percentage",
                ],
            )
        )

        employees_dict = {}
        for insp in inspections:
            emp_id = insp["employee_id"][0] if insp["employee_id"] else None
            emp_name = insp["employee_id"][1] if insp["employee_id"] else "Unknown"

            coords = (
                request.env["farm.coordinate"].sudo().browse(insp["coordinate_ids"])
            )
            coord_list = [
                {
                    "date": (c.date - timedelta(hours=7)).strftime("%d-%m-%Y %H:%M:%S")
                    if c.date
                    else None,
                    "latitude": c.latitude,
                    "longitude": c.longitude,
                    "accuracy": c.accuracy,
                    "speed": c.speed,
                    "state": c.state,
                }
                for c in coords
            ]

            issue = request.env["farm.issue"].sudo().browse(insp["issue_ids"])
            issue_list = [
                {
                    "id": i.id,
                    "date": (i.date - timedelta(hours=7)).strftime("%d-%m-%Y %H:%M:%S")
                    if i.date
                    else None,
                    "latitude": i.latitude,
                    "longitude": i.longitude,
                    "subject": i.subject,
                    "detail_location": i.detail_location,
                    "block_id": i.block_id,
                    "states_id": i.states_id,
                    "image_count": i.image_count,
                }
                for i in issue
            ]

            if emp_id not in employees_dict:
                employees_dict[emp_id] = {
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "inspections": [],
                }

            # Tambahkan setiap inspeksi sebagai route terpisah
            employees_dict[emp_id]["inspections"].append(
                {
                    "name": insp["name"],
                    "coordinates": coord_list,
                    "issue_ids": issue_list,
                    "inspection_start": insp["inspection_start"],
                    "inspection_end": insp["inspection_end"],
                    "step": insp["step"],
                    "start_battery_percentage": insp["start_battery_percentage"],
                    "end_battery_percentage": insp["end_battery_percentage"],
                }
            )

        return list(employees_dict.values())
