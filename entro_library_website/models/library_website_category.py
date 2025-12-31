# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryWebsiteCategory(models.Model):
    _name = 'library.website.category'
    _description = 'Danh mục Website'
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh mục', required=True, translate=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    description = fields.Text(string='Mô tả')
    color = fields.Integer(string='Màu')
    category_type = fields.Selection([
        ('book', 'Dành cho tài liệu sách'),
        ('media', 'Dành cho tài liệu số'),
        ('both', 'Cả hai')
    ], string='Category Type', required=True, default='both',
       help='Specify whether this category is for Books, Media, or Both')

    # Relationships
    book_ids = fields.One2many('library.book', 'website_category_id', string='Sách')
    book_count = fields.Integer(
        string='Số lượng sách',
        compute='_compute_book_count',
        store=True
    )
    media_ids = fields.One2many('library.media', 'website_category_id', string='Media')
    media_count = fields.Integer(
        string='Số lượng phương tiện',
        compute='_compute_media_count',
        store=True
    )

    # Status
    active = fields.Boolean(string='Hoạt động', default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tên danh mục phải là duy nhất!'),
    ]

    @api.depends('book_ids')
    def _compute_book_count(self):
        for category in self:
            category.book_count = len(category.book_ids)

    @api.depends('media_ids')
    def _compute_media_count(self):
        for category in self:
            category.media_count = len(category.media_ids)

    def action_view_books(self):
        """Xem sách trong danh mục này"""
        self.ensure_one()
        return {
            'name': f'Sách - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'kanban,list,form',
            'domain': [('website_category_id', '=', self.id)],
            'context': {'default_website_category_id': self.id}
        }
