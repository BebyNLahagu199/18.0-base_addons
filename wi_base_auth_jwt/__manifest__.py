{
    "name": "Auth JWT",
    "summary": "Base Module for Weighbridge",
    "version": "18.0.1.1.0",
    "category": "Hidden/Tools",
    "website": "https://github.com/witech-io/base_addons",
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["kelzxu-witech"],
    "module_type": "official",
    "license": "OPL-1",
    "external_dependencies": {"python": ["pyjwt", "cryptography"]},
    "application": False,
    "installable": True,
    "depends": [],
    "data": [
        "security/ir.model.access.csv",
        "views/auth_jwt_validator_views.xml",
        "views/auth_jwt_request_views.xml",
        "data/auth_jwt_validator.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wi_base_auth_jwt/static/src/scss/auth_jwt_log_views.scss",
        ]
    },
    "demo": [
        "demo/auth_jwt_validator.xml",
    ],
}
