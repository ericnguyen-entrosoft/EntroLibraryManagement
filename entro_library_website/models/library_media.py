# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryMedia(models.Model):
    _inherit = ['library.media', 'website.seo.metadata',
                'website.published.mixin']
    _name = 'library.media'

    # Website Publishing
    website_published = fields.Boolean(
        'Xuất bản trên Website', default=False, copy=False)
    website_url = fields.Char(
        'URL Website', compute='_compute_website_url', store=False)
    website_sequence = fields.Integer('Thứ tự trên Website', default=10)

    # Website Category
    website_category_id = fields.Many2one(
        'library.website.category',
        string='Danh mục Website',
        help='Danh mục hiển thị trên website',
        tracking=True
    )

    # Access control by borrower type
    allowed_borrower_type_ids = fields.Many2many(
        'library.borrower.type',
        'library_media_borrower_type_website_rel',
        'media_id',
        'borrower_type_id',
        string='Loại độc giả được phép',
        help='Chỉ những loại độc giả này mới được xem tài liệu trên website. Để trống nếu cho phép tất cả.'
    )

    # Menu Category (Hierarchical)
    menu_category_id = fields.Many2one(
        'library.menu.category',
        string='Danh mục Menu',
        help='Danh mục trong menu website (hỗ trợ cấu trúc phân cấp)',
        tracking=True,
        index=True
    )

    @api.depends('name')
    def _compute_website_url(self):
        for media in self:
            if media.id:
                media.website_url = f'/media/{media.id}'
            else:
                media.website_url = False

    def _prepare_meta_tags(self):
        """Prepare meta tags for SEO"""
        self.ensure_one()
        return {
            'default_opengraph': {
                'og:title': self.name,
                'og:description': self.description or '',
                'og:type': 'article',
                'og:image': f'/web/image/library.media/{self.id}/thumbnail' if self.thumbnail else '',
            },
            'default_twitter': {
                'twitter:card': 'summary_large_image',
                'twitter:title': self.name,
                'twitter:description': self.description or '',
                'twitter:image': f'/web/image/library.media/{self.id}/thumbnail' if self.thumbnail else '',
            }
        }

    def action_publish(self):
        """Publish media on website"""
        self.website_published = True

    def action_unpublish(self):
        """Unpublish media from website"""
        self.website_published = False
