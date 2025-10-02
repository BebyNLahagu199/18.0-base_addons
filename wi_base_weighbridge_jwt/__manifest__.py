{
    "name": "Weighbridge API JWT",
    "summary": "Weighbridge API with JWT Token",
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["kelzxu-witech", "imstefannyyy"],
    "website": "https://github.com/witech-io/base_addons",
    "category": "Manufacturing/Manufacturing",
    "version": "18.0.1.1.0",
    "depends": ["wi_base_weighbridge", "wi_base_auth_jwt"],
    "data": [
        "security/ir.model.access.csv",
        "data/auth_jwt_validator.xml",
        "data/quality_control_cron.xml",
        "views/res_config_settings_view.xml",
    ],
    "installable": True,
    "license": "OPL-1",
    "module_type": "official",
}
