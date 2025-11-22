# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryQuantType(models.Model):
    _name = 'library.quant.type'
    _description = 'Loại bản sao sách'
    _order = 'sequence, name'

    name = fields.Char(
        string='Tên loại',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='Mã',
        required=True,
        index=True,
        help='Mã định danh cho loại bản sao'
    )
    color = fields.Char(
        string='Màu',
        required=True,
        default='#3498db',
        help='Màu hiển thị cho loại bản sao (mã hex)'
    )
    can_borrow = fields.Boolean(
        string='Có thể mượn',
        default=True,
        help='Cho phép mượn bản sao loại này về nhà'
    )
    sequence = fields.Integer(
        string='Thứ tự',
        default=10
    )
    active = fields.Boolean(
        string='Hoạt động',
        default=True
    )
    description = fields.Text(
        string='Mô tả'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Mã loại phải là duy nhất!')
    ]
