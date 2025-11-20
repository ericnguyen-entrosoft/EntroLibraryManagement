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
    registration_date = fields.Date(string='Ngày ĐKTQ', default=fields.Date.today)

    # Thông tin trách nhiệm
    code = fields.Char(string='Mã', index=True)

    # Tác giả
    author_ids = fields.Many2many(
        'library.author',
        'library_book_author_rel',
        'book_id',
        'author_id',
        string='Tác giả'
    )
    co_author_ids = fields.Many2many(
        'library.author',
        'library_book_coauthor_rel',
        'book_id',
        'author_id',
        string='Đồng tác giả'
    )
    author_name_for_cutter = fields.Char(
        string='Tên tác giả (cho Mã Cutter)',
        help='Nhập tên tác giả để tính Mã Cutter. VD: Nguyen Van A'
    )

    # Thông tin xuất bản
    publication_place = fields.Char(string='Nơi xuất bản')
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
    ddc_number = fields.Char(string='Số DDC', help='Dewey Decimal Classification')
    cutter_number = fields.Char(
        string='Mã Cutter',
        compute='_compute_cutter_number',
        store=True,
        help='Mã Cutter được tính tự động từ tên tác giả'
    )
    category_id = fields.Many2one('library.category', string='Nhóm')

    # Quants (Physical copies)
    quant_ids = fields.One2many('library.book.quant', 'book_id', string='Bản sao vật lý')
    quant_count = fields.Integer(string='Số lượng bản sao', compute='_compute_quant_count', store=True)
    available_quant_count = fields.Integer(
        string='Số lượng có sẵn',
        compute='_compute_quant_count',
        store=True
    )

    # Statistics from quants
    total_times_borrowed = fields.Integer(
        string='Tổng số lần được mượn',
        compute='_compute_book_stats',
        store=True
    )
    total_reservation_count = fields.Integer(
        string='Tổng số người đang đặt trước',
        compute='_compute_book_stats',
        store=True
    )

    # Ghi chú
    note = fields.Text(string='Phụ chú')

    # Images
    book_image_ids = fields.One2many('library.book.image', 'book_id', string='Hình ảnh')

    # Trạng thái
    active = fields.Boolean(string='Hoạt động', default=True)

    @api.depends('quant_ids', 'quant_ids.state')
    def _compute_quant_count(self):
        for book in self:
            book.quant_count = len(book.quant_ids)
            book.available_quant_count = len(book.quant_ids.filtered(
                lambda q: q.state == 'available'
            ))

    @api.depends('quant_ids.times_borrowed', 'quant_ids.current_reservation_count')
    def _compute_book_stats(self):
        for book in self:
            book.total_times_borrowed = sum(book.quant_ids.mapped('times_borrowed'))
            book.total_reservation_count = sum(book.quant_ids.mapped('current_reservation_count'))

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
        without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
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

    @api.depends('author_name_for_cutter', 'language_id')
    def _compute_cutter_number(self):
        for record in self:
            if not record.author_name_for_cutter:
                record.cutter_number = ''
                continue

            author_name = record.author_name_for_cutter.strip()
            words = author_name.split()

            if not words:
                record.cutter_number = ''
                continue

            # Bước 1: Lấy chữ cái đầu của từ đầu tiên (viết hoa)
            first_word = words[0]
            first_letter = first_word[0].upper()

            # Bước 2: Lấy vần đầu từ từ đầu tiên
            first_syllable = self._get_first_syllable(author_name)

            # Tìm mã vần từ character.mapping
            van_code = ''
            if first_syllable and record.language_id:
                # Remove the first consonant to get the rhyme (vần)
                # For example: "nguyen" -> "uyen", "van" -> "an"
                rhyme = re.sub(r'^[bcdfghjklmnpqrstvwxyz]+', '', first_syllable)

                if rhyme:
                    # Search in character.mapping
                    mapping = self.env['character.mapping'].search([
                        ('van', '=', rhyme),
                        ('language_id', '=', record.language_id.id)
                    ], limit=1)

                    if mapping:
                        van_code = mapping.ma_so

            # Bước 3: Lấy chữ cái đầu của từ thứ 2 (nếu có)
            second_letter = ''
            if len(words) > 1:
                second_word = words[1]
                if second_word:
                    second_letter = second_word[0].lower()

            # Tạo mã Cutter
            cutter = first_letter
            if van_code:
                cutter += van_code
            if second_letter:
                cutter += second_letter

            record.cutter_number = cutter

    def action_create_quants(self):
        """Open wizard to create multiple book quants"""
        self.ensure_one()
        return {
            'name': 'Tạo bản sao sách',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.create.quant.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_book_id': self.id,
                'default_quantity': 1,
            }
        }

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for record in self:
            if record.code:
                record.display_name = f"[{record.code}] {record.name}"
            else:
                record.display_name = record.name
