# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Quản lý mượn sách'
    _order = 'borrow_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã phiếu mượn', required=True,
                       copy=False, readonly=True, default='New')
    borrower_id = fields.Many2one(
        'res.partner', string='Người mượn', required=True, tracking=True)
    book_id = fields.Many2one(
        'library.book', string='Sách', required=True, tracking=True)

    # Dates
    borrow_date = fields.Date(
        string='Ngày mượn', default=fields.Date.today, required=True, tracking=True)
    due_date = fields.Date(string='Ngày hạn trả', required=True, tracking=True)
    return_date = fields.Date(string='Ngày trả thực tế', tracking=True)

    # State
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('borrowed', 'Đang mượn'),
        ('returned', 'Đã trả'),
        ('overdue', 'Quá hạn'),
        ('lost', 'Mất sách'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', default='draft', required=True, tracking=True)

    # Computed fields
    late_days = fields.Integer(
        string='Số ngày trễ', compute='_compute_late_info', store=True)
    is_overdue = fields.Boolean(
        string='Quá hạn', compute='_compute_late_info', store=True)
    fine_amount = fields.Float(
        string='Tiền phạt', compute='_compute_fine_amount', store=True)

    # Additional info
    notes = fields.Text(string='Ghi chú')
    librarian_id = fields.Many2one(
        'res.users', string='Thủ thư', default=lambda self: self.env.user)

    # Book info (related fields for quick access)
    book_code = fields.Char(related='book_id.code',
                            string='Mã sách', store=True)
    book_name = fields.Char(related='book_id.name',
                            string='Tên sách', store=True)
    book_location = fields.Char(
        related='book_id.location_id.complete_name', string='Vị trí sách')

    # Borrower info
    borrower_email = fields.Char(
        related='borrower_id.email', string='Email người mượn')
    borrower_phone = fields.Char(
        related='borrower_id.phone', string='Số điện thoại')

    active = fields.Boolean(string='Hoạt động', default=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'library.borrowing') or 'New'
        return super(LibraryBorrowing, self).create(vals)

    @api.depends('due_date', 'return_date', 'state')
    def _compute_late_info(self):
        today = fields.Date.today()
        for record in self:
            if record.state in ('returned', 'cancelled', 'draft'):
                record.late_days = 0
                record.is_overdue = False
            elif record.state == 'borrowed':
                if record.due_date and today > record.due_date:
                    record.late_days = (today - record.due_date).days
                    record.is_overdue = True
                else:
                    record.late_days = 0
                    record.is_overdue = False
            elif record.state == 'overdue':
                if record.due_date:
                    record.late_days = (today - record.due_date).days
                    record.is_overdue = True
                else:
                    record.late_days = 0
                    record.is_overdue = False
            else:
                record.late_days = 0
                record.is_overdue = False

    @api.depends('late_days')
    def _compute_fine_amount(self):
        config = self.env['ir.config_parameter'].sudo()
        fine_rate = float(config.get_param(
            'library.fine_rate_per_day', default=5000))
        grace_period = int(config.get_param(
            'library.grace_period_days', default=0))

        for record in self:
            if record.late_days > grace_period:
                record.fine_amount = (
                    record.late_days - grace_period) * fine_rate
            else:
                record.fine_amount = 0

    @api.onchange('borrow_date')
    def _onchange_borrow_date(self):
        if self.borrow_date:
            config = self.env['ir.config_parameter'].sudo()
            default_days = int(config.get_param(
                'library.default_borrowing_days', default=14))
            self.due_date = self.borrow_date + timedelta(days=default_days)

    @api.constrains('borrower_id', 'book_id', 'borrow_date')
    def _check_borrowing_constraints(self):
        for record in self:
            if record.state == 'draft':
                continue

            # Check if book is available
            if record.book_id.state != 'available' and record.state in ('draft', 'borrowed'):
                active_borrowing = self.search([
                    ('book_id', '=', record.book_id.id),
                    ('state', 'in', ('borrowed', 'overdue')),
                    ('id', '!=', record.id)
                ], limit=1)
                if active_borrowing:
                    raise exceptions.ValidationError(
                        f'Sách "{record.book_id.name}" hiện đang được mượn bởi {active_borrowing.borrower_id.name}.'
                    )

            # Check borrower's current borrowing limit
            config = self.env['ir.config_parameter'].sudo()
            max_books = int(config.get_param(
                'library.max_books_per_borrower', default=5))

            current_borrowings = self.search_count([
                ('borrower_id', '=', record.borrower_id.id),
                ('state', 'in', ('borrowed', 'overdue')),
                ('id', '!=', record.id)
            ])

            if current_borrowings >= max_books:
                raise exceptions.ValidationError(
                    f'Người mượn đã đạt giới hạn {max_books} quyển sách.'
                )

    def action_confirm(self):
        """Xác nhận phiếu mượn"""
        for record in self:
            record.state = 'borrowed'
            record.book_id.write({
                'state': 'borrowed',
                'current_borrowing_id': record.id
            })
            # Send notification email
            if record.borrower_email:
                self._send_borrowing_email()

    def action_return(self):
        """Trả sách"""
        for record in self:
            record.return_date = fields.Date.today()
            record.state = 'returned'
            record.book_id.write({
                'state': 'available',
                'current_borrowing_id': False
            })
            # Check for reservations
            reservation = self.env['library.reservation'].search([
                ('book_id', '=', record.book_id.id),
                ('state', '=', 'active')
            ], order='reservation_date', limit=1)
            if reservation:
                reservation.action_notify_available()

    def action_mark_lost(self):
        """Đánh dấu sách mất"""
        for record in self:
            record.state = 'lost'
            record.book_id.write({'state': 'lost'})

    def action_cancel(self):
        """Hủy phiếu mượn"""
        for record in self:
            if record.state == 'borrowed':
                record.book_id.write({
                    'state': 'available',
                    'current_borrowing_id': False
                })
            record.state = 'cancelled'

    def action_set_to_draft(self):
        """Chuyển về nháp"""
        for record in self:
            record.state = 'draft'

    def _send_borrowing_email(self):
        """Send email notification to borrower"""
        self.ensure_one()
        template = self.env.ref(
            'entro_library.email_template_borrowing_confirmation', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_due_reminder_email(self):
        """Send reminder email before due date"""
        self.ensure_one()
        template = self.env.ref(
            'entro_library.email_template_due_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_overdue_email(self):
        """Send overdue notification email"""
        self.ensure_one()
        template = self.env.ref(
            'entro_library.email_template_overdue_notification', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def _cron_update_overdue_status(self):
        """Scheduled action to update overdue borrowings"""
        today = fields.Date.today()
        overdue_borrowings = self.search([
            ('state', '=', 'borrowed'),
            ('due_date', '<', today)
        ])
        overdue_borrowings.write({'state': 'overdue'})

        # Send overdue notifications
        for borrowing in overdue_borrowings:
            if borrowing.borrower_email:
                borrowing._send_overdue_email()

    @api.model
    def _cron_send_due_reminders(self):
        """Scheduled action to send due date reminders"""
        config = self.env['ir.config_parameter'].sudo()
        reminder_days = int(config.get_param(
            'library.reminder_days_before', default=2))

        reminder_date = fields.Date.today() + timedelta(days=reminder_days)
        borrowings = self.search([
            ('state', '=', 'borrowed'),
            ('due_date', '=', reminder_date)
        ])

        for borrowing in borrowings:
            if borrowing.borrower_email:
                borrowing._send_due_reminder_email()
