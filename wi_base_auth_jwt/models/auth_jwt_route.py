from odoo import fields, models


class AuthJwtRoute(models.Model):
    _name = "auth.jwt.route"
    _description = "Auth JWT Route"

    name = fields.Char()
    route = fields.Char()
    method = fields.Selection(
        [
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
            ("DELETE", "DELETE"),
        ]
    )
    validator_id = fields.Many2one("auth.jwt.validator", string="Validator")
    farm_data = fields.Boolean(default=False)
    weighbridge_data = fields.Boolean(default=False)

    def _get_domain(self, params):
        domain = []
        if params == "farm":
            domain = [("farm_data", "=", True)]
        elif params == "weighbridge":
            domain = [("weighbridge_data", "=", True)]
        return domain

    def get_route_data(self, company=None, params=None):
        res = []
        domain = self._get_domain(params)
        data = self.sudo()._read_group(domain, ["validator_id"], ["id:array_agg"])
        if data:
            for rec in data:
                res.append(self._prepare_data_response(rec))
        return res

    def _prepare_data_response(self, data):
        return {
            "name": data[0].audience,
            "routes": self._prepare_data(data[1]),
        }

    def _prepare_data(self, data):
        res = []
        for rec in data:
            route = self.sudo().browse(rec)
            res.append(
                {
                    "id": route.id,
                    "name": route.name,
                    "route": route.route,
                    "method": route.method,
                }
            )
        return res
