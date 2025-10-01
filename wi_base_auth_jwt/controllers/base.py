import json

from odoo import _
from odoo.http import Controller, Response, request, route

DEFAULT_RESPONSE = {"status": 204, "message": "Data Not Found", "data": []}

API_ENDPOINTS = {
    "GET": [
        (
            "/api/base/company",
            "res.company",
            "get_company_data",
            "Success Get Companies Data",
        ),
        (
            "/api/farm/route",
            "auth.jwt.route",
            "get_route_data",
            "Success Get Routes Data",
        ),
        (
            "/api/weighbridge/route",
            "auth.jwt.route",
            "get_route_data",
            "Success Get Routes Data",
        ),
    ]
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
POST_PATH_DATA = {}
PUT_PATH_DATA = {}


class BaseController(Controller):
    def _generate_response(self, request_id, status, message, response):
        return {
            "request_id": request_id,
            "status": status,
            "message": message,
            "data": response,
        }

    def register_path(self, get_path=None, post_path=None, put_path=None):
        if get_path:
            GET_PATH_DATA.update(get_path)
        if post_path:
            POST_PATH_DATA.update(post_path)
        if put_path:
            PUT_PATH_DATA.update(put_path)
        return True

    def get_api_data(self, request, params=None):
        res = DEFAULT_RESPONSE
        company_id = getattr(request, "jwt_company_id", None)
        path = request.httprequest.path
        model = GET_PATH_DATA[path]["model"]
        function = GET_PATH_DATA[path]["function"]
        success_message = GET_PATH_DATA[path]["success_message"]
        data = (
            getattr(request.env[model], function)(company=company_id, params=params)
            if params
            else getattr(request.env[model], function)(company=company_id)
        )
        if data:
            res = self._generate_response(
                getattr(request, "jwt_request_id", None),
                200,
                success_message,
                data,
            )
        return Response(json.dumps(res), content_type="application/json", status=200)

    def generate_failed_response(self, models, data):
        failed_response = models.prepare_response_data(
            None,
            data.get("name", False),
            data.get("ref_id", False),
            "failed",
            data.get("error_message", False),
        )
        return failed_response

    def check_missing_or_incorrect_fields(self, request_data, required_fields):
        try:
            missing_fields, incorrect_type = self._check_validity_fields(
                request_data, required_fields, [], []
            )
            if missing_fields:
                return _(f"Required Fields Not Found: {', '.join(missing_fields)}")
            if incorrect_type:
                return _(f"Incorrect Data Type: {', '.join(incorrect_type)}")
            return False
        except Exception as e:
            return str(e)

    def _check_validity_fields(
        self, request_data, required_fields, missing_fields, incorrect_data_type
    ):
        missing_fields = missing_fields
        incorrect_data_type = incorrect_data_type
        for field in required_fields:
            if field not in request_data or not request_data[field]:
                missing_fields.append(field)
            elif isinstance(required_fields[field], list):
                for data in request_data[field]:
                    self._check_validity_fields(
                        data,
                        required_fields[field][0],
                        missing_fields,
                        incorrect_data_type,
                    )
            elif not isinstance(request_data[field], required_fields[field]):
                if isinstance(required_fields[field], tuple):
                    data_type_names = " or ".join(
                        [t.__name__ for t in required_fields[field]]
                    )
                    msg = f"Field {field} must be {data_type_names}"
                    incorrect_data_type.append(msg)
                else:
                    msg = f"Field {field} must be {required_fields[field].__name__}"
                    incorrect_data_type.append(msg)
        return missing_fields, incorrect_data_type

    def create_or_update_api_data(self, request, src_path):
        models = request.env[src_path["model"]]
        company_id = getattr(request, "jwt_company_id", None)
        request_id = getattr(request, "jwt_request_id", None)
        request_datas = getattr(request, "jwt_body", None)
        required_fields = models._get_required_fields()
        failed_data = []
        datas = request_datas[src_path["key"]]
        succeed_data = datas.copy()
        for data in datas:
            fields_error = self.check_missing_or_incorrect_fields(data, required_fields)
            if fields_error:
                failed = succeed_data.pop(succeed_data.index(data))
                failed["error_message"] = fields_error
                failed_data.append(failed)
        status, message, success_data = getattr(models, src_path["function"])(
            succeed_data, company=company_id
        )
        if failed_data:
            status = 206
            message = "Some data failed to create"
            for data in failed_data:
                failed_response = self.generate_failed_response(models, data)
                success_data[src_path["key"]].append(failed_response)
        res = self._generate_response(request_id, status, message, success_data)
        return Response(json.dumps(res), content_type="application/json")

    def create_api_data(self, request):
        path = request.httprequest.path
        post_path = POST_PATH_DATA[path]
        return self.create_or_update_api_data(request, post_path)

    def update_api_data(self, request):
        path = request.httprequest.path
        put_path = PUT_PATH_DATA[path]
        return self.create_or_update_api_data(request, put_path)

    @route(
        "/api/base/company",
        type="http",
        auth="jwt_base_module",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_company_data(self):
        return self.get_api_data(request)

    @route(
        "/api/farm/route",
        type="http",
        auth="jwt_base_module",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_farm_route(self):
        return self.get_api_data(request, params="farm")

    @route(
        "/api/weighbridge/route",
        type="http",
        auth="jwt_base_module",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def get_weighbridge_route(self):
        return self.get_api_data(request, params="weighbridge")
