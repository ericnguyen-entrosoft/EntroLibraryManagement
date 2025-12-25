# -*- coding: utf-8 -*-
{
    'name': 'Entro: Thư Viện Website',
    'version': '18.0.1.0.0',
    'category': 'Library',
    'summary': 'Trang web công khai cho thư viện sách và phương tiện',
    'description': """
        Module website cho thư viện
        =============================
        * Trang danh sách sách công khai
        * Trang chi tiết sách
        * Lọc theo danh mục, tác giả, kho tài nguyên
        * Portal cho độc giả xem lịch sử mượn sách
        * Giỏ mượn sách trực tuyến
        * Quản lý đặt trước
        * Trang phương tiện với video, âm thanh, hình ảnh, tài liệu PDF
        * Trình phát video (HTML5, YouTube, Vimeo)
        * Trình xem PDF, hình ảnh với lightbox
        * Trình phát âm thanh
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
        'website_blog',
    ],
    'data': [
        # Security
        'security/portal_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/library_website_category_data.xml',
        'data/website_menu.xml',

        # Views
        'views/library_website_category_views.xml',
        'views/library_website_slider_views.xml',
        'views/library_book_views.xml',
        'views/library_media_views.xml',
        'views/home_templates.xml',
        'views/templates.xml',
        'views/media_templates.xml',
        'views/portal_templates.xml',
        'views/navbar_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # External libraries (CDN in template)
            'entro_library_website/static/src/scss/library_website.scss',
            'entro_library_website/static/src/scss/book_detail_gallery.scss',
            'entro_library_website/static/src/scss/library_media.scss',
            'entro_library_website/static/src/scss/mega_menu.scss',
            'entro_library_website/static/src/js/library_website.js',
            'entro_library_website/static/src/js/book_detail_gallery.js',
            'entro_library_website/static/src/js/library_media.js',
            'entro_library_website/static/src/js/hero_slider.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
