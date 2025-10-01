{
    "name": "QR Code",
    "summary": """
        Use to add QR Code in any model with custom field.
    """,
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["imstefannyyy"],
    "website": "https://github.com/witech-io/base_addons",
    "category": "Hidden",
    "version": "18.0.1.1.0",
    "depends": ["base_setup"],
    "external_dependencies": {"python": ["cryptography"]},
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_view.xml",
    ],
    "installable": True,
    "license": "OPL-1",
    "module_type": "official",
    "auto_install": False,
}
