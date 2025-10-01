{
    "name": "Custom Map View",
    "summary": """
        Customs the Map View for Odoo that can be used in any model
    """,
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["imstefannyyy"],
    "website": "https://github.com/witech-io/base_addons",
    "category": "Hidden",
    "version": "18.0.1.1.0",
    "depends": ["web", "base_setup", "base_geolocalize"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wi_base_web_maps/static/src/**/*",
        ],
    },
    "installable": True,
    "license": "OPL-1",
    "module_type": "official",
    "auto_install": True,
}
