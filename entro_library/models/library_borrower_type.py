# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryBorrowerType(models.Model):
    _name = 'library.borrower.type'
    _description = 'Loại độc giả'
    _order = 'sequence, name'

    name = fields.Char(string='Tên loại độc giả', required=True, translate=True)
    code = fields.Char(string='Mã', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)

    # Borrowing limits
    max_books = fields.Integer(
        string='Số sách tối đa',
        default=5,
        required=True,
        help='Số lượng sách tối đa có thể mượn cùng lúc'
    )
    max_days = fields.Integer(
        string='Số ngày mượn tối đa',
        default=30,
        required=True,
        help='Số ngày mượn tối đa cho mỗi lần mượn'
    )

    # Fine configuration
    daily_fine_amount = fields.Float(
        string='Tiền phạt/ngày',
        default=5000,
        help='Số tiền phạt cho mỗi ngày quá hạn'
    )

    # Settings
    can_reserve = fields.Boolean(
        string='Được đặt trước',
        default=True,
        help='Cho phép loại độc giả này đặt trước sách'
    )
    can_extend = fields.Boolean(
        string='Được gia hạn',
        default=True,
        help='Cho phép loại độc giả này gia hạn mượn sách'
    )
    max_extensions = fields.Integer(
        string='Số lần gia hạn tối đa',
        default=2,
        help='Số lần được gia hạn tối đa cho mỗi phiếu mượn'
    )

    # Status
    active = fields.Boolean(string='Hoạt động', default=True)

    # Description
    description = fields.Text(string='Mô tả')

    # Statistics
    borrower_count = fields.Integer(
        string='Số độc giả',
        compute='_compute_borrower_count',
        store=True
    )

    @api.depends('code')
    def _compute_borrower_count(self):
        for record in self:
            record.borrower_count = self.env['res.partner'].search_count([
                ('is_borrower', '=', True),
                ('borrower_type_id', '=', record.id)
            ])

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã loại độc giả phải là duy nhất!')
    ]
