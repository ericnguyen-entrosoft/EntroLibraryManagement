{
    'name': 'Entro: Quản lý Thư Viện Pháp Đăng',
    'version': '18.0.1.0.0',
    'category': 'Library',
    'summary': 'Quản lý thư viện sách',
    'description': """
        Module quản lý thư viện sách
        ================================
        * Quản lý thông tin sách
        * Quản lý tác giả
        * Quản lý nhà xuất bản
        * Quản lý vị trí lưu trữ
        * Quản lý trạng thái sách
        * Quản lý mượn/trả sách
        * Quản lý đặt trước sách
        * Quản lý độc giả
        * Tính phạt tự động
        * Thông báo email
        * Báo cáo và thống kê
    """,
    'author': 'Entro',
    'website': 'https://www.entro.vn',
    'depends': ['base', 'mail', 'barcodes'],
    'data': [
        # Data
        'data/library_data.xml',

        # Security
        'security/library_security.xml',
        'security/ir.model.access.csv',

        # Wizards
        'wizards/library_book_update_quantity_views.xml',
        'wizards/library_book_label_wizard_views.xml',
        'wizards/library_return_confirmation_views.xml',

        # Reports (must be loaded before views that reference them)
        'reports/library_card_report.xml',
        'reports/library_book_label_reports.xml',

        # Views
        'views/res_partner_views.xml',
        'views/library_book_image_views.xml',
        'views/library_book_views.xml',
        'views/library_book_quant_views.xml',
        'views/library_book_quant_count_views.xml',
        'views/library_book_statistics_views.xml',
        'views/library_borrower_type_views.xml',
        'views/library_management_views.xml',
        'views/library_author_views.xml',
        'views/library_publisher_views.xml',
        'views/library_category_views.xml',
        'views/library_series_views.xml',
        'views/library_location_views.xml',
        'views/library_quant_type_views.xml',
        'views/character_mapping_views.xml',
        'views/library_borrowing_views.xml',
        'views/library_reservation_views.xml',
        'views/res_config_settings_views.xml',

        # Menus (must be loaded before dashboard)
        'views/library_menus.xml',

        # Dashboard (must be loaded after menus)
        'views/library_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'entro_library/static/src/js/library_dashboard.js',
            'entro_library/static/src/xml/library_dashboard_templates.xml',
            'entro_library/static/src/scss/library_dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
