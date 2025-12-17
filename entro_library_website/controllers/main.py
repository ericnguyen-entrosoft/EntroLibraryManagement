# -*- coding: utf-8 -*-
import base64
from odoo import http, _, exceptions
from odoo.http import request
from odoo.addons.website.controllers.main import QueryURL
from werkzeug.exceptions import NotFound


class LibraryWebsite(http.Controller):

    @http.route([
        '/thu-vien',
        '/thu-vien/page/<int:page>',
        '/thu-vien/danh-muc/<model("library.website.category"):category>',
        '/thu-vien/danh-muc/<model("library.website.category"):category>/page/<int:page>',
    ], type='http', auth='public', website=True, sitemap=True)
    def library_books(self, page=1, category=None, search='', sortby=None, **kwargs):
        """Trang danh sách sách"""

        domain = [('website_published', '=', True)]

        # Filter by borrower type access control
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            if partner.borrower_type_id:
                # Show books that either:
                # 1. Have no type restrictions (allowed_borrower_type_ids is empty), OR
                # 2. Include the user's borrower type in allowed list
                domain += [
                    '|',
                    ('allowed_borrower_type_ids', '=', False),
                    ('allowed_borrower_type_ids', 'in', partner.borrower_type_id.id)
                ]

        # Tìm kiếm
        if search:
            domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('author_names', 'ilike', search),
                ('keywords', 'ilike', search),
                ('parallel_title', 'ilike', search),
            ]

        # Lọc theo danh mục website
        if category:
            domain += [('website_category_id', '=', category.id)]

        # Sorting
        sort_options = {
            'date_desc': 'registration_date desc, name',
            'date_asc': 'registration_date asc, name',
            'name_asc': 'name asc',
            'name_desc': 'name desc',
            'author_asc': 'author_names asc, name',
            'author_desc': 'author_names desc, name',
        }
        if not sortby or sortby not in sort_options:
            sortby = 'date_desc'
        order = sort_options[sortby]

        Book = request.env['library.book']
        books_count = Book.search_count(domain)

        # Phân trang
        ppg = 20  # products per page
        # Construct base URL based on whether we have a category filter
        if category:
            url = f'/thu-vien/danh-muc/{category.id}'
            url_args = {'search': search, 'sortby': sortby}
        else:
            url = '/thu-vien'
            url_args = {'search': search, 'sortby': sortby}

        pager = request.website.pager(
            url=url,
            url_args=url_args,
            total=books_count,
            page=page,
            step=ppg,
        )

        books = Book.search(
            domain,
            limit=ppg,
            offset=pager['offset'],
            order=order
        )

        # Lấy website categories
        website_categories = request.env['library.website.category'].search(
            [('active', '=', True)], order='sequence, name')

        # Keep query parameters
        keep = QueryURL(
            '/thu-vien',
            category=category and category.id,
            search=search,
            sortby=sortby
        )

        values = {
            'books': books,
            'books_count': books_count,
            'pager': pager,
            'search': search,
            'category': category,
            'website_categories': website_categories,
            'page_name': 'library_books',
            'keep': keep,
            'sortby': sortby,
            'sort_options': sort_options,
        }

        return request.render("entro_library_website.library_books", values)

    @http.route([
        '/thu-vien/sach/<model("library.book"):book>',
    ], type='http', auth='public', website=True, sitemap=True)
    def book_detail(self, book, **kwargs):
        """Trang chi tiết sách"""

        if not book.website_published or not book.active:
            return request.redirect('/thu-vien')

        # Check borrower type access
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            if partner.borrower_type_id and book.allowed_borrower_type_ids:
                # If book has type restrictions, check if user's type is allowed
                if partner.borrower_type_id not in book.allowed_borrower_type_ids:
                    return request.redirect('/thu-vien')

        # Tìm sách liên quan (cùng danh mục hoặc cùng tác giả)
        related_books = request.env['library.book'].search([
            ('website_published', '=', True),
            ('id', '!=', book.id),
            '|',
            ('category_id', '=', book.category_id.id),
            ('author_ids', 'in', book.author_ids.ids),
        ], limit=6)

        # Get meta tags
        meta_data = book._prepare_meta_tags()

        # Check if book is already in user's cart
        is_in_cart = False
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            draft_borrowing = request.env['library.borrowing'].search([
                ('borrower_id', '=', partner.id),
                ('state', '=', 'draft'),
            ], limit=1)

            if draft_borrowing:
                is_in_cart = bool(draft_borrowing.borrowing_line_ids.filtered(
                    lambda l: l.book_id.id == book.id
                ))

        values = {
            'book': book,
            'related_books': related_books,
            'is_public_user': request.env.user._is_public(),
            'is_in_cart': is_in_cart,
            'main_object': book,
            'page_name': 'book_detail',
        }
        values.update(meta_data)

        return request.render("entro_library_website.library_book_detail", values)

    @http.route(['/thu-vien/them-vao-gio'], type='json', auth='user', website=True)
    def add_to_borrowing_cart(self, book_id, **kwargs):
        """Thêm sách vào giỏ mượn (AJAX)"""

        book = request.env['library.book'].browse(int(book_id))
        book.action_add_to_borrowing()

        # Get cart count
        partner = request.env.user.partner_id
        cart_count = request.env['library.borrowing'].search_count([
            ('borrower_id', '=', partner.id),
            ('state', '=', 'draft'),
        ])

        return {
            'success': True,
            'message': _('Sách "%s" đã được thêm vào giỏ mượn!') % book.name,
            'cart_count': cart_count,
        }

    # ====================================
    # MEDIA ROUTES
    # ====================================

    @http.route([
        '/media',
        '/media/page/<int:page>',
        '/media/danh-muc/<model("library.website.category"):category>',
        '/media/danh-muc/<model("library.website.category"):category>/page/<int:page>',
    ], type='http', auth='public', website=True, sitemap=True)
    def library_media_list(self, page=1, category=None, search='', media_type=None, sortby=None, **kwargs):
        """Trang danh sách phương tiện"""

        domain = [('website_published', '=', True), ('active', '=', True)]

        # Filter by borrower type access control
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            if partner.borrower_type_id:
                domain += [
                    '|',
                    ('allowed_borrower_type_ids', '=', False),
                    ('allowed_borrower_type_ids', 'in', partner.borrower_type_id.id)
                ]

        # Filter by access level
        if request.env.user._is_public():
            domain += [('access_level', '=', 'public')]
        else:
            # Logged in users can see public and members content
            domain += [('access_level', 'in', ['public', 'members'])]

        # Search
        if search:
            domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('author', 'ilike', search),
                ('keywords', 'ilike', search),
                ('description', 'ilike', search),
            ]

        # Filter by category
        if category:
            domain += [('website_category_id', '=', category.id)]

        # Filter by media type
        if media_type:
            domain += [('media_type', '=', media_type)]

        # Sorting
        sort_options = {
            'date_desc': 'create_date desc, name',
            'date_asc': 'create_date asc, name',
            'name_asc': 'name asc',
            'name_desc': 'name desc',
            'views_desc': 'view_count desc',
            'downloads_desc': 'download_count desc',
        }
        if not sortby or sortby not in sort_options:
            sortby = 'date_desc'
        order = sort_options[sortby]

        Media = request.env['library.media']
        media_count = Media.search_count(domain)

        # Pagination
        ppg = 12  # media per page

        # Construct base URL
        if category:
            url = f'/media/danh-muc/{category.id}'
        else:
            url = '/media'

        url_args = {'search': search, 'sortby': sortby}
        if media_type:
            url_args['media_type'] = media_type

        pager = request.website.pager(
            url=url,
            url_args=url_args,
            total=media_count,
            page=page,
            step=ppg,
        )

        media_items = Media.search(
            domain,
            limit=ppg,
            offset=pager['offset'],
            order=order
        )

        # Get website categories
        website_categories = request.env['library.website.category'].search(
            [('active', '=', True)],
            order='sequence, name'
        )

        # Keep query parameters
        keep = QueryURL(
            '/media',
            category=category and category.id,
            search=search,
            media_type=media_type,
            sortby=sortby
        )

        values = {
            'media_items': media_items,
            'media_count': media_count,
            'pager': pager,
            'search': search,
            'category': category,
            'media_type': media_type,
            'website_categories': website_categories,
            'page_name': 'library_media',
            'keep': keep,
            'sortby': sortby,
            'sort_options': sort_options,
        }

        return request.render("entro_library_website.library_media_list", values)

    @http.route([
        '/media/<int:media_id>',
        '/media/<int:media_id>/<string:slug>',
    ], type='http', auth='public', website=True, sitemap=True)
    def library_media_detail(self, media_id, slug=None, **kwargs):
        """Trang chi tiết phương tiện"""

        media = request.env['library.media'].browse(media_id)

        if not media.exists() or not media.website_published or not media.active:
            return request.redirect('/media')

        # Check borrower type access
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            if partner.borrower_type_id and media.allowed_borrower_type_ids:
                if partner.borrower_type_id not in media.allowed_borrower_type_ids:
                    return request.redirect('/media')

        # Check access level
        if request.env.user._is_public() and media.access_level != 'public':
            return request.redirect('/web/login?redirect=/media/%s' % media_id)

        # Increment view count
        media.sudo().write({'view_count': media.view_count + 1})

        # Log view
        if not request.env.user._is_public():
            try:
                request.env['library.media.view.log'].sudo().create({
                    'media_id': media.id,
                    'user_id': request.env.user.id,
                })
            except Exception:
                pass  # Ignore if log creation fails

        # Find related media (same category or same type)
        related_domain = [
            ('website_published', '=', True),
            ('active', '=', True),
            ('id', '!=', media.id),
        ]

        if request.env.user._is_public():
            related_domain += [('access_level', '=', 'public')]
        else:
            related_domain += [('access_level', 'in', ['public', 'members'])]

        related_media = request.env['library.media'].search([
            *related_domain,
            '|',
            ('category_id', '=', media.category_id.id),
            ('media_type', '=', media.media_type),
        ], limit=6, order='view_count desc')

        # Get meta tags
        meta_data = media._prepare_meta_tags()

        # Detect YouTube/Vimeo URLs
        youtube_id = None
        vimeo_id = None
        if media.storage_type == 'url' and media.file_url:
            import re
            # YouTube detection
            youtube_patterns = [
                r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)',
                r'youtube\.com\/embed\/([^&\s]+)',
            ]
            for pattern in youtube_patterns:
                match = re.search(pattern, media.file_url)
                if match:
                    youtube_id = match.group(1)
                    break

            # Vimeo detection
            vimeo_match = re.search(r'vimeo\.com\/(\d+)', media.file_url)
            if vimeo_match:
                vimeo_id = vimeo_match.group(1)

        values = {
            'media': media,
            'related_media': related_media,
            'is_public_user': request.env.user._is_public(),
            'main_object': media,
            'page_name': 'media_detail',
            'youtube_id': youtube_id,
            'vimeo_id': vimeo_id,
        }
        values.update(meta_data)

        return request.render("entro_library_website.library_media_detail", values)

    @http.route(['/media/<int:media_id>/tai-xuong'], type='http', auth='public', website=True)
    def library_media_download(self, media_id, **kwargs):
        """Download media file"""

        media = request.env['library.media'].browse(media_id)

        if not media.exists() or not media.website_published or not media.active:
            return request.redirect('/media')

        if not media.is_downloadable:
            return request.render("website.403")

        if media.storage_type != 'file' or not media.file:
            return request.redirect('/media/%s' % media_id)

        # Check access level
        if request.env.user._is_public() and media.access_level != 'public':
            return request.redirect('/web/login?redirect=/media/%s' % media_id)

        # Increment download count
        media.sudo().write({'download_count': media.download_count + 1})

        # Return file
        return request.make_response(
            base64.b64decode(media.file),
            headers=[
                ('Content-Type', media.mime_type or 'application/octet-stream'),
                ('Content-Disposition',
                 f'attachment; filename="{media.filename}"'),
            ]
        )

    # ====================================
    # MEDIA ROUTES BY BORROWER TYPE
    # ====================================

    def _render_media_by_borrower_type(self, borrower_type, page=1, search='', sortby=None, title='', **kwargs):
        """Helper method to render media filtered by borrower type"""

        domain = [
            ('website_published', '=', True),
            ('active', '=', True),
            ('allowed_borrower_type_ids', 'in', borrower_type.id)
        ]

        # Filter by access level
        if request.env.user._is_public():
            domain += [('access_level', '=', 'public')]
        else:
            domain += [('access_level', 'in', ['public', 'members'])]

        # Search
        if search:
            domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('author', 'ilike', search),
                ('keywords', 'ilike', search),
                ('description', 'ilike', search),
            ]

        # Sorting
        sort_options = {
            'date_desc': 'create_date desc, name',
            'date_asc': 'create_date asc, name',
            'name_asc': 'name asc',
            'name_desc': 'name desc',
            'views_desc': 'view_count desc',
            'downloads_desc': 'download_count desc',
        }
        if not sortby or sortby not in sort_options:
            sortby = 'date_desc'
        order = sort_options[sortby]

        Media = request.env['library.media']
        media_count = Media.search_count(domain)

        # Pagination
        ppg = 12
        url = request.httprequest.path

        pager = request.website.pager(
            url=url,
            url_args={'search': search, 'sortby': sortby},
            total=media_count,
            page=page,
            step=ppg,
        )

        media_items = Media.search(
            domain,
            limit=ppg,
            offset=pager['offset'],
            order=order
        )

        # Get website categories
        website_categories = request.env['library.website.category'].search(
            [('active', '=', True)],
            order='sequence, name'
        )

        # Keep query parameters
        keep = QueryURL(
            url,
            search=search,
            sortby=sortby
        )

        values = {
            'media_items': media_items,
            'media_count': media_count,
            'pager': pager,
            'search': search,
            'category': None,
            'media_type': None,
            'borrower_type_filter': borrower_type.name,
            'website_categories': website_categories,
            'page_name': 'library_media',
            'page_title': title or f'Phương tiện - {borrower_type.name}',
            'keep': keep,
            'sortby': sortby,
            'sort_options': sort_options,
        }

        return request.render("entro_library_website.library_media_list", values)

    def _render_media_exclude_types(self, exclude_types, page=1, search='', sortby=None, title='', **kwargs):
        """Helper method to render media excluding specific borrower types"""

        # Build domain: media that either:
        # 1. Has no borrower type restrictions (allowed_borrower_type_ids is empty), OR
        # 2. Has restrictions but NOT including the excluded types
        domain = [
            ('website_published', '=', True),
            ('active', '=', True),
        ]

        # For each excluded type, we want: NOT in that type
        # This means: (no restrictions) OR (has restrictions but not this type)
        exclude_ids = [bt.id for bt in exclude_types]

        # Media with empty allowed_borrower_type_ids OR not containing excluded types
        domain += [
            '|',
            ('allowed_borrower_type_ids', '=', False),
            ('allowed_borrower_type_ids', 'not in', exclude_ids)
        ]

        # Filter by access level
        if request.env.user._is_public():
            domain += [('access_level', '=', 'public')]
        else:
            domain += [('access_level', 'in', ['public', 'members'])]

        # Search
        if search:
            domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('author', 'ilike', search),
                ('keywords', 'ilike', search),
                ('description', 'ilike', search),
            ]

        # Sorting
        sort_options = {
            'date_desc': 'create_date desc, name',
            'date_asc': 'create_date asc, name',
            'name_asc': 'name asc',
            'name_desc': 'name desc',
            'views_desc': 'view_count desc',
            'downloads_desc': 'download_count desc',
        }
        if not sortby or sortby not in sort_options:
            sortby = 'date_desc'
        order = sort_options[sortby]

        Media = request.env['library.media']
        media_count = Media.search_count(domain)

        # Pagination
        ppg = 12
        url = request.httprequest.path

        pager = request.website.pager(
            url=url,
            url_args={'search': search, 'sortby': sortby},
            total=media_count,
            page=page,
            step=ppg,
        )

        media_items = Media.search(
            domain,
            limit=ppg,
            offset=pager['offset'],
            order=order
        )

        # Get website categories
        website_categories = request.env['library.website.category'].search(
            [('active', '=', True)],
            order='sequence, name'
        )

        # Keep query parameters
        keep = QueryURL(
            url,
            search=search,
            sortby=sortby
        )

        values = {
            'media_items': media_items,
            'media_count': media_count,
            'pager': pager,
            'search': search,
            'category': None,
            'media_type': None,
            'borrower_type_filter': 'Phật tử',
            'website_categories': website_categories,
            'page_name': 'library_media',
            'page_title': title or 'Phương tiện - Phật tử',
            'keep': keep,
            'sortby': sortby,
            'sort_options': sort_options,
        }

        return request.render("entro_library_website.library_media_list", values)

    @http.route(['/media/chu-ni', '/media/chu-ni/page/<int:page>'],
                type='http', auth='public', website=True, sitemap=True)
    def media_chu_ni(self, page=1, **kwargs):
        """Phương tiện dành cho Chư Ni"""
        try:
            borrower_type = request.env.ref('entro_library.borrower_type_chu_ni')
        except ValueError:
            return request.redirect('/media')

        return self._render_media_by_borrower_type(
            borrower_type, page,
            title='Phương tiện - Chư Ni',
            **kwargs
        )

    @http.route(['/media/thien-sinh', '/media/thien-sinh/page/<int:page>'],
                type='http', auth='public', website=True, sitemap=True)
    def media_thien_sinh(self, page=1, **kwargs):
        """Phương tiện dành cho Thiền sinh"""
        try:
            borrower_type = request.env.ref('entro_library.borrower_type_thien_sinh')
        except ValueError:
            return request.redirect('/media')

        return self._render_media_by_borrower_type(
            borrower_type, page,
            title='Phương tiện - Thiền sinh',
            **kwargs
        )

    @http.route(['/media/phat-tu', '/media/phat-tu/page/<int:page>'],
                type='http', auth='public', website=True, sitemap=True)
    def media_phat_tu(self, page=1, **kwargs):
        """Phương tiện dành cho Phật tử (không phải Chư Ni hoặc Thiền sinh)"""
        try:
            chu_ni = request.env.ref('entro_library.borrower_type_chu_ni')
            thien_sinh = request.env.ref('entro_library.borrower_type_thien_sinh')
        except ValueError:
            return request.redirect('/media')

        return self._render_media_exclude_types(
            [chu_ni, thien_sinh], page,
            title='Phương tiện - Phật tử',
            **kwargs
        )
