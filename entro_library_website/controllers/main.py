# -*- coding: utf-8 -*-
import base64
from odoo import http, _, exceptions, fields
from odoo.http import request
from odoo.addons.website.controllers.main import QueryURL
from werkzeug.exceptions import NotFound
from odoo.addons.portal.controllers.web import Home

class Website(Home):

    def _login_redirect(self, uid, redirect=None):
        if not redirect and request.params.get('login_success'):
            if request.env['res.users'].browse(uid)._is_internal():
                redirect = '/odoo?' + request.httprequest.query_string.decode()
            else:
                redirect = '/'
        return super()._login_redirect(uid, redirect=redirect)

class LibraryWebsite(http.Controller):

    @http.route(['/'], type='http', auth='public', website=True, sitemap=True)
    def library_home(self, **kwargs):
        """Trang chủ thư viện"""

        # Get hero slides
        hero_slides = request.env['library.website.slider'].search([
            ('active', '=', True),
            ('is_published', '=', True)
        ], order='sequence, id')

        # Get popular books (most borrowed)
        # Use SQL to get books with borrow count
        request.env.cr.execute("""
            SELECT b.id, COUNT(bl.id) as borrow_count
            FROM library_book b
            LEFT JOIN library_borrowing_line bl ON bl.book_id = b.id
            WHERE b.website_published = true AND b.active = true
            GROUP BY b.id
            HAVING COUNT(bl.id) > 0
            ORDER BY borrow_count DESC
            LIMIT 10
        """)
        popular_books_data = request.env.cr.fetchall()
        popular_book_ids = [row[0] for row in popular_books_data]
        popular_books = request.env['library.book'].browse(popular_book_ids)

        # Get popular media (most viewed)
        popular_media = request.env['library.media'].search([
            ('website_published', '=', True),
            ('active', '=', True),
        ], limit=10, order='view_count desc')

        # Get recent blog posts
        blog_posts = request.env['blog.post'].search([
            ('website_published', '=', True)
        ], limit=3, order='published_date desc')

        # Get statistics
        total_books = request.env['library.book'].search_count([('active', '=', True)])
        total_media = request.env['library.media'].search_count([('active', '=', True)])
        total_members = request.env['res.partner'].search_count([('borrower_type_id', '!=', False)])

        # Get visitor count from Google Analytics (cached value)
        visitor_count = 0
        try:
            # Get cached value from system parameter (updated by scheduled action)
            visitor_count = int(request.env['ir.config_parameter'].sudo().get_param(
                'library.visitor_count', default=0
            ))
        except (ValueError, TypeError):
            visitor_count = 0

        values = {
            'hero_slides': hero_slides,
            'popular_books': popular_books,
            'popular_media': popular_media,
            'blog_posts': blog_posts,
            'total_books': total_books,
            'total_media': total_media,
            'total_members': total_members,
            'visitor_count': visitor_count,
            'page_name': 'library_home',
        }

        return request.render("entro_library_website.library_home", values)

    @http.route([
        '/thu-vien',
        '/thu-vien/page/<int:page>',
        '/thu-vien/<string:parent_slug>',
        '/thu-vien/<string:parent_slug>/page/<int:page>',
        '/thu-vien/<string:parent_slug>/<string:child_slug>',
        '/thu-vien/<string:parent_slug>/<string:child_slug>/page/<int:page>',
        # Legacy routes
        '/thu-vien/danh-muc/<model("library.website.category"):category>',
        '/thu-vien/danh-muc/<model("library.website.category"):category>/page/<int:page>',
    ], type='http', auth='public', website=True, sitemap=True)
    def library_books(self, page=1, category=None, parent_slug=None, child_slug=None, search='', sortby=None, category_id=None, **kwargs):
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

        # ========================================
        # Filter by library.book.category (hierarchical - for slug-based URLs)
        # ========================================
        book_category_id_list = []
        selected_book_category = None

        # Priority 1: Slug-based URL (SEO-friendly)
        if child_slug:
            # Child category slug (e.g., /thu-vien/phat-hoc/subcategory)
            selected_book_category = request.env['library.book.category'].sudo().search([
                ('slug', '=', child_slug),
                ('parent_id.slug', '=', parent_slug)
            ], limit=1)
            if selected_book_category:
                book_category_id_list = [selected_book_category.id]
        elif parent_slug:
            # Parent category slug (e.g., /thu-vien/phat-hoc)
            selected_book_category = request.env['library.book.category'].sudo().search([
                ('slug', '=', parent_slug),
                ('parent_id', '=', False)
            ], limit=1)
            if selected_book_category:
                book_category_id_list = [selected_book_category.id]

        # Apply library.book.category filter (including child categories)
        if book_category_id_list:
            # Get all child categories recursively
            all_book_category_ids = list(book_category_id_list)
            book_categories = request.env['library.book.category'].sudo().browse(book_category_id_list)
            for cat in book_categories:
                if cat.child_ids:
                    all_book_category_ids += cat.child_ids.ids
                    # Recursive for nested children
                    for child in cat.child_ids:
                        all_book_category_ids += child.child_ids.ids
            domain += [('book_category_id', 'in', all_book_category_ids)]

            # Apply access control based on category access_level
            for cat in book_categories:
                if cat.access_level == 'members' and request.env.user._is_public():
                    # Redirect to login if trying to access members-only content
                    return request.redirect('/web/login?redirect=/thu-vien/' + parent_slug)
                elif cat.access_level == 'restricted':
                    # Check if user has permission
                    if not request.env.user.has_group('entro_library.group_library_manager'):
                        raise exceptions.AccessError(_('Bạn không có quyền truy cập vào danh mục này.'))

        # ========================================
        # Filter by library.website.category (for sidebar filter checkboxes)
        # ========================================
        website_category_id_list = []
        category_ids_from_request = request.httprequest.args.getlist('category_id')

        if category_ids_from_request:
            website_category_id_list = [int(cid) for cid in category_ids_from_request if cid]
            domain += [('website_category_id', 'in', website_category_id_list)]
        elif category_id:
            # Fallback to single category_id parameter
            if isinstance(category_id, list):
                website_category_id_list = [int(cid) for cid in category_id]
            else:
                website_category_id_list = [int(category_id)]
            if website_category_id_list:
                domain += [('website_category_id', 'in', website_category_id_list)]
        elif category:
            # Support old single category URL format
            domain += [('website_category_id', '=', category.id)]
            website_category_id_list = [category.id]

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
        ppg = 20  # books per page

        # Construct base URL - preserve slug-based URLs
        if child_slug and parent_slug:
            # Child category slug URL (e.g., /thu-vien/phat-hoc/subcategory)
            url = f'/thu-vien/{parent_slug}/{child_slug}'
        elif parent_slug:
            # Parent category slug URL (e.g., /thu-vien/phat-hoc)
            url = f'/thu-vien/{parent_slug}'
        elif category:
            # Legacy category URL
            url = f'/thu-vien/danh-muc/{category.id}'
        else:
            # Default URL
            url = '/thu-vien'

        url_args = {'search': search, 'sortby': sortby}
        if website_category_id_list:
            url_args['category_id'] = website_category_id_list

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

        # Load library.website.category for sidebar filters
        # Only show website categories that have books in the current book.category context
        website_category_domain = [
            ('active', '=', True),
            ('category_type', 'in', ['book', 'both'])
        ]

        # If a book.category is selected (via slug), filter website_categories
        # to only show those that have books in this book.category
        if book_category_id_list:
            # Get all child categories recursively
            all_book_category_ids = list(book_category_id_list)
            book_categories = request.env['library.book.category'].sudo().browse(book_category_id_list)
            for cat in book_categories:
                if cat.child_ids:
                    all_book_category_ids += cat.child_ids.ids
                    for child in cat.child_ids:
                        all_book_category_ids += child.child_ids.ids

            # Find all website_category_ids that have books in this book.category
            books_in_category = request.env['library.book'].sudo().search([
                ('book_category_id', 'in', all_book_category_ids),
                ('website_category_id', '!=', False)
            ])
            available_website_category_ids = books_in_category.mapped('website_category_id').ids

            if available_website_category_ids:
                website_category_domain.append(('id', 'in', available_website_category_ids))
            else:
                # No books with website_category in this book.category, show empty list
                website_category_domain.append(('id', '=', False))

        website_categories = request.env['library.website.category'].search(
            website_category_domain,
            order='sequence, name'
        )

        # Keep query parameters
        keep = QueryURL(
            url,
            category=category and category.id,
            search=search,
            category_id=website_category_id_list,
            sortby=sortby
        )

        values = {
            'books': books,
            'books_count': books_count,
            'pager': pager,
            'search': search,
            'category': category,

            # library.book.category variables (hierarchical menu)
            'book_category_id_list': book_category_id_list,
            'selected_book_category': selected_book_category,

            # library.website.category variables (sidebar filters)
            'website_category_id_list': website_category_id_list,
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
        '/thu-vien/media',
        '/thu-vien/media/page/<int:page>',
        '/thu-vien/media/<string:parent_slug>',
        '/thu-vien/media/<string:parent_slug>/page/<int:page>',
        '/thu-vien/media/<string:parent_slug>/<string:child_slug>',
        '/thu-vien/media/<string:parent_slug>/<string:child_slug>/page/<int:page>',
        # Legacy routes
        '/media',
        '/media/<path:menu_path>',
        '/media/page/<int:page>',
        '/media/<path:menu_path>/page/<int:page>',
    ], type='http', auth='public', website=True, sitemap=True)
    def library_media_list(self, page=1, parent_slug=None, child_slug=None, category=None, menu_path=None, search='', media_type=None, category_id=None, sortby=None, **kwargs):
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

        # ========================================
        # Filter by library.media.category (hierarchical - for slug-based URLs)
        # ========================================
        media_category_id_list = []
        selected_media_category = None

        # Priority 1: Slug-based URL (SEO-friendly)
        if child_slug:
            # Child category slug (e.g., /thu-vien/media/thien-vipassana/phap-thoai)
            selected_media_category = request.env['library.media.category'].sudo().search([
                ('slug', '=', child_slug),
                ('parent_id.slug', '=', parent_slug)
            ], limit=1)
            if selected_media_category:
                media_category_id_list = [selected_media_category.id]
        elif parent_slug:
            # Parent category slug (e.g., /thu-vien/media/phat-hoc)
            selected_media_category = request.env['library.media.category'].sudo().search([
                ('slug', '=', parent_slug),
                ('parent_id', '=', False)
            ], limit=1)
            if selected_media_category:
                media_category_id_list = [selected_media_category.id]

        # Apply library.media.category filter (including child categories)
        if media_category_id_list:
            # Get all child categories recursively
            all_media_category_ids = list(media_category_id_list)
            media_categories = request.env['library.media.category'].sudo().browse(media_category_id_list)
            for cat in media_categories:
                if cat.child_ids:
                    all_media_category_ids += cat.child_ids.ids
                    # Recursive for nested children
                    for child in cat.child_ids:
                        all_media_category_ids += child.child_ids.ids
            domain += [('category_id', 'in', all_media_category_ids)]

            # Apply access control based on category access_level
            for cat in media_categories:
                if cat.access_level == 'members' and request.env.user._is_public():
                    # Redirect to login if trying to access members-only content
                    return request.redirect('/web/login?redirect=/thu-vien/media?category_id=' + str(cat.id))
                elif cat.access_level == 'restricted':
                    # Check if user has permission
                    if not request.env.user.has_group('entro_library.group_library_manager'):
                        raise exceptions.AccessError(_('Bạn không có quyền truy cập vào danh mục này.'))

        # ========================================
        # Filter by library.website.category (for sidebar filter checkboxes)
        # ========================================
        website_category_id_list = []
        category_ids_from_request = request.httprequest.args.getlist('category_id')

        if category_ids_from_request:
            website_category_id_list = [int(cid) for cid in category_ids_from_request if cid]
            domain += [('website_category_id', 'in', website_category_id_list)]
        elif category_id:
            # Fallback to single category_id parameter
            if isinstance(category_id, list):
                website_category_id_list = [int(cid) for cid in category_id]
            else:
                website_category_id_list = [int(category_id)]
            if website_category_id_list:
                domain += [('website_category_id', 'in', website_category_id_list)]
        elif category:
            # Support old single category URL format
            domain += [('website_category_id', '=', category.id)]
            website_category_id_list = [category.id]

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

        # Construct base URL - preserve slug-based URLs
        if child_slug and parent_slug:
            # Child category slug URL (e.g., /thu-vien/media/thien-vipassana/phap-thoai)
            url = f'/thu-vien/media/{parent_slug}/{child_slug}'
        elif parent_slug:
            # Parent category slug URL (e.g., /thu-vien/media/thien-vipassana)
            url = f'/thu-vien/media/{parent_slug}'
        elif menu_path:
            # Legacy menu path URL (e.g., /media/thien-vipassana)
            url = f'/media/{menu_path}'
        elif category:
            # Legacy category URL
            url = f'/media/danh-muc/{category.id}'
        else:
            # Default URL
            url = '/thu-vien/media'

        url_args = {'search': search, 'sortby': sortby}
        if website_category_id_list:
            url_args['category_id'] = website_category_id_list

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

        # Load library.website.category for sidebar filters
        # Only show website categories that have media in the current media.category context
        website_category_domain = [
            ('active', '=', True),
            ('category_type', 'in', ['media', 'both'])
        ]

        # If a media.category is selected (via slug), filter website_categories
        # to only show those that have media in this media.category
        if media_category_id_list:
            # Get all child categories recursively
            all_media_category_ids = list(media_category_id_list)
            media_categories = request.env['library.media.category'].sudo().browse(media_category_id_list)
            for cat in media_categories:
                if cat.child_ids:
                    all_media_category_ids += cat.child_ids.ids
                    for child in cat.child_ids:
                        all_media_category_ids += child.child_ids.ids

            # Find all website_category_ids that have media in this media.category
            media_in_category = request.env['library.media'].sudo().search([
                ('category_id', 'in', all_media_category_ids),
                ('website_category_id', '!=', False)
            ])
            available_website_category_ids = media_in_category.mapped('website_category_id').ids

            if available_website_category_ids:
                website_category_domain.append(('id', 'in', available_website_category_ids))
            else:
                # No media with website_category in this media.category, show empty list
                website_category_domain.append(('id', '=', False))

        website_categories = request.env['library.website.category'].search(
            website_category_domain,
            order='sequence, name'
        )

        # Keep query parameters
        keep = QueryURL(
            url,
            category=category and category.id,
            search=search,
            category_id=website_category_id_list,
            sortby=sortby
        )

        values = {
            'media_items': media_items,
            'media_count': media_count,
            'pager': pager,
            'search': search,
            'category': category,
            'media_type': media_type,

            # library.media.category variables (hierarchical menu)
            'media_category_id_list': media_category_id_list,
            'selected_media_category': selected_media_category,

            # library.website.category variables (sidebar filters)
            'website_category_id_list': website_category_id_list,
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
            [('active', '=', True), ('category_type', 'in', ['media', 'both'])],
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
            [('active', '=', True), ('category_type', 'in', ['media', 'both'])],
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

    # ====================================
    # UNIFIED CATALOG (BOOKS + MEDIA)
    # ====================================

    @http.route([
        '/kho-tai-nguyen',
        '/kho-tai-nguyen/page/<int:page>',
        '/kho-tai-nguyen/danh-muc/<model("library.website.category"):category>',
        '/kho-tai-nguyen/danh-muc/<model("library.website.category"):category>/page/<int:page>',
    ], type='http', auth='public', website=True, sitemap=True)
    def unified_catalog(self, page=1, category=None, search='', item_type=None, sortby=None, category_id=None, **kwargs):
        """Unified page showing both books and media"""

        # Build domain for books
        book_domain = [('website_published', '=', True)]
        media_domain = [('website_published', '=', True), ('active', '=', True)]

        # Filter by borrower type access control
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            if partner.borrower_type_id:
                book_domain += [
                    '|',
                    ('allowed_borrower_type_ids', '=', False),
                    ('allowed_borrower_type_ids', 'in', partner.borrower_type_id.id)
                ]
                media_domain += [
                    '|',
                    ('allowed_borrower_type_ids', '=', False),
                    ('allowed_borrower_type_ids', 'in', partner.borrower_type_id.id)
                ]

        # Filter by access level for media
        if request.env.user._is_public():
            media_domain += [('access_level', '=', 'public')]
        else:
            media_domain += [('access_level', 'in', ['public', 'members'])]

        # Search
        if search:
            book_domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('author_names', 'ilike', search),
                ('keywords', 'ilike', search),
                ('parallel_title', 'ilike', search),
            ]
            media_domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('author', 'ilike', search),
                ('keywords', 'ilike', search),
                ('description', 'ilike', search),
            ]

        # Filter by category (support multiple categories via checkbox)
        category_id_list = []
        # Get all category_id values from request (supports multiple checkboxes)
        category_ids_from_request = request.httprequest.args.getlist('category_id')

        if category_ids_from_request:
            category_id_list = [int(cid) for cid in category_ids_from_request if cid]
            if category_id_list:
                book_domain += [('website_category_id', 'in', category_id_list)]
                media_domain += [('website_category_id', 'in', category_id_list)]
        elif category_id:
            # Fallback to single category_id parameter
            if isinstance(category_id, list):
                category_id_list = [int(cid) for cid in category_id]
            else:
                category_id_list = [int(category_id)]
            if category_id_list:
                book_domain += [('website_category_id', 'in', category_id_list)]
                media_domain += [('website_category_id', 'in', category_id_list)]
        elif category:
            # Support old single category URL format
            book_domain += [('website_category_id', '=', category.id)]
            media_domain += [('website_category_id', '=', category.id)]
            category_id_list = [category.id]

        # Filter by item type (book or media)
        if item_type == 'book':
            # Only show books
            media_items = request.env['library.media'].browse([])
            media_count = 0
        elif item_type == 'media':
            # Only show media
            books = request.env['library.book'].browse([])
            books_count = 0
        else:
            # Show both - we'll handle this below
            pass

        # Sorting
        sort_options = {
            'date_desc': ('registration_date desc, name', 'create_date desc, name'),
            'date_asc': ('registration_date asc, name', 'create_date asc, name'),
            'name_asc': ('name asc', 'name asc'),
            'name_desc': ('name desc', 'name desc'),
        }
        if not sortby or sortby not in sort_options:
            sortby = 'date_desc'

        book_order, media_order = sort_options[sortby]

        Book = request.env['library.book']
        Media = request.env['library.media']

        # Get counts
        if item_type != 'media':
            books_count = Book.search_count(book_domain)
        else:
            books_count = 0

        if item_type != 'book':
            media_count = Media.search_count(media_domain)
        else:
            media_count = 0

        total_count = books_count + media_count

        # Pagination
        ppg = 24  # items per page

        # Construct base URL
        if category:
            url = f'/kho-tai-nguyen/danh-muc/{category.id}'
        else:
            url = '/kho-tai-nguyen'

        url_args = {'search': search, 'sortby': sortby}
        if item_type:
            url_args['item_type'] = item_type

        pager = request.website.pager(
            url=url,
            url_args=url_args,
            total=total_count,
            page=page,
            step=ppg,
        )

        # Fetch mixed results
        all_items = []

        if item_type != 'media' and books_count > 0:
            books = Book.search(
                book_domain,
                limit=ppg if item_type == 'book' else books_count,
                offset=pager['offset'] if item_type == 'book' else 0,
                order=book_order
            )
            for book in books:
                all_items.append({
                    'type': 'book',
                    'item': book,
                    'date': book.registration_date or fields.Date.today(),
                })

        if item_type != 'book' and media_count > 0:
            media_items = Media.search(
                media_domain,
                limit=ppg if item_type == 'media' else media_count,
                offset=pager['offset'] if item_type == 'media' else 0,
                order=media_order
            )
            for media in media_items:
                all_items.append({
                    'type': 'media',
                    'item': media,
                    'date': media.create_date.date() if media.create_date else fields.Date.today(),
                })

        # Sort mixed items
        if not item_type:
            if sortby in ['date_desc', 'name_desc']:
                all_items.sort(key=lambda x: x['date'] if sortby == 'date_desc' else x['item'].name, reverse=True)
            else:
                all_items.sort(key=lambda x: x['date'] if sortby == 'date_asc' else x['item'].name)

            # Apply pagination to mixed results
            all_items = all_items[pager['offset']:pager['offset'] + ppg]

        # Get website categories (both book and media)
        website_categories = request.env['library.website.category'].search(
            [('active', '=', True)], order='sequence, name')

        # Keep query parameters
        keep = QueryURL(
            url,
            category=category and category.id,
            search=search,
            item_type=item_type,
            category_id=category_id_list,
            sortby=sortby
        )

        values = {
            'all_items': all_items,
            'total_count': total_count,
            'books_count': books_count,
            'media_count': media_count,
            'pager': pager,
            'search': search,
            'category': category,
            'category_id_list': category_id_list,
            'item_type': item_type,
            'website_categories': website_categories,
            'page_name': 'unified_catalog',
            'keep': keep,
            'sortby': sortby,
            'sort_options': {k: v[0] for k, v in sort_options.items()},
        }

        return request.render("entro_library_website.unified_catalog", values)
