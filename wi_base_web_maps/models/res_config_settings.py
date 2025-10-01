import requests

from odoo import _, api, fields, models
from odoo.http import request


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    maps_box_token = fields.Char(
        config_parameter="wi_base_web_maps.token_maps_box",
        string="Token Maps Box",
        help="Necessary for some functionalities in the custom maps view",
        copy=True,
        default="",
        store=True,
    )

    @api.onchange("maps_box_token")
    def _onchange_maps_box_token(self):
        if not self.maps_box_token:
            return
        maps_box_token = self.env["ir.config_parameter"].get_param(
            "wi_base_web_maps.token_maps_box"
        )
        if self.maps_box_token == maps_box_token:
            return

        url1 = "https://api.mapbox.com/directions/v5/mapbox/driving/"
        url2 = "-73.989%2C40.733%3B-74%2C40.733"
        url = url1 + url2
        headers = {
            "referer": request.httprequest.headers.environ.get("HTTP_REFERER"),
        }
        params = {
            "access_token": self.maps_box_token,
            "steps": "true",
            "geometries": "geojson",
        }
        try:
            result = requests.head(url=url, headers=headers, params=params, timeout=5)
            error_code = result.status_code
        except requests.exceptions.RequestException:
            error_code = 500
        if error_code == 200:
            return
        self.maps_box_token = ""
        if error_code == 401:
            return {"warning": {"message": _("The token input is not valid")}}
        elif error_code == 403:
            return {"warning": {"message": _("This referer is not authorized")}}
        elif error_code == 500:
            return {"warning": {"message": _("The MapBox server is unreachable")}}
