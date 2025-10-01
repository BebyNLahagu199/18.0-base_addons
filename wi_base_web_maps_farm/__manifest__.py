{
    "name": "Farm - Custom Map View",
    "summary": """
        Customs the Map View for Farm
    """,
    "author": "Witech Inovasi Indonesia.PT (Witech Enterprise)",
    "maintainers": ["imstefannyyy"],
    "website": "https://github.com/witech-io/base_addons",
    "category": "Hidden",
    "version": "18.0.1.1.0",
    "depends": ["wi_base_farm", "wi_base_web_maps"],
    "data": [
        "views/estate_estate_view.xml",
        "views/estate_block_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wi_base_web_maps_farm/static/src/js/**/*",
            "wi_base_web_maps_farm/static/src/xml/**/*",
        ],
    },
    # "web.assets_qweb": ["wi_palm_manufactory/static/src/xml/**/*"],
    "installable": True,
    "license": "OPL-1",
    "module_type": "official",
    "auto_install": False,
}
