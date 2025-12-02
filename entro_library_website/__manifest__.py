# -*- coding: utf-8 -*-
{
    'name': 'Entro: Thư Viện Website',
    'version': '18.0.1.0.0',
    'category': 'Library',
    'summary': 'Trang web công khai cho thư viện sách',
    'description': """
        Module website cho thư viện
        =============================
        * Trang danh sách sách công khai
        * Trang chi tiết sách
        * Lọc theo danh mục, tác giả, kho tài nguyên
        * Portal cho độc giả xem lịch sử mượn sách
        * Giỏ mượn sách trực tuyến
        * Quản lý đặt trước
        * Giao diện tiếng Việt
        * SEO-friendly URLs
        * Responsive design
    """,
    'author': 'Entro',
    'website': 'https://www.entro.vn',
    'depends': [
        'entro_library',
        'website',
        'portal',
    ],
    'data': [
        # Security
        'security/portal_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/website_menu.xml',

        # Views
        'views/library_website_category_views.xml',
        'views/library_book_views.xml',
        'views/library_media_views.xml',
        'views/templates.xml',
        'views/portal_templates.xml',
        'views/navbar_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # External libraries (CDN in template)
            'entro_library_website/static/src/scss/library_website.scss',
            'entro_library_website/static/src/scss/book_detail_gallery.scss',
            'entro_library_website/static/src/js/library_website.js',
            'entro_library_website/static/src/js/book_detail_gallery.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
