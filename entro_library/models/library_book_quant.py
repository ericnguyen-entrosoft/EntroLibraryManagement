# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class LibraryBookQuant(models.Model):
    _name = 'library.book.quant'
    _description = 'Quản lý bản sao sách vật lý'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'registration_number'
    _rec_name = 'registration_number'

    name = fields.Char(
        string='Tên',
        compute='_compute_name',
        store=True
    )
    book_id = fields.Many2one(
        'library.book',
        string='Sách',
        required=True,
        ondelete='cascade',
        index=True
    )

    category_id = fields.Many2one(related='book_id.category_id')

    registration_number = fields.Char(
        string='Số ĐKCB',
        required=False,
        index=True,
        help='Số đăng ký cá biệt cho bản sao này'
    )

    code_registration_number = fields.Char(
        string='Mã số ĐKCB',
        required=False,
        index=True,
        help='Mã số đăng ký cá biệt cho bản sao này'
    )

    quantity = fields.Integer(
        string='Số lượng',
        default=1,
        required=True,
        help='Số lượng bản sao vật lý'
    )

    # Vị trí lưu trữ
    location_id = fields.Many2one(
        'library.location',
        string='Vị trí lưu trữ',
        index=True
    )

    # Trạng thái
    state = fields.Selection([
        ('available', 'Có sẵn'),
        ('borrowed', 'Đang mượn'),
        ('reserved', 'Đã đặt trước'),
        ('maintenance', 'Bảo trì'),
        ('lost', 'Mất'),
        ('damaged', 'Hư hỏng')
    ], string='Trạng thái', default='available', required=True, tracking=True, index=True)

    # Borrowing information
    current_borrowing_id = fields.Many2one(
        'library.borrowing',
        string='Phiếu mượn hiện tại',
        readonly=True
    )
    current_borrower_id = fields.Many2one(
        related='current_borrowing_id.borrower_id',
        string='Người đang mượn',
        store=True
    )
    borrowing_line_ids = fields.One2many(
        'library.borrowing.line',
        'quant_id',
        string='Lịch sử mượn'
    )
    reservation_ids = fields.One2many(
        'library.reservation',
        'quant_id',
        string='Đặt trước'
    )

    current_reservation_count = fields.Integer(
        string='Đặt trước',
        compute='_compute_borrowing_stats',
        store=True
    )

    # Ghi chú
    note = fields.Text(string='Ghi chú')

    # Trạng thái
    active = fields.Boolean(string='Hoạt động', default=True)

    # Quant Type
    quant_type_id = fields.Many2one(
        'library.quant.type',
        string='Loại bản sao',
        required=True,
        default=lambda self: self.env.ref('entro_library.quant_type_no_borrow', raise_if_not_found=False),
        index=True
    )
    color = fields.Char(
        related='quant_type_id.color',
        string='Màu',
        readonly=True
    )
    can_borrow = fields.Boolean(
        related='quant_type_id.can_borrow',
        string='Có thể mượn',
        store=True,
        readonly=True
    )

    _sql_constraints = [
        ('registration_number_unique', 'UNIQUE(registration_number)',
         'Số ĐKCB phải là duy nhất!'),
        ('quantity_positive', 'CHECK(quantity > 0)',
         'Số lượng phải lớn hơn 0!')
    ]

    @api.depends('book_id', 'registration_number')
    def _compute_name(self):
        for quant in self:
            if quant.registration_number and quant.book_id:
                quant.name = f"[{quant.registration_number}] {quant.book_id.name}"
            elif quant.registration_number:
                quant.name = quant.registration_number
            elif quant.book_id:
                quant.name = quant.book_id.name
            else:
                quant.name = 'Bản sao mới'

    @api.depends('reservation_ids.state')
    def _compute_borrowing_stats(self):
        for quant in self:
            quant.current_reservation_count = len(quant.reservation_ids.filtered(
                lambda r: r.state in ('active', 'available')
            ))

    def action_view_borrowings(self):
        """View quant's borrowing history"""
        self.ensure_one()
        return {
            'name': 'Lịch sử mượn',
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing.line',
            'view_mode': 'list,form',
            'domain': [('quant_id', '=', self.id)],
            'context': {'default_quant_id': self.id, 'default_book_id': self.book_id.id}
        }

    def action_view_reservations(self):
        """View quant's reservations"""
        self.ensure_one()
        return {
            'name': 'Đặt trước',
            'type': 'ir.actions.act_window',
            'res_model': 'library.reservation',
            'view_mode': 'list,form',
            'domain': [('quant_id', '=', self.id)],
            'context': {'default_quant_id': self.id, 'default_book_id': self.book_id.id}
        }
