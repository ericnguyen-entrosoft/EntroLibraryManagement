# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryLocation(models.Model):
    _name = 'library.location'
    _description = 'Vị trí lưu trữ sách'
    _order = 'complete_name'
    _parent_store = True

    name = fields.Char(string='Tên vị trí', required=True, index=True)
    code = fields.Char(string='Mã vị trí', index=True)
    complete_name = fields.Char(
        string='Tên đầy đủ',
        compute='_compute_complete_name',
        store=True,
        recursive=True
    )
    parent_id = fields.Many2one(
        'library.location',
        string='Vị trí cha',
        ondelete='restrict',
        index=True
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('library.location', 'parent_id', string='Vị trí con')

    # Thông tin vị trí
    location_type = fields.Selection([
        ('warehouse', 'Kho'),
        ('building', 'Tòa nhà'),
        ('floor', 'Tầng'),
        ('room', 'Phòng'),
        ('shelf', 'Giá sách'),
        ('row', 'Kệ'),
        ('position', 'Vị trí cụ thể')
    ], string='Loại vị trí', required=True, default='shelf')

    description = fields.Text(string='Mô tả')
    capacity = fields.Integer(string='Sức chứa', help='Số lượng sách tối đa có thể lưu trữ')

    # Thông tin địa chỉ
    address = fields.Text(string='Địa chỉ')
    responsible_id = fields.Many2one('res.users', string='Người phụ trách')

    # Thống kê
    book_ids = fields.One2many('library.book', 'location_id', string='Sách')
    book_count = fields.Integer(string='Số sách', compute='_compute_book_count')
    book_available_count = fields.Integer(
        string='Số sách có sẵn',
        compute='_compute_book_count'
    )

    note = fields.Text(string='Ghi chú')
    active = fields.Boolean(string='Hoạt động', default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for location in self:
            if location.parent_id:
                location.complete_name = f"{location.parent_id.complete_name} / {location.name}"
            else:
                location.complete_name = location.name

    @api.depends('book_ids')
    def _compute_book_count(self):
        for location in self:
            location.book_count = len(location.book_ids)
            location.book_available_count = len(
                location.book_ids.filtered(lambda b: b.state == 'available')
            )

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise models.ValidationError('Không thể tạo vị trí đệ quy!')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã vị trí phải duy nhất!')
    ]

    def action_view_books(self):
        """View books at this location"""
        self.ensure_one()
        return {
            'name': 'Sách tại vị trí này',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('location_id', '=', self.id)],
            'context': {'default_location_id': self.id}
        }

    def name_get(self):
        result = []
        for record in self:
            if record.code:
                name = f"[{record.code}] {record.complete_name}"
            else:
                name = record.complete_name
            result.append((record.id, name))
        return result
