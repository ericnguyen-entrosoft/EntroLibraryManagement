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
    quant_ids = fields.One2many('library.book.quant', 'location_id', string='Bản sao sách')
    quant_count = fields.Integer(string='Số bản sao', compute='_compute_quant_count')
    quant_available_count = fields.Integer(
        string='Số bản sao có sẵn',
        compute='_compute_quant_count'
    )
    book_count = fields.Integer(string='Số đầu sách', compute='_compute_quant_count',
                                help='Số lượng tác phẩm khác nhau (không tính bản sao)')

    note = fields.Text(string='Ghi chú')
    active = fields.Boolean(string='Hoạt động', default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for location in self:
            if location.parent_id:
                location.complete_name = f"{location.parent_id.complete_name} / {location.name}"
            else:
                location.complete_name = location.name

    @api.depends('quant_ids', 'quant_ids.state', 'quant_ids.book_id')
    def _compute_quant_count(self):
        for location in self:
            location.quant_count = len(location.quant_ids)
            location.quant_available_count = len(
                location.quant_ids.filtered(lambda q: q.state == 'available')
            )
            # Count unique books
            location.book_count = len(location.quant_ids.mapped('book_id'))

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise models.ValidationError('Không thể tạo vị trí đệ quy!')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã vị trí phải duy nhất!')
    ]

    def action_view_quants(self):
        """View book quants at this location"""
        self.ensure_one()
        return {
            'name': 'Bản sao sách tại vị trí này',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.quant',
            'view_mode': 'list,form',
            'domain': [('location_id', '=', self.id)],
            'context': {'default_location_id': self.id}
        }

    def action_view_books(self):
        """View unique books at this location"""
        self.ensure_one()
        book_ids = self.quant_ids.mapped('book_id').ids
        return {
            'name': 'Đầu sách tại vị trí này',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('id', 'in', book_ids)],
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
