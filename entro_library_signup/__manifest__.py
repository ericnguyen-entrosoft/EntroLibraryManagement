# -*- coding: utf-8 -*-
{
    'name': 'Entro: Library Signup Enhancement',
    'version': '18.0.1.0.0',
    'category': 'Library',
    'summary': 'Enhanced signup with approval workflow for library members',
    'description': """
        Library Signup Enhancement
        ===========================
        * Extended signup form with additional information
        * Member type selection
        * Phone number and address
        * ID card/Student ID
        * Pending approval state
        * Library manager approval interface
        * Email notifications
        * Auto-create borrower type assignment
    """,
    'author': 'Entro',
    'website': 'https://www.entro.vn',
    'depends': [
        'entro_library',
        'entro_library_website',
        'auth_signup',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data
        'data/mail_template_data.xml',

        # Views
        'views/library_signup_request_views.xml',
        'views/signup_templates.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
