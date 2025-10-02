import json

from odoo.http import Response, request, route

from odoo.addons.wi_base_auth_jwt.controllers.base import BaseController

GET_PATH_DATA = {
    "/api/weighbridge/weighbridges": {
        "model": "weighbridge.weighbridge",
        "function": "get_weighbridge_data",
        "success_message": "Success Get Weighbridge Data",
    },
    "/api/weighbridge/partners": {
        "model": "res.partner",
        "function": "get_weighbridge_partner_data",
        "success_message": "Success Get Partner Data",
    },
    "/api/weighbridge/product/categories": {
        "model": "product.category",
        "function": "get_weighbridge_product_categories_data",
        "success_message": "Success Get Product Categories Data",
    },
    "/api/weighbridge/product/items": {
        "model": "product.product",
        "function": "get_weighbridge_product_data",
        "success_message": "Success Get Product Items Data",
    },
    "/api/weighbridge/quality_type/penalty": {
        "model": "weighbridge.quality.type",
        "function": "get_quality_type",
        "success_message": "Success Get Penalty Quality Type Data",
    },
    "/api/weighbridge/quality_type/return": {
        "model": "weighbridge.quality.type",
        "function": "get_quality_type",
        "success_message": "Success Get Return Quality Type Data",
    },
    "/api/weighbridge/quality_type/fraction": {
        "model": "weighbridge.quality.type",
        "function": "get_quality_type",
        "success_message": "Success Get Fraction Quality Type Data",
    },
    "/api/weighbridge/product_type": {
        "model": "factory.quality.type",
        "function": "get_product_quality_type",
        "success_message": "Success Get Product Quality Type Data",
    },
    "/api/weighbridge/farm/estate": {
        "model": "estate.estate",
        "function": "get_estate_data",
        "success_message": "Success Get Estate Data",
    },
    "/api/weighbridge/farm/afdeling": {
        "model": "estate.estate",
        "function": "get_afdeling_data",
        "success_message": "Success Get Afdeling Data",
    },
    "/api/weighbridge/farm/block": {
        "model": "estate.block",
        "function": "get_block_data",
        "success_message": "Success Get Block Data",
    },
}
POST_PATH_DATA = {
    "/api/weighbridge/scale_ticket": {
        "model": "weighbridge.scale",
        "function": "create_scale_data",
        "key": "scale_ticket",
    },
    "/api/weighbridge/quality_control": {
        "model": "weighbridge.quality.control",
        "function": "create_quality_control_data",
        "key": "quality_control",
    },
    "/api/weighbridge/partner": {
        "model": "res.partner",
        "function": "create_partner_data",
        "key": "partner",
    },
    "/api/weighbridge/weighbridge": {
        "model": "weighbridge.weighbridge",
        "function": "create_weighbridge_data",
        "key": "weighbridge",
    },
    "/api/weighbridge/product": {
        "model": "product.template",
        "function": "create_product_data",
        "key": "product",
    },
}
PUT_PATH_DATA = {
    "/api/weighbridge/scale_ticket": {
        "model": "weighbridge.scale",
        "function": "update_scale_data",
        "key": "scale_ticket",
    },
    "/api/weighbridge/quality_control": {
        "model": "weighbridge.quality.control",
        "function": "update_quality_control_data",
        "key": "quality_control",
    },
}


class WeighbridgeController(BaseController):
    def __init__(self):
        super().__init__()
        self.register_path(
            get_path=GET_PATH_DATA, post_path=POST_PATH_DATA, put_path=PUT_PATH_DATA
        )

    @route(
        "/api/weighbridge/weighbridges",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_weighbridge_data(self):
        return self.get_api_data(request)

    @route(
        "/api/weighbridge/partners",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_wb_partner_data(self):
        return self.get_api_data(request)

    @route(
        "/api/weighbridge/product/categories",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_weighbridge_product_categories_data(self):
        return self.get_api_data(request)

    @route(
        "/api/weighbridge/farm/estate",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_weighbridge_estate_data(self):
        return self.get_api_data(request)

    @route(
        "/api/weighbridge/farm/afdeling",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_weighbridge_afdeling_data(self):
        return self.get_api_data(request)

    @route(
        "/api/weighbridge/farm/block",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_weighbridge_block_data(self):
        return self.get_api_data(request)

    @route(
        "/api/weighbridge/product/items",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_weighbridge_product_items_data(self):
        return self.get_api_data(request)

    @route(
        "/api/weighbridge/quality_type/penalty",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_quality_type_penalty_data(self):
        return self.get_api_data(request, params="penalty")

    @route(
        "/api/weighbridge/quality_type/return",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_quality_type_return_data(self):
        return self.get_api_data(request, params="return")

    @route(
        "/api/weighbridge/quality_type/fraction",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_quality_type_fraction_data(self):
        return self.get_api_data(request, params="fraction")

    @route(
        "/api/weighbridge/product_type",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_product_quality_type_data(self, **kwargs):
        return self.get_api_data(request)

    @route(
        "/api/weighbridge/scale_ticket",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST"],
    )
    def add_scale_ticket_data(self, **kwargs):
        return self.create_api_data(request)

    @route(
        "/api/weighbridge/quality_control",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST"],
    )
    def add_quality_control_data(self, **kwargs):
        return self.create_api_data(request)

    @route(
        "/api/weighbridge/partner",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST"],
    )
    def add_partner_data(self, **kwargs):
        return self.create_api_data(request)

    @route(
        "/api/weighbridge/weighbridge",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST"],
    )
    def add_weighbridge_data(self, **kwargs):
        return self.create_api_data(request)

    @route(
        "/api/weighbridge/product",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST"],
    )
    def add_product_data(self, **kwargs):
        return self.create_api_data(request)

    # Update Section
    def check_access_update_scale(self, company_id):
        company = request.env["res.company"].sudo().search([("id", "=", company_id)])
        return company.allow_update_scale_ticket

    def check_update_availability(self, request):
        company_id = getattr(request, "jwt_company_id", None)
        request_id = getattr(request, "jwt_request_id", None)
        try:
            if not company_id:
                raise Exception("Required Company Registry for JWT Token")
            access = self.check_access_update_scale(company_id)
            if not access:
                raise Exception("You don't have access to update the data")
        except Exception as e:
            res = self._generate_response(request_id, 400, "failed", str(e))
            return False, Response(
                json.dumps(res), content_type="application/json", status=400
            )
        return True, None

    @route(
        "/api/weighbridge/scale_ticket",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["PUT"],
    )
    def update_scale_ticket_data(self, **kwargs):
        allowed, res = self.check_update_availability(request)
        if allowed:
            return self.update_api_data(request)
        return res

    @route(
        "/api/weighbridge/quality_control",
        type="http",
        auth="jwt_weighbridge",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["PUT"],
    )
    def update_quality_control_data(self, **kwargs):
        allowed, res = self.check_update_availability(request)
        if allowed:
            return self.update_api_data(request)
        return res

    def check_missing_or_incorrect_fields(self, request_data, required_fields):
        # check if request data has 'is_return' and  'souce_id' fields
        # remove partner_id from required fields if exist
        if "is_return" in request_data and "source_id" in request_data:
            if "partner_id" in required_fields:
                required_fields.pop("partner_id", None)
        return super().check_missing_or_incorrect_fields(request_data, required_fields)
