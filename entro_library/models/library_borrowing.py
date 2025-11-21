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

    # Keep for backward compatibility, but make it optional
    book_id = fields.Many2one(
        'library.book', string='Sách', tracking=True)

    # Book lines for multiple books
    borrowing_line_ids = fields.One2many(
        'library.borrowing.line', 'borrowing_id', string='Danh sách sách')

    # Dates
    borrow_date = fields.Date(
        string='Ngày mượn', default=fields.Date.today, required=True, tracking=True)
    due_date = fields.Date(string='Ngày hạn trả', compute='_compute_due_date', store=True)
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

    # Count fields
    book_count = fields.Integer(
        string='Số sách', compute='_compute_book_count', store=True)

    # Additional info
    notes = fields.Text(string='Ghi chú')
    librarian_id = fields.Many2one(
        'res.users', string='Thủ thư', default=lambda self: self.env.user)

    # Book info (related fields for quick access) - kept for backward compatibility
    book_code = fields.Char(related='book_id.code',
                            string='Mã sách', store=True)
    book_name = fields.Char(related='book_id.name',
                            string='Tên sách', store=True)

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

    @api.depends('borrowing_line_ids.due_date')
    def _compute_due_date(self):
        """Compute due date as max due date from all lines"""
        for record in self:
            if record.borrowing_line_ids:
                due_dates = record.borrowing_line_ids.mapped('due_date')
                record.due_date = max(due_dates) if due_dates else False
            else:
                record.due_date = False

    @api.depends('borrowing_line_ids.late_days', 'borrowing_line_ids.is_overdue', 'state')
    def _compute_late_info(self):
        """Compute late days and overdue status from lines"""
        for record in self:
            if record.borrowing_line_ids:
                # Get the maximum late days from all lines
                max_late_days = max(record.borrowing_line_ids.mapped('late_days') or [0])
                record.late_days = max_late_days
                record.is_overdue = any(record.borrowing_line_ids.mapped('is_overdue'))
            else:
                record.late_days = 0
                record.is_overdue = False

    @api.depends('borrowing_line_ids.fine_amount')
    def _compute_fine_amount(self):
        """Compute total fine amount from all lines"""
        for record in self:
            record.fine_amount = sum(record.borrowing_line_ids.mapped('fine_amount'))

    @api.depends('borrowing_line_ids')
    def _compute_book_count(self):
        """Count number of books in this borrowing"""
        for record in self:
            record.book_count = len(record.borrowing_line_ids)

    @api.onchange('borrow_date')
    def _onchange_borrow_date(self):
        """Update due dates for all lines when borrow date changes"""
        if self.borrow_date:
            config = self.env['ir.config_parameter'].sudo()
            default_days = int(config.get_param(
                'library.default_borrowing_days', default=14))
            default_due_date = self.borrow_date + timedelta(days=default_days)
            # Update all lines
            for line in self.borrowing_line_ids:
                if not line.due_date:
                    line.due_date = default_due_date

    @api.constrains('borrower_id', 'borrowing_line_ids')
    def _check_borrowing_constraints(self):
        """Check borrower's total book limit"""
        for record in self:
            if record.state == 'draft':
                continue

            # Check borrower's current borrowing limit
            config = self.env['ir.config_parameter'].sudo()
            max_books = int(config.get_param(
                'library.max_books_per_borrower', default=5))

            # Count books in current borrowing lines
            current_line_count = len(record.borrowing_line_ids.filtered(
                lambda l: l.state in ('borrowed', 'overdue')
            ))

            # Count books in other borrowings
            other_borrowings = self.search([
                ('borrower_id', '=', record.borrower_id.id),
                ('state', 'in', ('borrowed', 'overdue')),
                ('id', '!=', record.id)
            ])
            other_book_count = sum(len(b.borrowing_line_ids.filtered(
                lambda l: l.state in ('borrowed', 'overdue')
            )) for b in other_borrowings)

            total_books = current_line_count + other_book_count

            if total_books > max_books:
                raise exceptions.ValidationError(
                    f'Người mượn đã đạt giới hạn {max_books} quyển sách. Hiện tại: {total_books} quyển.'
                )

    def action_confirm(self):
        """Xác nhận phiếu mượn"""
        for record in self:
            if not record.borrowing_line_ids:
                raise exceptions.ValidationError('Vui lòng thêm ít nhất một cuốn sách vào phiếu mượn.')

            record.state = 'borrowed'
            # Confirm all lines
            for line in record.borrowing_line_ids:
                line.state = 'borrowed'
                line.quant_id.write({
                    'state': 'borrowed',
                    'current_borrowing_id': record.id
                })
            # Send notification email
            if record.borrower_email:
                self._send_borrowing_email()

    def action_return(self):
        """Trả tất cả sách"""
        for record in self:
            record.return_date = fields.Date.today()
            # Return all lines
            for line in record.borrowing_line_ids.filtered(lambda l: l.state in ('borrowed', 'overdue')):
                line.action_return()
            # Update borrowing state if all lines are returned
            if all(line.state in ('returned', 'cancelled') for line in record.borrowing_line_ids):
                record.state = 'returned'

    def action_mark_lost(self):
        """Đánh dấu tất cả sách mất"""
        for record in self:
            record.state = 'lost'
            for line in record.borrowing_line_ids.filtered(lambda l: l.state in ('borrowed', 'overdue')):
                line.action_mark_lost()

    def action_cancel(self):
        """Hủy phiếu mượn"""
        for record in self:
            # Cancel all lines
            for line in record.borrowing_line_ids:
                if line.state == 'borrowed':
                    line.quant_id.write({
                        'state': 'available',
                        'current_borrowing_id': False
                    })
                line.state = 'cancelled'
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
        """Scheduled action to update overdue borrowing lines"""
        today = fields.Date.today()

        # Update overdue lines
        BorrowingLine = self.env['library.borrowing.line']
        overdue_lines = BorrowingLine.search([
            ('state', '=', 'borrowed'),
            ('due_date', '<', today)
        ])
        overdue_lines.write({'state': 'overdue'})

        # Update borrowing state if any line is overdue
        borrowings_to_update = overdue_lines.mapped('borrowing_id')
        for borrowing in borrowings_to_update:
            if borrowing.state == 'borrowed' and any(line.state == 'overdue' for line in borrowing.borrowing_line_ids):
                borrowing.state = 'overdue'
                # Send overdue notification
                if borrowing.borrower_email:
                    borrowing._send_overdue_email()

    @api.model
    def _cron_send_due_reminders(self):
        """Scheduled action to send due date reminders"""
        config = self.env['ir.config_parameter'].sudo()
        reminder_days = int(config.get_param(
            'library.reminder_days_before', default=2))

        reminder_date = fields.Date.today() + timedelta(days=reminder_days)

        # Find borrowing lines with upcoming due dates
        BorrowingLine = self.env['library.borrowing.line']
        upcoming_lines = BorrowingLine.search([
            ('state', '=', 'borrowed'),
            ('due_date', '=', reminder_date)
        ])

        # Send reminders per borrowing (not per line)
        borrowings = upcoming_lines.mapped('borrowing_id')
        for borrowing in borrowings:
            if borrowing.borrower_email:
                borrowing._send_due_reminder_email()
