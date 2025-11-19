# -*- coding: utf-8 -*-
from odoo import models, fields


class LibrarySeries(models.Model):
    _name = 'library.series'
    _description = 'Tùng thư'
    _order = 'name'

    name = fields.Char(string='Tên tùng thư', required=True, index=True)
    code = fields.Char(string='Mã tùng thư', index=True)
    description = fields.Text(string='Mô tả')
    publisher_id = fields.Many2one('library.publisher', string='Nhà xuất bản')
    note = fields.Text(string='Ghi chú')
    active = fields.Boolean(string='Hoạt động', default=True)

    book_ids = fields.One2many('library.book', 'series_id', string='Sách trong tùng thư')
    book_count = fields.Integer(string='Số sách', compute='_compute_book_count')

    def _compute_book_count(self):
        for record in self:
            record.book_count = len(record.book_ids)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã tùng thư phải duy nhất!')
    ]
