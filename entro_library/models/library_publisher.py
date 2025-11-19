# -*- coding: utf-8 -*-
from odoo import models, fields


class LibraryPublisher(models.Model):
    _name = 'library.publisher'
    _description = 'Nhà xuất bản'
    _order = 'name'

    name = fields.Char(string='Tên nhà xuất bản', required=True, index=True)
    code = fields.Char(string='Mã NXB', index=True)
    address = fields.Text(string='Địa chỉ')
    phone = fields.Char(string='Điện thoại')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    country = fields.Char(string='Quốc gia')
    note = fields.Text(string='Ghi chú')
    active = fields.Boolean(string='Hoạt động', default=True)

    book_ids = fields.One2many('library.book', 'publisher_id', string='Sách xuất bản')
    book_count = fields.Integer(string='Số sách', compute='_compute_book_count')

    def _compute_book_count(self):
        for record in self:
            record.book_count = len(record.book_ids)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã nhà xuất bản phải duy nhất!')
    ]
