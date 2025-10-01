from odoo.http import request, route

from odoo.addons.wi_base_auth_jwt.controllers.base import BaseController

API_ENDPOINTS = {
    "GET": [
        (
            "/api/farm/employee",
            "hr.employee",
            "get_employee_data",
            "Success Get Employee Data",
        ),
        (
            "/api/farm/partners",
            "res.partner",
            "get_farm_partner_data",
            "Success Get Partner Data",
        ),
        (
            "/api/farm/estate",
            "estate.estate",
            "get_estate_data",
            "Success Get Estate Data",
        ),
        (
            "/api/farm/afdeling",
            "estate.estate",
            "get_afdeling_data",
            "Success Get Afdeling Data",
        ),
        ("/api/farm/block", "estate.block", "get_block_data", "Success Get Block Data"),
        (
            "/api/farm/product/category",
            "product.category",
            "get_farm_product_category_data",
            "Success Get Product Category Data",
        ),
        (
            "/api/farm/product/items",
            "product.product",
            "get_farm_product_data",
            "Success Get Product Data",
        ),
        (
            "/api/farm/penalty",
            "estate.activity.penalty",
            "get_penalty_data",
            "Success Get Penalty Data",
        ),
        (
            "/api/farm/activity",
            "account.analytic.account",
            "get_activity_data",
            "Success Get Activity Data",
        ),
        (
            "/api/farm/teams",
            "estate.harvest.team",
            "get_team_data",
            "Success Get Harvest Team Data",
        ),
        ("/api/farm/users", "res.users", "get_users_data", "Success Get User Data"),
        (
            "/api/farm/operation_type",
            "estate.operation.type",
            "get_operation_type_data",
            "Success Get Operation Type Data",
        ),
        (
            "/api/farm/planning/harvest",
            "estate.operation",
            "get_planning_harvest_data",
            "Success Get Planned Harvest Data",
        ),
        (
            "/api/farm/planning/upkeep",
            "estate.operation",
            "get_planning_upkeep_data",
            "Success Get Planned Upkeep Data",
        ),
    ],
    "POST": [
        ("/api/farm/harvesting", "estate.operation", "create_harvest_data", "harvest"),
        ("/api/farm/upkeeping", "estate.operation", "create_upkeep_data", "upkeep"),
        ("/api/farm/picking", "estate.picking", "create_picking_data", "picking"),
    ],
    "PUT": [
        ("/api/farm/harvesting", "estate.operation", "update_harvest_data", "harvest"),
        ("/api/farm/upkeeping", "estate.operation", "update_upkeep_data", "upkeep"),
        ("/api/farm/picking", "estate.picking", "update_picking_data", "picking"),
    ],
}


def generate_api_path_data(method):
    if method in ["POST", "PUT"]:
        return {
            path: {"model": model, "function": function, "key": key}
            for path, model, function, key in API_ENDPOINTS.get(method, [])
        }

    else:
        return {
            path: {"model": model, "function": function, "success_message": message}
            for path, model, function, message in API_ENDPOINTS.get(method, [])
        }


GET_PATH_DATA = generate_api_path_data("GET")
POST_PATH_DATA = generate_api_path_data("POST")
PUT_PATH_DATA = generate_api_path_data("PUT")


class FarmController(BaseController):
    def __init__(self):
        super().__init__()
        self.register_path(
            get_path=GET_PATH_DATA, post_path=POST_PATH_DATA, put_path=PUT_PATH_DATA
        )

    @route(
        "/api/farm/employee",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_employee_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/partners",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_farm_partner_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/estate",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_estate_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/afdeling",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_afdeling_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/block",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_block_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/product/category",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_product_category_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/product/items",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_product_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/penalty",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_penalty_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/activity",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_activity_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/teams",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_team_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/users",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_users_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/operation_type",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_operation_type_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/planning/harvest",
        type="http",
        auth="jwt_farm",
        methods=["GET"],
        csrf=False,
    )
    def get_planning_harvest_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/planning/upkeep",
        type="http",
        auth="jwt_farm",
        methods=["GET"],
        csrf=False,
    )
    def get_planning_upkeep_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/harvesting",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST"],
    )
    def add_harvest_data(self):
        return self.create_api_data(request)

    @route(
        "/api/farm/upkeeping",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST"],
    )
    def add_upkeep_data(self):
        return self.create_api_data(request)

    @route(
        "/api/farm/picking",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST"],
    )
    def add_picking_data(self):
        return self.create_api_data(request)

    @route(
        "/api/farm/harvesting",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["PUT"],
    )
    def update_harvest_data(self):
        return self.update_api_data(request)

    @route(
        "/api/farm/upkeeping",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["PUT"],
    )
    def update_upkeep_data(self):
        return self.update_api_data(request)

    @route(
        "/api/farm/picking",
        type="http",
        auth="jwt_farm",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["PUT"],
    )
    def update_picking_data(self):
        return self.update_api_data(request)
