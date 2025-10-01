{
    "name": "Farm - Stock",
    "summary": "Bridge module between farm and stock",
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["kelzxu-witech"],
    "website": "https://github.com/witech-io/base_addons",
    "category": "Manufacturing/Manufacturing",
    "version": "18.0.1.1.0",
    "depends": [
        "wi_base_farm",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/farm_sequence.xml",
        "data/farm_restan_cron_job.xml",
        "report/picking_report_view.xml",
        "report/monitoring_bjr_report.xml",
        "wizard/monitoring_bjr_report_view.xml",
        "views/estate_restan_view.xml",
        "views/estate_picking_view.xml",
        "views/res_config_settings_view.xml",
        "views/farm_menuitem.xml",
        "wizard/estate_picking_wizard_view.xml",
    ],
    "demo": [
        "demo/demo_estate_picking.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wi_base_farm_stock/static/src/*.js",
        ]
    },
    "installable": True,
    "application": False,
    "license": "OPL-1",
    "module_type": "official",
}
