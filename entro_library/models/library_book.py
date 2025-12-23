# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import timedelta
import re
import unicodedata
from ..utils.cutter_generator import CutterGenerator
class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Quản lý sách'
    _inherit = ['image.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'registration_date desc, name'
    _rec_names_search = ['name', 'author_ids', 'keywords', 'parallel_title']

    name = fields.Char(string='Tác phẩm (Nhan đề)', required=True, index=True)
    registration_date = fields.Date(
        string='Ngày ĐKTQ', default=fields.Date.today, required=True)

    # Thông tin trách nhiệm

    # Tác giả
    author_ids = fields.Many2many(
        'library.author',
        'library_book_author_rel',
        'book_id',
        'author_id',
        string='Tác giả',
        required=False
    )
    author_names = fields.Char(
        string='Tên tác giả',
        compute='_compute_author_names',
        store=True,
        help='Tên tác giả được nối bởi dấu phẩy'
    )
    co_author_ids = fields.Many2many(
        'library.author',
        'library_book_coauthor_rel',
        'book_id',
        'author_id',
        string='Đồng tác giả'
    )

    # Thông tin xuất bản
    publication_country_id = fields.Many2one(
        'res.country', string='Quốc gia xuất bản')
    publication_city_id = fields.Many2one(
        'res.country.state', string='Thành phố xuất bản')
    publisher_id = fields.Many2one('library.publisher', string='Nhà xuất bản')
    publication_year = fields.Char(string='Năm')

    # Thông tin vật lý
    language_id = fields.Many2one('res.lang', string='Ngôn ngữ')
    page_count = fields.Integer(string='Số trang')
    length = fields.Char(string='Độ dài')
    reprint_count = fields.Char(string='Số lần tái bản')

    # Thông tin nhan đề
    subtitle = fields.Char(string='Phụ đề')
    parallel_title = fields.Char(string='Nhan đề song song')
    volume_title = fields.Char(string='Nhan đề tập')

    # Thông tin nội dung
    summary = fields.Html(string='Tóm tắt nội dung')
    keywords = fields.Char(string='Từ khóa')

    # Phân loại
    series_id = fields.Many2one('library.series', string='Tùng thư')
    ddc_number = fields.Char(
        string='Số DDC', help='Dewey Decimal Classification')
    cutter_number = fields.Char(
        string='Mã Cutter',
        compute='_compute_cutter_number',
        store=True,
        help='Mã Cutter được tính tự động từ tên tác giả'
    )
    category_id = fields.Many2one(
        'library.category', string='Nhóm', required=False)

    # Media relationship
    media_ids = fields.Many2many(
        'library.media',
        'library_media_book_rel',
        'book_id',
        'media_id',
        string='Phương tiện'
    )
    media_count = fields.Integer(
        string='Số phương tiện',
        compute='_compute_media_count',
        store=True
    )

    # Quants (Physical copies)
    quant_ids = fields.One2many(
        'library.book.quant', 'book_id', string='Bản sao vật lý')
    quant_count = fields.Integer(
        string='Số lượng',
        compute='_compute_quantities',
        compute_sudo=False,
        help='Tổng số bản sao vật lý của sách này'
    )
    available_quant_count = fields.Integer(
        string='Có sẵn',
        compute='_compute_quantities',
        compute_sudo=False,
        help='Số lượng bản sao đã có số ĐKCB và có sẵn để mượn'
    )
    borrowed_quant_count = fields.Integer(
        string='Đang mượn',
        compute='_compute_quantities',
        compute_sudo=False,
        help='Số lượng bản sao đang được mượn'
    )
    total_reservation_count = fields.Integer(
        string='Đặt trước',
        compute='_compute_quantities',
        compute_sudo=False,
        help='Tổng số người đang đặt trước sách này'
    )
    can_borrow_quant_count = fields.Integer(
        string='Có thể mượn',
        compute='_compute_quantities',
        compute_sudo=False,
        help='Số lượng bản sao có thể mượn về'
    )
    no_borrow_quant_count = fields.Integer(
        string='Đọc tại chỗ',
        compute='_compute_quantities',
        compute_sudo=False,
        help='Số lượng bản sao chỉ đọc tại chỗ, không cho mượn về'
    )

    # Borrow locations
    borrow_location_ids = fields.Many2many(
        'library.location',
        string='Khu vực',
        compute='_compute_borrow_locations',
        help='Các vị trí có sách này có thể mượn về'
    )

    # Ghi chú
    note = fields.Text(string='Phụ chú')

    # Images
    book_image_ids = fields.One2many(
        'library.book.image', 'book_id', string='Hình ảnh')

    # Soft copy
    soft_copy = fields.Binary(string='Bản mềm', attachment=True)
    soft_copy_filename = fields.Char(string='Tên file bản mềm')
    media_link = fields.Char(string='URL')

    # Trạng thái
    active = fields.Boolean(string='Hoạt động', default=True)
    can_borrow = fields.Boolean(string='Có thể mượn', default=True, help='Cho phép mượn sách này về nhà')
    is_published = fields.Boolean(
        string='Hiển thị trên Website',
        default=False,
        copy=False,
        help='Hiển thị sách này trên trang web công khai'
    )
    website_url = fields.Char(
        string='Website URL',
        compute='_compute_website_url',
        help='URL truy cập sách trên website'
    )

    def _compute_quantities(self):
        """
        Compute quantities using _read_group for better performance.
        Similar to Odoo's stock.quant approach for product.product
        """
        # Get total quantity (sum of all quant quantities) grouped by book_id
        quants_sum_data = self.env['library.book.quant']._read_group(
            [('book_id', 'in', self.ids)],
            ['book_id'],
            ['quantity:sum']
        )

        # Get quants count by state, registration_number, and can_borrow for available/borrowed/borrowable
        quants_data = self.env['library.book.quant']._read_group(
            [('book_id', 'in', self.ids)],
            ['book_id', 'state', 'registration_number', 'can_borrow'],
            ['__count']
        )

        # Get reservation counts grouped by book_id
        reservations_data = self.env['library.reservation']._read_group(
            [
                ('book_id', 'in', self.ids),
                ('state', 'in', ['active', 'available'])
            ],
            ['book_id'],
            ['__count']
        )

        # Build dictionaries for quick lookup
        quant_counts = {book.id: quantity_sum for book,
                        quantity_sum in quants_sum_data}
        available_counts = {}
        borrowed_counts = {}
        can_borrow_counts = {}
        no_borrow_counts = {}

        for book, state, registration_number, can_borrow, count in quants_data:
            book_id = book.id
            if book_id not in available_counts:
                available_counts[book_id] = 0
                borrowed_counts[book_id] = 0
                can_borrow_counts[book_id] = 0
                no_borrow_counts[book_id] = 0

            # Only count as available if has registration_number and state is available
            if state == 'available' and registration_number:
                available_counts[book_id] += count
            elif state == 'borrowed':
                borrowed_counts[book_id] += count

            # Count borrowable vs non-borrowable quants (regardless of state)
            if can_borrow:
                can_borrow_counts[book_id] += count
            else:
                no_borrow_counts[book_id] += count

        reservation_counts = {
            book.id: count for book, count in reservations_data}

        # Update all books
        for book in self:
            book.quant_count = quant_counts.get(book.id, 0)
            book.available_quant_count = available_counts.get(book.id, 0)
            book.borrowed_quant_count = borrowed_counts.get(book.id, 0)
            book.total_reservation_count = reservation_counts.get(book.id, 0)
            book.can_borrow_quant_count = can_borrow_counts.get(book.id, 0)
            book.no_borrow_quant_count = no_borrow_counts.get(book.id, 0)

    @api.depends('quant_ids', 'quant_ids.location_id', 'quant_ids.location_id.is_borrow_location', 'quant_ids.can_borrow')
    def _compute_borrow_locations(self):
        """Compute locations where this book can be borrowed from"""
        for book in self:
            # Get all quants that can be borrowed
            borrowable_quants = book.quant_ids.filtered(lambda q: q.can_borrow and q.location_id.is_borrow_location)
            # Get unique locations
            book.borrow_location_ids = borrowable_quants.mapped('location_id')

    def action_view_quants(self):
        """View book's physical copies (quants)"""
        self.ensure_one()
        return {
            'name': 'Bản sao vật lý',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.quant',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id}
        }

    def action_view_borrowings(self):
        """View all borrowing history for this book's quants"""
        self.ensure_one()
        return {
            'name': 'Lịch sử mượn',
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing.line',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id}
        }

    def action_view_reservations(self):
        """View all reservations for this book's quants"""
        self.ensure_one()
        return {
            'name': 'Đặt trước',
            'type': 'ir.actions.act_window',
            'res_model': 'library.reservation',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id}
        }

    def _remove_accents(self, text):
        """Remove Vietnamese accents from text"""
        if not text:
            return ''
        # Normalize unicode characters
        nfd = unicodedata.normalize('NFD', text)
        # Remove combining characters (accents)
        without_accents = ''.join(
            char for char in nfd if unicodedata.category(char) != 'Mn')
        # Replace Đ/đ specifically
        without_accents = without_accents.replace('Đ', 'D').replace('đ', 'd')
        return without_accents

    def _get_first_syllable(self, text):
        """Get first syllable from Vietnamese text"""
        if not text:
            return ''
        text = text.strip()
        # Split by space to get first word
        words = text.split()
        if not words:
            return ''
        first_word = words[0]
        # Remove accents for processing
        normalized = self._remove_accents(first_word).lower()
        return normalized

    @api.depends('name')
    def _compute_cutter_number(self):
        for record in self:
            if not record.name:
                record.cutter_number = ''
                continue
            generator = CutterGenerator()
            record.cutter_number = generator.generate_cutter_code(record.name)

    @api.depends('author_ids.name')
    def _compute_author_names(self):
        for book in self:
            if book.author_ids:
                book.author_names = ', '.join(book.author_ids.mapped('name'))
            else:
                book.author_names = ''

    @api.depends('media_ids')
    def _compute_media_count(self):
        for book in self:
            book.media_count = len(book.media_ids)

    def _compute_website_url(self):
        """Compute the website URL for this book"""
        for book in self:
            if book.id:
                book.website_url = f"/library/book/{book.id}"
            else:
                book.website_url = False

    def action_view_media(self):
        """View media related to this book"""
        self.ensure_one()
        return {
            'name': f'Phương tiện - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.media',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.media_ids.ids)],
            'context': {'default_book_ids': [(4, self.id)]}
        }

    def action_update_quantity(self):
        """Open wizard to create multiple book quants"""
        self.ensure_one()
        return {
            'name': 'Thêm số lượng',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.update.quantity',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_book_id': self.id,
                'default_quantity': 1,
            }
        }

    def action_toggle_website_published(self):
        """Toggle website publication status"""
        for book in self:
            book.is_published = not book.is_published
        return True

    def action_add_to_borrowing(self):
        """
        Add ONE copy of this book to borrower's draft borrowing (like adding to cart)
        Uses two-layer structure: creates book line with 1 quantity, adds 1 quant line
        If user wants more copies, they click "Add to Cart" multiple times
        """
        self.ensure_one()

        # Get current user's partner
        borrower = self.env.user.partner_id

        # Get or create draft borrowing (this also validates membership)
        borrowing = borrower.get_or_create_draft_borrowing()

        # Check if book has available copies
        available_count = self.env['library.book.quant'].search_count([
            ('book_id', '=', self.id),
            ('state', '=', 'available'),
            ('can_borrow', '=', True),
            ('registration_number', '!=', False),
            ('location_id.is_borrow_location', '=', True),
        ])

        if available_count == 0:
            raise exceptions.UserError(
                f'Sách "{self.name}" hiện không có bản sao nào khả dụng để mượn.'
            )

        # Calculate due date based on default borrowing days
        config = self.env['ir.config_parameter'].sudo()
        default_days = int(config.get_param('library.default_borrowing_days', default=14))

        due_date = borrowing.borrow_date + timedelta(days=default_days)

        # Find existing book line for this book
        book_line = borrowing.borrowing_line_ids.filtered(
            lambda l: l.book_id.id == self.id
        )

        if book_line:
            # Book already exists in cart - don't allow adding again
            raise exceptions.UserError(
                f'Sách "{self.name}" đã có trong giỏ mượn của bạn. Mỗi sách chỉ được mượn 1 bản mỗi lần.'
            )

        # Create new book line with quantity=1 (NO quant assignment yet)
        book_line = self.env['library.borrowing.line'].create({
            'borrowing_id': borrowing.id,
            'book_id': self.id,
            'requested_quantity': 1,
            'due_date': due_date,
        })

        # NOTE: Quant assignment will be done later (at checkout or by staff)
        # No quant_line is created here

        # Return action to open borrowing form
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công!',
                'message': 'Đã thêm sách vào phiếu mượn.',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'library.borrowing',
                    'res_id': borrowing.id,
                    'view_mode': 'form',
                    'views': [[False, 'form']],
                    'target': 'current',
                }
            }
        }
