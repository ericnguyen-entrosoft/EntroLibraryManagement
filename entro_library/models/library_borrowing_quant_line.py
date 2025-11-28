# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import timedelta


class LibraryBorrowingQuantLine(models.Model):
    _name = 'library.borrowing.quant.line'
    _description = 'Chi tiết mượn sách (cấp bản sao)'
    _order = 'id'

    # Parent link
    line_id = fields.Many2one(
        'library.borrowing.line',
        string='Dòng sách',
        required=True,
        ondelete='cascade',
        index=True
    )
    borrowing_id = fields.Many2one(
        related='line_id.borrowing_id',
        store=True,
        index=True,
        string='Phiếu mượn'
    )
    borrower_id = fields.Many2one(
        related='line_id.borrower_id',
        store=True,
        index=True,
        string='Người mượn'
    )
    book_id = fields.Many2one(
        related='line_id.book_id',
        store=True,
        index=True,
        string='Sách'
    )

    # Specific quant
    quant_id = fields.Many2one(
        'library.book.quant',
        string='Bản sao',
        required=True,
        ondelete='restrict',
        index=True
    )
    registration_number = fields.Char(
        related='quant_id.registration_number',
        store=True,
        string='Số ĐKCB'
    )

    # Dates
    due_date = fields.Date(
        string='Hạn trả',
        required=True
    )
    return_date = fields.Date(
        string='Ngày trả thực tế'
    )

    # State (per quant)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('borrowed', 'Đang mượn'),
        ('returned', 'Đã trả'),
        ('overdue', 'Quá hạn'),
        ('lost', 'Mất'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', default='draft', required=True, index=True)

    # Late tracking
    late_days = fields.Integer(
        string='Số ngày trễ',
        compute='_compute_late_info',
        store=True
    )
    is_overdue = fields.Boolean(
        string='Quá hạn',
        compute='_compute_late_info',
        store=True
    )
    fine_amount = fields.Float(
        string='Tiền phạt',
        compute='_compute_fine_amount',
        store=True
    )

    # Location info
    location_id = fields.Many2one(
        related='quant_id.location_id',
        string='Vị trí',
        store=True
    )

    note = fields.Text(string='Ghi chú')

    _sql_constraints = [
        ('quant_unique_per_borrowing',
         'UNIQUE(quant_id, borrowing_id)',
         'Bản sao này đã có trong phiếu mượn!'),
    ]

    @api.depends('due_date', 'return_date', 'state')
    def _compute_late_info(self):
        today = fields.Date.today()
        for line in self:
            if line.state in ('returned', 'cancelled', 'draft'):
                line.late_days = 0
                line.is_overdue = False
            elif line.state in ('borrowed', 'overdue'):
                if line.due_date and today > line.due_date:
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
        fine_rate = float(config.get_param('library.fine_rate_per_day', default=5000))
        grace_period = int(config.get_param('library.grace_period_days', default=0))

        for line in self:
            if line.late_days > grace_period:
                line.fine_amount = (line.late_days - grace_period) * fine_rate
            else:
                line.fine_amount = 0

    @api.constrains('quant_id', 'state')
    def _check_quant_availability(self):
        """Check if quant is not currently borrowed by another borrowing"""
        for line in self:
            if line.state in ('borrowed', 'overdue') and line.quant_id:
                # Check if quant is currently borrowed by another borrowing
                active_line = self.search([
                    ('quant_id', '=', line.quant_id.id),
                    ('state', 'in', ('borrowed', 'overdue')),
                    ('id', '!=', line.id)
                ], limit=1)
                if active_line:
                    raise exceptions.ValidationError(
                        f'Bản sao [{line.quant_id.registration_number}] đang được mượn '
                        f'bởi {active_line.borrowing_id.borrower_id.name}.'
                    )

    def action_confirm(self):
        """Confirm borrowing for this quant"""
        for line in self:
            if line.state != 'draft':
                continue

            line.state = 'borrowed'
            line.quant_id.write({
                'state': 'borrowed',
                'current_borrowing_id': line.borrowing_id.id
            })

    def action_return(self):
        """Return this specific quant"""
        for line in self:
            if line.state not in ('borrowed', 'overdue'):
                continue

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
            ], order='priority desc, reservation_date', limit=1)
            if reservation:
                reservation.action_notify_available()

    def action_mark_lost(self):
        """Mark this quant as lost"""
        for line in self:
            line.state = 'lost'
            line.quant_id.write({'state': 'lost'})

    def action_cancel(self):
        """Cancel this quant line"""
        for line in self:
            if line.state == 'borrowed':
                line.quant_id.write({
                    'state': 'available',
                    'current_borrowing_id': False
                })
            line.state = 'cancelled'
