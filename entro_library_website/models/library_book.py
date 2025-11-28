# -*- coding: utf-8 -*-
from odoo import models, fields, api
import re
import unicodedata


class LibraryBook(models.Model):
    _inherit = 'library.book'

    # Website visibility
    website_published = fields.Boolean(
        string='Xuất bản lên Website',
        default=False,
        help='Hiển thị sách này trên trang web công khai'
    )
    is_published = fields.Boolean(
        string='Đã xuất bản',
        compute='_compute_is_published',
        store=False
    )
    website_url = fields.Char(
        string='URL Website',
        compute='_compute_website_url',
        help='URL slug cho SEO-friendly'
    )

    # SEO fields
    website_meta_title = fields.Char(
        string='Tiêu đề Meta',
        help='Tiêu đề hiển thị trên kết quả tìm kiếm Google'
    )
    website_meta_description = fields.Text(
        string='Mô tả Meta',
        help='Mô tả ngắn cho SEO (160 ký tự)'
    )
    website_meta_keywords = fields.Char(
        string='Từ khóa Meta',
        help='Từ khóa cho SEO, phân cách bằng dấu phẩy'
    )

    # Display options
    website_sequence = fields.Integer(
        string='Thứ tự hiển thị',
        default=1,
        help='Thứ tự sắp xếp trên website'
    )

    @api.depends('website_published', 'active')
    def _compute_is_published(self):
        """Compute if book is published and active"""
        for book in self:
            book.is_published = book.website_published and book.active

    def _get_vietnamese_slug(self, text):
        """Convert Vietnamese text to URL-friendly slug"""
        if not text:
            return ''

        # Lowercase
        text = text.lower()

        # Vietnamese character mapping
        vietnamese_map = {
            'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
            'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
            'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
            'đ': 'd',
            'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
            'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
            'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
            'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
            'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
            'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
            'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
            'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
            'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        }

        for viet_char, latin_char in vietnamese_map.items():
            text = text.replace(viet_char, latin_char)

        # Remove special characters
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        # Replace spaces with hyphens
        text = re.sub(r'[\s]+', '-', text)
        # Remove multiple hyphens
        text = re.sub(r'-+', '-', text)

        return text.strip('-')

    @api.depends('name')
    def _compute_website_url(self):
        """Compute SEO-friendly URL"""
        for book in self:
            if book.name:
                slug = self._get_vietnamese_slug(book.name)
                book.website_url = f'/thu-vien/sach/{slug}-{book.id}'
            else:
                book.website_url = ''

    def _prepare_meta_tags(self):
        """Prepare meta tags for SEO"""
        self.ensure_one()
        return {
            'meta_title': self.website_meta_title or f'{self.name} - {self.author_names} | Thư Viện',
            'meta_description': self.website_meta_description or (self.summary[:160] if self.summary else f'Mượn sách {self.name} của {self.author_names} tại thư viện'),
            'meta_keywords': self.website_meta_keywords or f'{self.name}, {self.author_names}, {self.category_id.name if self.category_id else ""}',
        }

    def action_toggle_website_published(self):
        """Toggle website published status"""
        for book in self:
            book.website_published = not book.website_published
