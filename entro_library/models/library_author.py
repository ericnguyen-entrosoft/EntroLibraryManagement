# -*- coding: utf-8 -*-
from odoo import models, fields


class LibraryAuthor(models.Model):
    _name = 'library.author'
    _description = 'Tác giả'
    _order = 'name'

    name = fields.Char(string='Tên tác giả', required=True, index=True)
    code = fields.Char(string='Mã tác giả', index=True)
    birth_year = fields.Integer(string='Năm sinh')
    death_year = fields.Integer(string='Năm mất')
    nationality = fields.Char(string='Quốc tịch')
    biography = fields.Text(string='Tiểu sử')
    note = fields.Text(string='Ghi chú')
    active = fields.Boolean(string='Hoạt động', default=True)

    book_ids = fields.Many2many(
        'library.book',
        'library_book_author_rel',
        'author_id',
        'book_id',
        string='Sách chính'
    )
    co_book_ids = fields.Many2many(
        'library.book',
        'library_book_coauthor_rel',
        'author_id',
        'book_id',
        string='Sách đồng tác giả'
    )
    book_count = fields.Integer(string='Số sách', compute='_compute_book_count')

    def _compute_book_count(self):
        for record in self:
            record.book_count = len(record.book_ids) + len(record.co_book_ids)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã tác giả phải duy nhất!')
    ]
