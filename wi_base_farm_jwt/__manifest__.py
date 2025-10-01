{
    "name": "Farm API JWT",
    "summary": "Farm API with JWT Token",
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["BebyNlahagu199"],
    "website": "https://github.com/witech-io/base_addons",
    "category": "Manufacturing/Manufacturing",
    "version": "18.0.1.1.0",
    "depends": ["wi_base_farm_stock", "wi_base_auth_jwt"],
    "data": [
        "security/ir.model.access.csv",
        "data/mobile_base_data.xml",
        "data/auth_jwt_validator.xml",
        "views/mobile_user_view.xml",
        "views/estate_operation_view.xml",
        "views/farm_menuitem.xml",
    ],
    "demo": [
        "demo/mobile_demo_data.xml",
    ],
    "installable": True,
    "license": "OPL-1",
    "module_type": "official",
}
