import hashlib
import hmac
import json
import logging
import time
import uuid

from odoo.http import Controller, Response, request, route

DEFAULT_RESPONSE = {"status": 400, "message": "No Data Found", "data": []}

_logger = logging.getLogger(__name__)


class JWTTestController(Controller):
    @route(
        "/auth/token/get",
        type="http",
        auth="public",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST", "OPTIONS"],
    )
    def get_token_auth(self):
        request_id = str(uuid.uuid4())
        request_data = request.httprequest.get_json(silent=True)

        if not request_data:
            return self._generate_response(
                request_id, 400, "Request data is empty", None
            )

        user = (
            request.env["res.users"]
            .sudo()
            .search([("login", "=", request_data.get("email"))])
        )

        if user:
            request.update_env(user=user)
            request.session.uid = user.id

        else:
            _logger.warning(f"User not found: {request_data.get('email')}")
            return self._generate_response(request_id, 400, "Email not found", None)

        missing_params = self.validate_request_data(request_data, "get_token")
        if missing_params:
            return self._generate_response(
                request_id,
                400,
                f"Missing parameters: {', '.join(missing_params)}",
                None,
            )

        company_registry = user.company_id.company_registry
        params = self.extract_request_params(request_data, company_registry)
        expected_sign = self.generate_signature(*params[:5], request_data)

        if hmac.compare_digest(params[5], expected_sign):
            return self.process_valid_signature(
                DEFAULT_RESPONSE,
                params[0],
                params[4],
                params[6],
                params[7],
                params[2],
                params[8],
                params[3],
            )
        else:
            _logger.warning(
                "Invalid signature from IP: %s on %s",
                params[-1],
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(params[2]))),
            )
            return self._generate_response(request_id, 400, "Invalid signature", None)

    def validate_request_data(self, request_data, function):
        required_params = []

        if function == "get_authenticate":
            required_params = ["email", "api_license"]
        elif function == "get_token":
            required_params = [
                "timestamp",
                "sign",
                "email",
                "api_license",
            ]

        # Find missing parameters
        missing_params = [
            param for param in required_params if param not in request_data
        ]

        return missing_params

    def extract_request_params(self, request_data, company_registry):
        company_registry = request_data.get("company_registry", company_registry)

        return (
            request_data.get("email"),
            request.httprequest.path,
            request_data.get("timestamp"),
            request_data.get("api_license"),
            company_registry,
            request_data.get("sign"),
            request_data.get("aud"),
            request_data.get("iss"),
            request.httprequest.remote_addr,
        )

    def _generate_response(self, request_id, status, message, response):
        res = {
            "request id": request_id,
            "status": status,
            "message": message,
            "data": response,
        }
        return Response(json.dumps(res), content_type="application/json", status=200)

    def process_valid_signature(
        self, res, email, company_registry, aud, iss, timestamp, client_ip, api_license
    ):
        exp = int(time.time()) + 36000
        payload = {
            "aud": aud,
            "iss": iss,
            "exp": exp,
            "email": email,
            "company_registry": company_registry,
        }
        validator = request.env["auth.jwt.validator"]
        token = validator._get_jwt_token(payload, api_license)
        res = {
            "request_id": str(uuid.uuid4()),
            "status": 200,
            "message": "Get Token Success",
            "email": email,
            "company_registry": company_registry,
            "access_token": token,
            "expires_in": exp,
        }
        return Response(json.dumps(res), content_type="application/json", status=200)

    def generate_signature(
        self, email, path, timestamp, api_license, company_registry, request_data
    ):
        # default base string
        base_string = f"{email}{path}{timestamp}{api_license}"
        # have company_registry in request data we add it to base string
        if "company_registry" in request_data:
            base_string = f"{base_string}{company_registry}"
        sign = hmac.new(
            api_license.encode(), base_string.encode(), hashlib.sha256
        ).hexdigest()

        return sign

    @route(
        "/get/authenticate",
        type="http",
        auth="public",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["POST", "OPTIONS"],
    )
    def get_authenticate(self):
        request_id = str(uuid.uuid4())
        request_data = request.httprequest.get_json(silent=True)
        if not request_data:
            return self._generate_response(
                request_id,
                400,
                "Request data is empty",
                None,
            )

        missing_params = self.validate_request_data(request_data, "get_authenticate")
        if missing_params:
            missing_params_str = ", ".join(missing_params)
            return self._generate_response(
                request_id,
                400,
                f"The following required parameters are missing: {missing_params_str}",
                None,
            )

        partner = (
            request.env["res.partner"]
            .sudo()
            .search([("email", "=", request_data["email"])])
        )
        validator_license = (
            request.env["auth.jwt.validator"]
            .sudo()
            .search([("secret_key", "=", request_data["api_license"])])
        )

        if not partner or not validator_license:
            return self._generate_response(
                request_id, 400, "Email or API License not valid", None
            )

        return self._generate_response(
            request_id, 200, "Test Authenticate Success", None
        )

    @route(
        "/auth_jwt_demo/whoami-public-or-jwt",
        type="http",
        auth="public_or_jwt_demo",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def whoami_public_or_jwt(self):
        data = {"uid": request.env.uid}
        if getattr(request, "jwt_partner_id", None):
            partner = request.env["res.partner"].browse(request.jwt_partner_id)
            data.update(name=partner.name, email=partner.email)
        return Response(json.dumps(data), content_type="application/json", status=200)

    @route(
        "/auth_jwt_demo_cookie/whoami",
        type="http",
        auth="jwt_demo_cookie",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def whoami_cookie(self):
        data = {"uid": request.env.uid}
        if getattr(request, "jwt_partner_id", None):
            partner = request.env["res.partner"].browse(request.jwt_partner_id)
            data.update(name=partner.name, email=partner.email)
        return Response(json.dumps(data), content_type="application/json", status=200)

    @route(
        "/auth_jwt_demo_cookie/whoami-public-or-jwt",
        type="http",
        auth="public_or_jwt_demo_cookie",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def whoami_cookie_public_or_jwt(self):
        data = {"uid": request.env.uid}
        if getattr(request, "jwt_partner_id", None):
            partner = request.env["res.partner"].browse(request.jwt_partner_id)
            data.update(name=partner.name, email=partner.email)
        return Response(json.dumps(data), content_type="application/json", status=200)

    @route(
        "/auth_jwt_demo/keycloak/whoami",
        type="http",
        auth="jwt_demo_keycloak",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def whoami_keycloak(self):
        """To use with the demo_keycloak validator.

        You can play with this using the browser app in tests/spa and the
        identity provider in tests/keycloak.
        """
        data = {}
        if getattr(request, "jwt_partner_id", None):
            partner = request.env["res.partner"].browse(request.jwt_partner_id)
            data.update(name=partner.name, email=partner.email)
        return Response(json.dumps(data), content_type="application/json", status=200)

    @route(
        "/auth_jwt_demo/keycloak/whoami-public-or-jwt",
        type="http",
        auth="public_or_jwt_demo_keycloak",
        csrf=False,
        cors="*",
        save_session=False,
        methods=["GET", "OPTIONS"],
    )
    def whoami_public_or_keycloak(self):
        """To use with the demo_keycloak validator.

        You can play with this using the browser app in tests/spa and the
        identity provider in tests/keycloak.
        """
        data = {"uid": request.env.uid}
        if getattr(request, "jwt_partner_id", None):
            partner = request.env["res.partner"].browse(request.jwt_partner_id)
            data.update(name=partner.name, email=partner.email)
        else:
            # public
            data.update(name="Anonymous")
        return Response(json.dumps(data), content_type="application/json", status=200)
