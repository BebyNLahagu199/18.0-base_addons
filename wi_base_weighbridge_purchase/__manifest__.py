{
    "name": "Purchase Order for Weighbridge",
    "summary": """
        The module is used to integrate the purchase process with a weighbridge scale,
        automating the creation of purchase orders when the weighbridge scale is posted.
    """,
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["imstefannyyy"],
    "website": "https://github.com/witech-io/base_addons",
    "category": "Manufacturing/Manufacturing",
    "version": "18.0.1.1.0",
    "depends": ["wi_base_weighbridge", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_weighbridge_view.xml",
        "views/purchase_weighbridge_scale_view.xml",
        "views/purchase_order_view.xml",
        "views/res_config_settings_view.xml",
        "views/purchase_menuitem.xml",
        "views/weighbridge_weighbridge_view.xml",
    ],
    "installable": True,
    "license": "OPL-1",
    "module_type": "official",
}
