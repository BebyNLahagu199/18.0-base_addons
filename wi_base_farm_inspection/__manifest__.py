{
    "name": "Farm Inspection",
    "summary": """
        Farm Management System
    """,
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["BebyNLahagu199"],
    "website": "https://github.com/witech-io/base_addons",
    "category": "Manufacturing/Manufacturing",
    "version": "18.0.1.1.0",
    "depends": ["base", "mail", "hr", "wi_base_farm", "web"],
    "assets": {
        "web.assets_backend": [
            "wi_base_farm_inspection/static/src/xml/map_reporting.xml",
            "wi_base_farm_inspection/static/src/js/map_reporting.js",
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
            "wi_base_farm_inspection/static/src/xml/map_render.xml",
            "wi_base_farm_inspection/static/src/js/map_render.js",
        ],
        "web.assets_common": [
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
        ],
    },
    "data": [
        "data/farm_issue_stage_data.xml",
        "security/ir.model.access.csv",
        "security/inspection_security_data.xml",
        "views/farm_inspection_report.xml",
        "views/farm_inspection_views.xml",
        "views/farm_issue_views.xml",
        "views/estate_estate_views_inherit.xml",
        "views/farm_inspection_menu.xml",
    ],
    "installable": True,
    "application": True,
    "license": "OPL-1",
    "module_type": "official",
}
