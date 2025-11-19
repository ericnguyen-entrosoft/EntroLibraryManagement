# -*- coding: utf-8 -*-
from odoo import models, fields


class LibraryCategory(models.Model):
    _name = 'library.category'
    _description = 'Danh mục sách'
    _order = 'name'
    _parent_store = True

    name = fields.Char(string='Tên danh mục', required=True, index=True)
    code = fields.Char(string='Mã danh mục', index=True)
    parent_id = fields.Many2one('library.category', string='Danh mục cha', ondelete='restrict')
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('library.category', 'parent_id', string='Danh mục con')
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Hoạt động', default=True)

    book_ids = fields.Many2many(
        'library.book',
        'library_book_category_rel',
        'category_id',
        'book_id',
        string='Sách'
    )
    book_count = fields.Integer(string='Số sách', compute='_compute_book_count')

    def _compute_book_count(self):
        for record in self:
            record.book_count = len(record.book_ids)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã danh mục phải duy nhất!')
    ]
