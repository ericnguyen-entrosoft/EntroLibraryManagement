# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Quản lý mượn sách'
    _order = 'borrow_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'library.sequence.mixin']

    # Override sequence.mixin settings
    _sequence_field = "name"
    _sequence_date_field = "borrow_date"
    _sequence_index = False

    name = fields.Char(
        string='Mã phiếu mượn',
        compute='_compute_name', inverse='_inverse_name', readonly=False, store=True,
        copy=False, tracking=True, default='/'
    )
    posted_before = fields.Boolean(
        string='Posted Before',
        default=False,
        copy=False,
        help="Technical field to track if borrowing was ever confirmed"
    )
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
    ], string='Trạng thái', compute='_compute_state', store=True,
       default='draft', required=True, tracking=True)

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
    book_name = fields.Char(related='book_id.name',
                            string='Tên sách', store=True)

    # Borrower info
    borrower_email = fields.Char(
        related='borrower_id.email', string='Email người mượn')
    borrower_phone = fields.Char(
        related='borrower_id.phone', string='Số điện thoại')

    active = fields.Boolean(string='Hoạt động', default=True)

    @api.depends('state', 'borrow_date', 'posted_before', 'sequence_number', 'sequence_prefix')
    def _compute_name(self):
        """Compute name based on state - similar to account.move"""
        self = self.sorted(lambda m: m.borrow_date)

        for record in self:
            # Skip cancelled records
            if record.state == 'cancelled':
                continue

            has_name = record.name and record.name != '/'

            # Reset name if date doesn't match sequence
            if not record.posted_before and not record._sequence_matches_date():
                record.name = False
                continue

            # Assign sequence when confirmed (not draft or cancelled)
            if record.borrow_date and not has_name and record.state not in ('draft', 'cancelled'):
                record._set_next_sequence()

        self._inverse_name()

    def _inverse_name(self):
        """Allow manual name setting - called after _compute_name"""
        # Parse sequence prefix and number from name
        to_write = []
        for record in self:
            if record.name and record.name != '/':
                # Use sequence.mixin's parsing logic
                format_values = record._get_sequence_format_param(record.name)[1]
                if format_values.get('seq'):
                    to_write.append({
                        'id': record.id,
                        'sequence_number': format_values['seq'],
                        'sequence_prefix': format_values.get('prefix1', ''),
                    })
        if to_write:
            self.env['library.borrowing'].browse([x['id'] for x in to_write]).write({
                'sequence_number': False,
                'sequence_prefix': False,
            })

    def _set_next_sequence(self):
        """Set the next sequence number - uses sequence.mixin logic"""
        self.ensure_one()
        # Call the parent mixin's _set_next_sequence which handles everything
        super(LibraryBorrowing, self)._set_next_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        """Get the SQL domain to retrieve the previous sequence number."""
        self.ensure_one()
        where_string = "WHERE state != 'cancelled'"
        where_params = {}

        if self.borrow_date:
            date_start, date_end, *_ = self._get_sequence_date_range(
                self._deduce_sequence_number_reset(self.name or '')
            )
            where_string += " AND borrow_date >= %(date_from)s AND borrow_date <= %(date_to)s"
            where_params['date_from'] = date_start
            where_params['date_to'] = date_end

        return where_string, where_params

    def _get_starting_sequence(self):
        """Get the starting sequence when no previous sequence exists."""
        self.ensure_one()
        if self.borrow_date:
            return f'PM/{self.borrow_date.year}/{self.borrow_date.month:02d}/00000'
        return 'PM/00000'

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

    @api.depends('borrowing_line_ids.state')
    def _compute_state(self):
        """Compute borrowing state based on line states"""
        for record in self:
            if not record.borrowing_line_ids:
                # No lines yet, keep current state (draft by default)
                continue

            line_states = record.borrowing_line_ids.mapped('state')

            # If all lines are cancelled
            if all(state == 'cancelled' for state in line_states):
                record.state = 'cancelled'
            # If all lines are returned or cancelled
            elif all(state in ('returned', 'cancelled') for state in line_states):
                record.state = 'returned'
            # If any line is overdue
            elif 'overdue' in line_states:
                record.state = 'overdue'
            # If any line is borrowed
            elif 'borrowed' in line_states:
                record.state = 'borrowed'


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

            # Mark as posted before (for sequence logic)
            record.posted_before = True

            # Confirm all lines - borrowing state will be computed automatically
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
        """Trả sách - always show wizard for flexibility"""
        for record in self:
            # All lines in borrowed/overdue state
            lines_to_return = record.borrowing_line_ids.filtered(
                lambda l: l.state in ('borrowed', 'overdue')
            )

            if not lines_to_return:
                raise exceptions.ValidationError('Không có sách nào để trả.')

            # Always show wizard to allow user to select which books to return
            return {
                'name': 'Xác nhận trả sách',
                'type': 'ir.actions.act_window',
                'res_model': 'library.return.confirmation',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_borrowing_id': record.id,
                    'button_validate_borrowing_ids': [record.id],
                }
            }

    def action_mark_lost(self):
        """Đánh dấu tất cả sách mất"""
        for record in self:
            # Mark all borrowed/overdue lines as lost - borrowing state will be computed
            for line in record.borrowing_line_ids.filtered(lambda l: l.state in ('borrowed', 'overdue')):
                line.action_mark_lost()

    def action_cancel(self):
        """Hủy phiếu mượn"""
        for record in self:
            # Cancel all lines - borrowing state will be computed
            for line in record.borrowing_line_ids:
                if line.state == 'borrowed':
                    line.quant_id.write({
                        'state': 'available',
                        'current_borrowing_id': False
                    })
                line.state = 'cancelled'

    def action_set_to_draft(self):
        """Chuyển về nháp"""
        for record in self:
            # Set all lines to draft - borrowing state will be computed
            for line in record.borrowing_line_ids:
                line.state = 'draft'

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

        # Send overdue notification (borrowing state will be computed automatically)
        borrowings_to_notify = overdue_lines.mapped('borrowing_id')
        for borrowing in borrowings_to_notify:
            if borrowing.borrower_email and borrowing.state == 'overdue':
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
