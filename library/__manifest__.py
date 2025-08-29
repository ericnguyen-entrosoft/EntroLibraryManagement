{
    "name": "Library Management for Education ERP",
    "version": "18.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "category": "School Management",
    "website": "http://www.serpentcs.com",
    "license": "AGPL-3",
    "summary": "A Module For Library Management For School",
    "complexity": "easy",
    "depends": ["stock", "delivery", "purchase"],
    "data": [
        "security/library_security.xml",
        "security/ir.model.access.csv",
        "views/card_details.xml",
        "report/report_view.xml",
        "report/qrcode_label.xml",
        # Separated view files by model
        "views/library_author_views.xml",
        "views/library_card_views.xml",
        "views/product_views.xml",
        "views/user_library_views.xml",
        "views/menus.xml",
        # Wizard files
        "wizard/book_receipt_wizard_view.xml",
        "wizard/book_borrow_wizard_view.xml",
        "wizard/book_barcode_wizard_view.xml",
        "wizard/book_transfer_wizard_view.xml",
        # Report files
        "report/lot_barcode_label_report.xml",
        "report/library_card_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "library/static/src/css/library.css",
        ]
    },
    "image": ["static/description/Banner_library_17.png"],
    "installable": True,
    "application": True,
}
