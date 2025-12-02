# -*- coding: utf-8 -*-
from odoo import models, fields


class LibraryMedia(models.Model):
    _inherit = 'library.media'

    # Access control by borrower type
    allowed_borrower_type_ids = fields.Many2many(
        'library.borrower.type',
        'library_media_borrower_type_website_rel',
        'media_id',
        'borrower_type_id',
        string='Loại độc giả được phép',
        help='Chỉ những loại độc giả này mới được xem phương tiện trên website. Để trống nếu cho phép tất cả.'
    )
