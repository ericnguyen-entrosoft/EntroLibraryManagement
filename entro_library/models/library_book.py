# -*- coding: utf-8 -*-
from odoo import models, fields, api
import re
import unicodedata


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Quản lý sách'
    _inherit = ['image.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'registration_date desc, name'

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
        required=True
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
    publication_year = fields.Integer(string='Năm')

    # Thông tin vật lý
    language_id = fields.Many2one('res.lang', string='Ngôn ngữ')
    page_count = fields.Integer(string='Số trang')
    length = fields.Char(string='Độ dài')
    reprint_count = fields.Integer(string='Số lần tái bản', default=0)

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
        'library.category', string='Nhóm', required=True)

    # Resource assignment (computed from quants' locations)
    resource_ids = fields.Many2many(
        'library.resource',
        string='Kho tài nguyên',
        compute='_compute_resource_ids',
        store=True
    )

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

        # Get quants count by state and registration_number for available/borrowed
        quants_data = self.env['library.book.quant']._read_group(
            [('book_id', 'in', self.ids)],
            ['book_id', 'state', 'registration_number'],
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

        for book, state, registration_number, count in quants_data:
            book_id = book.id
            if book_id not in available_counts:
                available_counts[book_id] = 0
                borrowed_counts[book_id] = 0

            # Only count as available if has registration_number and state is available
            if state == 'available' and registration_number:
                available_counts[book_id] += count
            elif state == 'borrowed':
                borrowed_counts[book_id] += count

        reservation_counts = {
            book.id: count for book, count in reservations_data}

        # Update all books
        for book in self:
            book.quant_count = quant_counts.get(book.id, 0)
            book.available_quant_count = available_counts.get(book.id, 0)
            book.borrowed_quant_count = borrowed_counts.get(book.id, 0)
            book.total_reservation_count = reservation_counts.get(book.id, 0)

    @api.depends('quant_ids', 'quant_ids.location_id', 'quant_ids.location_id.is_borrow_location', 'quant_ids.can_borrow')
    def _compute_borrow_locations(self):
        """Compute locations where this book can be borrowed from"""
        for book in self:
            # Get all quants that can be borrowed
            borrowable_quants = book.quant_ids.filtered(lambda q: q.can_borrow and q.location_id.is_borrow_location)
            # Get unique locations
            book.borrow_location_ids = borrowable_quants.mapped('location_id')

    @api.depends('quant_ids', 'quant_ids.location_id', 'quant_ids.location_id.resource_id')
    def _compute_resource_ids(self):
        """Compute resources based on quants' locations"""
        for book in self:
            # Get unique resources from all quants' locations
            resources = book.quant_ids.mapped('location_id.resource_id')
            book.resource_ids = resources

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

    @api.depends('name', 'language_id')
    def _compute_cutter_number(self):
        for record in self:
            if not record.name:
                record.cutter_number = ''
                continue

            book_name = record.name.strip()
            words = book_name.split()

            if not words:
                record.cutter_number = ''
                continue

            # Bước 1: Lấy chữ cái đầu của từ đầu tiên (viết hoa)
            first_word = words[0]
            first_letter = first_word[0].upper()

            # Bước 2: Lấy vần đầu từ từ đầu tiên
            # Ví dụ: "Rộng" -> remove accents -> "rong" -> remove first consonant(s) -> "ong"
            # But we need the full syllable with accent for mapping lookup
            # So we keep the original first word and extract vần (everything after first consonant cluster)
            first_word_normalized = self._remove_accents(first_word).lower()

            # Extract vần (rhyme) by removing initial consonant cluster
            # For "rộng" -> normalized "rong" -> extract "ong"
            # But we need the accented version for mapping
            # So we find where the vần starts in normalized, then take from original
            consonant_match = re.match(
                r'^[bcdfghjklmnpqrstvwxyz]+', first_word_normalized)
            consonant_len = len(consonant_match.group(0)
                                ) if consonant_match else 0

            # Get the vần (with accents) from original word
            van = first_word[consonant_len:].lower() if consonant_len < len(
                first_word) else first_word.lower()

            # Tìm mã vần từ character.mapping
            van_code = ''
            if van and record.language_id:
                # Search in character.mapping with the accented vần
                mapping = self.env['character.mapping'].search([
                    ('van', '=', van),
                    ('language_id', '=', record.language_id.id)
                ], limit=1)

                if mapping:
                    van_code = mapping.ma_so

            # Bước 3: Lấy chữ cái đầu của từ thứ 2 (viết hoa)
            second_letter = ''
            if len(words) > 1:
                second_word = words[1]
                if second_word:
                    second_letter = second_word[0].upper()

            # Tạo mã Cutter: Chữ cái đầu + mã vần + chữ cái đầu từ 2
            # Ví dụ: "Rộng mở cửa trái tim" -> R + 100 + M = R100M
            cutter = first_letter
            if van_code:
                cutter += van_code
            if second_letter:
                cutter += second_letter

            record.cutter_number = cutter

    @api.depends('media_ids')
    def _compute_media_count(self):
        for book in self:
            book.media_count = len(book.media_ids)

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
