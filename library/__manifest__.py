# See LICENSE file for full copyright and licensing details.

{
    "name": "Library Management for Education ERP",
    "version": "17.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "category": "School Management",
    "website": "http://www.serpentcs.com",
    "license": "AGPL-3",
    "summary": "A Module For Library Management For School",
    "complexity": "easy",
    "depends": ["school", "stock", "delivery", "purchase"],
    "data": [
        "data/library_sequence.xml",
        "data/library_category_data.xml",
        "data/library_location_data.xml",
        "data/library_card_schedular.xml",
        "security/library_security.xml",
        "security/ir.model.access.csv",
        "views/card_details.xml",
        "report/report_view.xml",
        "report/qrcode_label.xml",
        "views/library_view.xml",
        "wizard/terminate_reason.xml",
        "wizard/book_receipt_wizard_view.xml",
        "wizard/book_borrow_wizard_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "library/static/src/css/library.css",
        ]
    },
    "demo": ["demo/library_demo.xml"],
    "image": ["static/description/Banner_library_17.png"],
    "installable": True,
    "application": True,
}
