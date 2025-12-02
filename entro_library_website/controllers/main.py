# -*- coding: utf-8 -*-
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
        website_categories = request.env['library.website.category'].search([('active', '=', True)], order='sequence, name')

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
