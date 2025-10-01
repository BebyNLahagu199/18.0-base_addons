import json
import math

from odoo import _, api, fields, models


class FarmInspection(models.Model):
    _name = "farm.inspection"
    _inherit = ["mail.thread"]
    _description = "Farm Inspection"
    _rec_name = "inspection"

    sequence = fields.Integer()
    color = fields.Integer(tracking=True)
    name = fields.Char(readonly=True, default=lambda self: _("New"), copy=False)
    inspection = fields.Char(required=True)
    employee_id = fields.Many2one("hr.employee")
    inspection_start = fields.Datetime(required=True)
    inspection_end = fields.Datetime(required=True)
    distance = fields.Float(required=True, compute="_compute_distance")
    distance_display = fields.Char(
        string="Distance", compute="_compute_distance_display"
    )
    time = fields.Float(required=False, compute="_compute_time")
    duration_display = fields.Char(string="Duration", compute="_compute_time")

    issue_ids = fields.One2many("farm.issue", "inspection_id")
    coordinate_ids = fields.One2many("farm.coordinate", "inspection_id")

    coordinate_map = fields.Text(compute="_compute_coordinates_json")

    issue_count = fields.Integer(compute="_compute_upkeep_issue")
    upkeep_issue = fields.Many2one("farm.issue", compute="_compute_upkeep_issue")
    upkeep_count = fields.Integer(compute="_compute_upkeep_issue")
    issue_all = fields.Char(compute="_compute_upkeep_issue")

    start_battery_percentage = fields.Integer(string="Start Battery (%)")
    end_battery_percentage = fields.Integer(string="End Battery (%)")
    step = fields.Integer()

    company_id = fields.Many2one(
        "res.company", string="", default=lambda self: self.env.company
    )

    def name_get(self):
        result = []
        for record in self:
            inspection = record.inspection or _("No Inspection Name")
            result.append((record.id, inspection))
        return result

    @api.depends("coordinate_ids", "issue_ids")
    def _compute_coordinates_json(self):
        for rec in self:
            data = []
            for line in rec.coordinate_ids:
                if not line.id:
                    continue
                data.append(
                    {
                        "longitude": line.longitude,
                        "latitude": line.latitude,
                        "date": line.date.isoformat() if line.date else "",
                        "source": "coordinates",
                    }
                )
            for issue in rec.issue_ids:
                if not issue.id:
                    continue
                data.append(
                    {
                        "longitude": issue.longitude,
                        "latitude": issue.latitude,
                        "date": issue.date.isoformat() if issue.date else "",
                        "source": "issues",
                        "subject": issue.subject,
                        "id": issue.id,
                    }
                )
            sorted_data = sorted(data, key=lambda x: x["date"] or "")
            rec.coordinate_map = json.dumps({"data": sorted_data})

    @api.depends("coordinate_ids.latitude", "coordinate_ids.longitude")
    def _compute_distance(self):
        for rec in self:
            coords = rec.coordinate_ids.sorted(key=lambda c: c.sequence)
            total_distance = 0.0

            for i in range(len(coords) - 1):
                start = coords[i]
                end = coords[i + 1]
                segment_distance = self._haversine(
                    start.latitude, start.longitude, end.latitude, end.longitude
                )
                total_distance += segment_distance

            rec.distance = total_distance

    def _haversine(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        radius = 6371
        return radius * c

    @api.depends("distance")
    def _compute_distance_display(self):
        for rec in self:
            rec.distance_display = f"{rec.distance:.2f} Km"

    @api.depends("inspection_start", "inspection_end")
    def _compute_time(self):
        for rec in self:
            if rec.inspection_start and rec.inspection_end:
                duration = rec.inspection_end - rec.inspection_start

                rec.time = duration.total_seconds() / 3600.0

                total_minutes = int(duration.total_seconds() / 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                rec.duration_display = f"{hours} Hours {minutes} Minutes"
            else:
                rec.time = 0.0
                rec.duration_display = "00:00"

    @api.depends("issue_ids.states_id.state")
    def _compute_upkeep_issue(self):
        for record in self:
            all_issues = record.issue_ids
            draft_issues = all_issues.filtered(
                lambda r: r.states_id.state == "confirmed"
            )
            record.upkeep_issue = bool(draft_issues)
            record.upkeep_count = len(draft_issues)
            record.issue_count = len(all_issues)
            record.issue_all = f"{len(all_issues)}"

    def get_issue_smart(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Issue",
            "view_mode": "tree,form",
            "domain": [("inspection_id", "=", self.id)],
            "res_model": "farm.issue",
            "context": "{'create': False}",
        }
