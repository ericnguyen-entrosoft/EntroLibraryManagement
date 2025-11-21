# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import timedelta


class LibraryReservation(models.Model):
    _name = 'library.reservation'
    _description = 'Đặt trước sách'
    _order = 'reservation_date, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã đặt trước', required=True,
                       copy=False, readonly=True, default='New')
    borrower_id = fields.Many2one(
        'res.partner', string='Người đặt', required=True, tracking=True)
    quant_id = fields.Many2one(
        'library.book.quant', string='Bản sao sách', tracking=True)
    book_id = fields.Many2one(
        'library.book', string='Sách', required=True, tracking=True)

    # Dates
    reservation_date = fields.Date(
        string='Ngày đặt', default=fields.Date.today, required=True, tracking=True)
    expiry_date = fields.Date(string='Hạn giữ sách',
                              required=True, tracking=True)
    notification_date = fields.Date(string='Ngày thông báo')

    # State
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('active', 'Đang chờ'),
        ('available', 'Sách đã sẵn sàng'),
        ('fulfilled', 'Đã hoàn thành'),
        ('expired', 'Hết hạn'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', default='draft', required=True, tracking=True)

    # Additional info
    notes = fields.Text(string='Ghi chú')
    priority = fields.Selection([
        ('0', 'Thấp'),
        ('1', 'Bình thường'),
        ('2', 'Cao'),
        ('3', 'Khẩn cấp')
    ], string='Độ ưu tiên', default='1')

    # Book info
    book_name = fields.Char(related='book_id.name',
                            string='Tên sách', store=True)

    # Quant info
    registration_number = fields.Char(
        related='quant_id.registration_number', string='Số ĐKCB', store=True)
    quant_state = fields.Selection(
        related='quant_id.state', string='Trạng thái bản sao')

    # Borrower info
    borrower_email = fields.Char(related='borrower_id.email', string='Email')
    borrower_phone = fields.Char(
        related='borrower_id.phone', string='Số điện thoại')

    active = fields.Boolean(string='Hoạt động', default=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'library.reservation') or 'New'
        return super(LibraryReservation, self).create(vals)

    @api.onchange('reservation_date')
    def _onchange_reservation_date(self):
        if self.reservation_date:
            config = self.env['ir.config_parameter'].sudo()
            hold_days = int(config.get_param(
                'library.reservation_hold_days', default=3))
            self.expiry_date = self.reservation_date + \
                timedelta(days=hold_days)

    @api.constrains('borrower_id', 'quant_id')
    def _check_reservation_constraints(self):
        for record in self:
            if not record.quant_id:
                continue

            # Check if borrower already has active reservation for this quant
            existing = self.search([
                ('borrower_id', '=', record.borrower_id.id),
                ('quant_id', '=', record.quant_id.id),
                ('state', 'in', ('draft', 'active', 'available')),
                ('id', '!=', record.id)
            ])
            if existing:
                raise exceptions.ValidationError(
                    f'Bạn đã có đặt trước cho bản sao sách [{record.quant_id.registration_number}] "{record.book_id.name}" rồi!'
                )

            # Check if borrower is currently borrowing this quant
            current_borrowing = self.env['library.borrowing.line'].search([
                ('borrowing_id.borrower_id', '=', record.borrower_id.id),
                ('quant_id', '=', record.quant_id.id),
                ('state', 'in', ('borrowed', 'overdue'))
            ], limit=1)
            if current_borrowing:
                raise exceptions.ValidationError(
                    f'Bạn đang mượn bản sao sách [{record.quant_id.registration_number}] "{record.book_id.name}"!'
                )

    def action_confirm(self):
        """Xác nhận đặt trước"""
        for record in self:
            record.state = 'active'

    def action_notify_available(self):
        """Notify borrower that quant is available"""
        for record in self:
            record.state = 'available'
            record.notification_date = fields.Date.today()
            if record.quant_id:
                record.quant_id.write({'state': 'reserved'})
            # Send email notification
            if record.borrower_email:
                record._send_available_email()

    def action_fulfill(self):
        """Mark reservation as fulfilled (quant borrowed)"""
        for record in self:
            record.state = 'fulfilled'
            # Create borrowing record with quant
            if record.quant_id:
                borrowing = self.env['library.borrowing'].create({
                    'borrower_id': record.borrower_id.id,
                    'borrow_date': fields.Date.today(),
                    'notes': f'Từ đặt trước: {record.name}'
                })
                borrowing.action_confirm()

    def action_cancel(self):
        """Hủy đặt trước"""
        for record in self:
            if record.state == 'available' and record.quant_id:
                record.quant_id.write({'state': 'available'})
            record.state = 'cancelled'

    def action_set_to_draft(self):
        """Chuyển về nháp"""
        for record in self:
            record.state = 'draft'

    def _send_available_email(self):
        """Send email when book becomes available"""
        self.ensure_one()
        template = self.env.ref(
            'entro_library.email_template_reservation_available', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def _cron_expire_reservations(self):
        """Scheduled action to expire old reservations"""
        today = fields.Date.today()
        expired = self.search([
            ('state', '=', 'available'),
            ('expiry_date', '<', today)
        ])
        for reservation in expired:
            reservation.state = 'expired'
            if reservation.quant_id:
                reservation.quant_id.write({'state': 'available'})

            # Notify next person in queue for same quant or book
            if reservation.quant_id:
                next_reservation = self.search([
                    ('quant_id', '=', reservation.quant_id.id),
                    ('state', '=', 'active')
                ], order='priority desc, reservation_date', limit=1)
            else:
                next_reservation = self.search([
                    ('book_id', '=', reservation.book_id.id),
                    ('state', '=', 'active')
                ], order='priority desc, reservation_date', limit=1)

            if next_reservation:
                next_reservation.action_notify_available()
