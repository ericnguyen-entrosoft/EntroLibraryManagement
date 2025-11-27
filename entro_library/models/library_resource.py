# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryResource(models.Model):
    _name = 'library.resource'
    _description = 'Kho tài nguyên thư viện'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Tên kho tài nguyên', required=True, tracking=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    code = fields.Char(string='Mã', required=True, copy=False, tracking=True)

    # Policy and description
    description = fields.Html(string='Mô tả')
    policy = fields.Html(string='Chính sách', help='Chính sách sử dụng tài nguyên này')

    # Icon/Color for UI
    color = fields.Integer(string='Màu', default=0)
    icon = fields.Char(string='Icon', default='fa-book', help='Font Awesome icon class')

    # Book assignments
    book_ids = fields.Many2many(
        'library.book',
        'library_resource_book_rel',
        'resource_id',
        'book_id',
        string='Sách'
    )
    book_count = fields.Integer(
        string='Số lượng sách',
        compute='_compute_book_count',
        store=True
    )

    # Statistics
    available_book_count = fields.Integer(
        string='Sách có sẵn',
        compute='_compute_statistics'
    )
    borrowed_book_count = fields.Integer(
        string='Đang mượn',
        compute='_compute_statistics'
    )

    # Status
    active = fields.Boolean(string='Hoạt động', default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Mã kho tài nguyên phải là duy nhất!'),
    ]

    @api.depends('book_ids')
    def _compute_book_count(self):
        for resource in self:
            resource.book_count = len(resource.book_ids)

    @api.depends('book_ids', 'book_ids.available_quant_count', 'book_ids.borrowed_quant_count')
    def _compute_statistics(self):
        for resource in self:
            resource.available_book_count = sum(resource.book_ids.mapped('available_quant_count'))
            resource.borrowed_book_count = sum(resource.book_ids.mapped('borrowed_quant_count'))

    def action_view_books(self):
        """View books assigned to this resource"""
        self.ensure_one()
        return {
            'name': f'Sách - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.book_ids.ids)],
            'context': {
                'default_resource_ids': [(4, self.id)],
            }
        }
