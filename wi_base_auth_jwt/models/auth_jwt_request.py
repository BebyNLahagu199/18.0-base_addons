from datetime import datetime

from odoo import api, fields, models
from odoo.tools.misc import _format_time_ago


class AuthJwtRequest(models.Model):
    _name = "auth.jwt.request"
    _description = "Auth JWT Request History"
    _order = "request_date desc"

    name = fields.Char(required=True)
    authorization = fields.Char(required=True)
    request_id = fields.Char(required=True)
    method = fields.Selection(
        [("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("DELETE", "DELETE")],
        required=True,
    )
    url = fields.Char(required=True)
    payload = fields.Text(required=True)
    request_date = fields.Datetime(required=True)
    ip_address = fields.Char(required=True)
    country_id = fields.Many2one("res.country")
    country_flag = fields.Char(related="country_id.image_url", readonly=True)
    partner_id = fields.Many2one("res.partner")
    partner_image = fields.Binary(related="partner_id.image_1920")
    validator_id = fields.Many2one(
        "auth.jwt.validator", required=True, ondelete="cascade"
    )
    time_since_last_action = fields.Char(
        compute="_compute_time_statistics",
        help="Time since last page view. E.g.: 2 minutes ago",
    )
    request_body = fields.Text(readonly=False)

    @api.depends("request_date")
    def _compute_time_statistics(self):
        for request in self:
            request.time_since_last_action = _format_time_ago(
                self.env, (datetime.now() - request.request_date)
            )
