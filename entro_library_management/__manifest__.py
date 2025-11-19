{
    'name': 'Entro: Library Management',
    'version': '1.0',
    'category': 'Library/',
    'sequence': 95,
    'summary': 'Complete library management system with book tracking and borrowing',
    'description': '''
        Library Management System
        =========================
        
        Features:
        - Book catalog management
        - ISBN tracking
        - Author and publisher information
        - Borrowing and return tracking
        - Library location management
        - Book condition tracking
        - Multiple views (Kanban, List, Form)
    ''',
    'website': 'https://entrosoft.org',
    'depends': [
        'stock', 'sale'
    ],
    'data': [
        'views/library_book_views.xml',
        'views/library_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
