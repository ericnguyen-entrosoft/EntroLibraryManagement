# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryBookQuantCountLine(models.Model):
    _name = 'library.book.quant.count.line'
    _description = 'Chi tiết kiểm kê bản sao sách'
    _order = 'registration_number'

    count_id = fields.Many2one(
        'library.book.quant.count',
        string='Phiếu kiểm kê',
        required=True,
        ondelete='cascade',
        index=True
    )
    quant_id = fields.Many2one(
        'library.book.quant',
        string='Bản sao',
        required=True,
        ondelete='cascade',
        index=True
    )
    book_id = fields.Many2one(
        related='quant_id.book_id',
        string='Sách',
        store=True,
        readonly=True
    )
    registration_number = fields.Char(
        related='quant_id.registration_number',
        string='Số ĐKCB',
        store=True,
        readonly=True
    )
    location_id = fields.Many2one(
        related='quant_id.location_id',
        string='Vị trí',
        store=True,
        readonly=True
    )
    theory_qty = fields.Integer(
        string='SL Lý thuyết',
        required=True,
        help='Số lượng trong hệ thống'
    )
    counted_qty = fields.Integer(
        string='SL Kiểm kê',
        default=0,
        required=True,
        help='Số lượng thực tế kiểm kê được'
    )
    difference = fields.Integer(
        string='Chênh lệch',
        compute='_compute_difference',
        store=True,
        help='Chênh lệch = SL Kiểm kê - SL Lý thuyết'
    )
    note = fields.Text(string='Ghi chú')

    @api.depends('counted_qty', 'theory_qty')
    def _compute_difference(self):
        for line in self:
            line.difference = line.counted_qty - line.theory_qty
