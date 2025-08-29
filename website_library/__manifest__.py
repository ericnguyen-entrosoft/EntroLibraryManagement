# -*- coding: utf-8 -*-
{
    'name': 'Website Library',
    'category': 'Website/Library',
    'sequence': 50,
    'summary': 'Borrow books online from library',
    'description': """
Library Website Module
======================
This module extends the library management system with a website interface
that allows users to:
* Browse and search books online
* Add books to borrowing cart
* Request book borrowing (creates sales orders)
* Manage book returns through website
* Track borrowing history

Based on website_sale architecture, adapted for library borrowing workflow.
    """,
    'version': '18.0.1.0.0',
    'depends': [
        'website',
        'library',  # Our existing library module
        'sale',
        'stock',
        'website_mail',
        'portal',
        'website_payment',  # For checkout processes
        'portal_rating',    # For book reviews and ratings
        'digest'           # For analytics and reporting
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/website_library.xml',

        'data/data.xml',
        'data/mail_template_data.xml',

        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/templates.xml',
        'views/website_library_menus.xml',
        'views/website_views.xml',

        'wizard/return_book_wizard_views.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_frontend': [
            'website_library/static/src/scss/website_library.scss',
            'website_library/static/src/js/website_library.js',
            'website_library/static/src/js/library_cart.js',
            'website_library/static/src/js/library_search.js',
            'website_library/static/src/xml/website_library.xml',
        ],
        'web.assets_backend': [
            'website_library/static/src/js/backend_library.js',
            'website_library/static/src/scss/backend_library.scss',
        ],
        'website.assets_wysiwyg': [
            'website_library/static/src/js/library_editor.js',
        ],
    },
    'license': 'LGPL-3',
}
