# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import timedelta


class LibraryBorrowingLine(models.Model):
    _name = 'library.borrowing.line'
    _description = 'Chi tiết mượn sách'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Thứ tự', default=10)
    borrowing_id = fields.Many2one(
        'library.borrowing', string='Phiếu mượn', required=True, ondelete='cascade')
    quant_id = fields.Many2one(
        'library.book.quant', string='Bản sao sách', required=True,
        domain="[('state', '=', 'available'), ('quant_type', '=', 'can_borrow')]", ondelete='restrict')
    book_id = fields.Many2one(
        related='quant_id.book_id', string='Sách', store=True, readonly=True)

    # Dates
    due_date = fields.Date(string='Ngày hạn trả', required=True)
    return_date = fields.Date(string='Ngày trả thực tế')

    # State
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('borrowed', 'Đang mượn'),
        ('returned', 'Đã trả'),
        ('overdue', 'Quá hạn'),
        ('lost', 'Mất sách'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', default='draft', required=True)

    # Computed fields
    late_days = fields.Integer(
        string='Số ngày trễ', compute='_compute_late_info', store=True)
    is_overdue = fields.Boolean(
        string='Quá hạn', compute='_compute_late_info', store=True)
    fine_amount = fields.Float(
        string='Tiền phạt', compute='_compute_fine_amount', store=True)

    # Quant info (related fields for quick access)
    registration_number = fields.Char(
        related='quant_id.registration_number', string='Số ĐKCB', store=True)
    quant_location = fields.Char(
        related='quant_id.location_id.complete_name', string='Vị trí sách')

    # Book info (related fields for quick access)
    book_code = fields.Char(related='book_id.code', string='Mã sách', store=True)
    book_name = fields.Char(related='book_id.name', string='Tên sách', store=True)

    # Borrowing info (related fields for reports)
    borrower_id = fields.Many2one(
        related='borrowing_id.borrower_id', string='Người mượn', store=True, readonly=True)
    borrow_date = fields.Date(
        related='borrowing_id.borrow_date', string='Ngày mượn', store=True, readonly=True)

    # Additional info
    notes = fields.Text(string='Ghi chú')

    @api.depends('due_date', 'return_date', 'state')
    def _compute_late_info(self):
        today = fields.Date.today()
        for line in self:
            if line.state in ('returned', 'cancelled', 'draft'):
                line.late_days = 0
                line.is_overdue = False
            elif line.state == 'borrowed':
                if line.due_date and today > line.due_date:
                    line.late_days = (today - line.due_date).days
                    line.is_overdue = True
                else:
                    line.late_days = 0
                    line.is_overdue = False
            elif line.state == 'overdue':
                if line.due_date:
                    line.late_days = (today - line.due_date).days
                    line.is_overdue = True
                else:
                    line.late_days = 0
                    line.is_overdue = False
            else:
                line.late_days = 0
                line.is_overdue = False

    @api.depends('late_days')
    def _compute_fine_amount(self):
        config = self.env['ir.config_parameter'].sudo()
        fine_rate = float(config.get_param(
            'library.fine_rate_per_day', default=5000))
        grace_period = int(config.get_param(
            'library.grace_period_days', default=0))

        for line in self:
            if line.late_days > grace_period:
                line.fine_amount = (line.late_days - grace_period) * fine_rate
            else:
                line.fine_amount = 0

    @api.onchange('quant_id')
    def _onchange_quant_id(self):
        """Set default due date when quant is selected"""
        if self.quant_id and self.borrowing_id.borrow_date:
            config = self.env['ir.config_parameter'].sudo()
            default_days = int(config.get_param(
                'library.default_borrowing_days', default=14))
            self.due_date = self.borrowing_id.borrow_date + timedelta(days=default_days)

    @api.constrains('quant_id', 'borrowing_id', 'state')
    def _check_quant_availability(self):
        """Check if quant is available for borrowing"""
        for line in self:
            if line.state in ('draft', 'borrowed') and line.quant_id:
                # Check if quant type allows borrowing
                if line.quant_id.quant_type == 'no_borrow':
                    raise exceptions.ValidationError(
                        f'Bản sao sách [{line.quant_id.registration_number}] "{line.book_id.name}" chỉ được đọc tại chỗ, không thể mượn về.'
                    )

                # Check if quant is currently borrowed by another borrowing
                active_borrowing_line = self.search([
                    ('quant_id', '=', line.quant_id.id),
                    ('state', 'in', ('borrowed', 'overdue')),
                    ('id', '!=', line.id)
                ], limit=1)
                if active_borrowing_line:
                    raise exceptions.ValidationError(
                        f'Bản sao sách [{line.quant_id.registration_number}] "{line.book_id.name}" hiện đang được mượn bởi {active_borrowing_line.borrowing_id.borrower_id.name}.'
                    )

    def action_return(self):
        """Return this book quant"""
        for line in self:
            line.return_date = fields.Date.today()
            line.state = 'returned'
            line.quant_id.write({
                'state': 'available',
                'current_borrowing_id': False
            })
            # Check for reservations
            reservation = self.env['library.reservation'].search([
                ('quant_id', '=', line.quant_id.id),
                ('state', '=', 'active')
            ], order='reservation_date', limit=1)
            if reservation:
                reservation.action_notify_available()

    def action_mark_lost(self):
        """Mark this book quant as lost"""
        for line in self:
            line.state = 'lost'
            line.quant_id.write({'state': 'lost'})
