import logging

from odoo.http import request, route

from odoo.addons.wi_base_auth_jwt.controllers.base import BaseController

_logger = logging.getLogger(__name__)

POST_PATH_DATA = {
    "/api/farm/inspection": {
        "model": "farm.inspection",
        "function": "create_inspection_data",
        "key": "inspections",
    },
}


class MainController(BaseController):
    def __init__(self):
        super().__init__()
        self.register_path(post_path=POST_PATH_DATA)

    @route(
        "/api/farm/inspection",
        type="http",
        auth="jwt_inspection",
        csrf=False,
        cors="*",
        methods=["POST"],
    )
    def add_inspection_data(self):
        return self.create_api_data(request)
