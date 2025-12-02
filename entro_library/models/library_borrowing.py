# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta
import uuid
import secrets
import qrcode
import io
import base64


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Quản lý mượn sách'
    _order = 'borrow_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'library.sequence.mixin', 'barcodes.barcode_events_mixin']
    _rec_names_search = ['name', 'checkout_code', 'access_token']

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
    checkout_code = fields.Char(
        string='Mã xác nhận',
        copy=False,
        index=True,
        help='Mã UUID để người mượn xuất trình khi đến thư viện nhận sách'
    )
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        index=True,
        groups='base.group_user',
        help='Token for public access to borrowing record via QR code'
    )
    qr_code = fields.Binary(
        string='QR Code',
        attachment=True,
        copy=False,
        help='QR code for quick access to borrowing record'
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
    due_date = fields.Date(
        string='Ngày hạn trả',
        default=lambda self: self._default_due_date(),
        required=True,
        tracking=True,
        help='Ngày hẹn trả sách - áp dụng chung cho tất cả sách trong phiếu mượn'
    )
    return_date = fields.Date(string='Ngày trả thực tế', tracking=True)

    # Extension fields
    extension_requested = fields.Boolean(
        string='Đã yêu cầu gia hạn',
        default=False,
        copy=False,
        tracking=True,
        help='Người mượn đã yêu cầu gia hạn một lần'
    )
    extension_date = fields.Date(
        string='Ngày yêu cầu gia hạn',
        copy=False,
        tracking=True
    )
    original_due_date = fields.Date(
        string='Hạn trả gốc',
        copy=False,
        help='Ngày hạn trả ban đầu trước khi gia hạn'
    )

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

    def generate_checkout_code(self):
        """Generate unique checkout code using UUID"""
        self.ensure_one()
        if not self.checkout_code:
            # Generate short UUID code (8 characters)
            self.checkout_code = str(uuid.uuid4())[:8].upper()
        return self.checkout_code

    def _generate_access_token(self):
        """Generate unique access token for secure public access and QR code"""
        self.ensure_one()
        if not self.access_token:
            # Generate secure random token (32 bytes = 43 characters in URL-safe base64)
            self.access_token = secrets.token_urlsafe(32)

        # Generate QR code after token is created and record has ID
        if self.id and self.access_token:
            self._generate_qr_code()

        return self.access_token

    def _generate_qr_code(self):
        """Generate QR code image for borrowing access"""
        self.ensure_one()
        if not self.access_token or not self.id:
            return

        try:
            # Get base URL
            base_url = self.get_base_url()
            url = f"{base_url}/my/borrowing/{self.id}?access_token={self.access_token}"

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to binary
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            self.qr_code = base64.b64encode(buffer.getvalue())
        except Exception as e:
            # Log error but don't fail
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Failed to generate QR code for borrowing {self.id}: {e}")
            self.qr_code = False

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

    @api.model
    def _default_due_date(self):
        """Calculate default due date based on system configuration"""
        config = self.env['ir.config_parameter'].sudo()
        default_days = int(config.get_param('library.default_borrowing_days', default=14))
        return fields.Date.today() + timedelta(days=default_days)

    @api.depends('borrowing_line_ids.late_days', 'borrowing_line_ids.is_overdue', 'state')
    def _compute_late_info(self):
        """Compute late days and overdue status from lines (aggregated from quant lines)"""
        for record in self:
            if record.borrowing_line_ids:
                # Get the maximum late days from all lines (which aggregate from quant lines)
                max_late_days = max(record.borrowing_line_ids.mapped('late_days') or [0])
                record.late_days = max_late_days
                record.is_overdue = any(record.borrowing_line_ids.mapped('is_overdue'))
            else:
                record.late_days = 0
                record.is_overdue = False

    @api.depends('borrowing_line_ids.fine_amount')
    def _compute_fine_amount(self):
        """Compute total fine amount from all lines (aggregated from quant lines)"""
        for record in self:
            record.fine_amount = sum(record.borrowing_line_ids.mapped('fine_amount'))

    @api.depends('borrowing_line_ids', 'borrowing_line_ids.requested_quantity')
    def _compute_book_count(self):
        """Count number of book titles (lines) in this borrowing"""
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
        """Update due date when borrow date changes"""
        if self.borrow_date and not self.due_date:
            config = self.env['ir.config_parameter'].sudo()
            default_days = int(config.get_param(
                'library.default_borrowing_days', default=14))
            self.due_date = self.borrow_date + timedelta(days=default_days)

    @api.constrains('borrower_id', 'borrowing_line_ids')
    def _check_borrowing_constraints(self):
        """Check borrower's total book limit and resource-based limits"""
        for record in self:
            if record.state == 'draft':
                continue

            # Check borrower's current borrowing limit (global)
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

            # Check resource-based limits for each book in borrowing
            resource_book_count = {}  # Track books per resource
            for line in record.borrowing_line_ids.filtered(lambda l: l.state in ('borrowed', 'overdue')):
                # Get resources for this book via quant location
                if line.quant_id and line.quant_id.location_id and line.quant_id.location_id.resource_id:
                    resource = line.quant_id.location_id.resource_id

                    # Initialize counter for this resource
                    if resource.id not in resource_book_count:
                        resource_book_count[resource.id] = {
                            'resource': resource,
                            'count': 0
                        }

                    resource_book_count[resource.id]['count'] += 1

            # Validate against each resource's limit
            for resource_id, data in resource_book_count.items():
                resource = data['resource']
                current_count_in_borrowing = data['count']

                # Get current borrowed count from other borrowings for this resource
                can_borrow, message, current_count_other = resource.check_borrowing_limit(
                    record.borrower_id.id,
                    book_id=None,
                    exclude_borrowing_id=record.id
                )

                total_from_resource = current_count_in_borrowing + current_count_other

                if total_from_resource > resource.max_books_per_borrower:
                    raise exceptions.ValidationError(
                        f'Vượt quá giới hạn của tài nguyên "{resource.name}": '
                        f'{total_from_resource}/{resource.max_books_per_borrower} quyển.'
                    )

    def action_confirm(self):
        """Xác nhận phiếu mượn"""
        for record in self:
            if not record.borrowing_line_ids:
                raise exceptions.ValidationError('Vui lòng thêm ít nhất một cuốn sách vào phiếu mượn.')

            # Check if all lines have at least one quant allocated
            lines_without_quants = record.borrowing_line_ids.filtered(
                lambda l: not l.quant_line_ids
            )
            if lines_without_quants:
                book_names = ', '.join(lines_without_quants.mapped('book_id.name'))
                raise exceptions.ValidationError(
                    f'Vui lòng phân bổ bản sao cụ thể cho các sách sau: {book_names}'
                )

            # Mark as posted before (for sequence logic)
            record.posted_before = True

            # Generate access token if not exists (for QR code access)
            if not record.access_token:
                record._generate_access_token()

            # Confirm all quant lines - line and borrowing states will be computed automatically
            for line in record.borrowing_line_ids:
                for quant_line in line.quant_line_ids:
                    if quant_line.state == 'draft':
                        quant_line.action_confirm()

            # Send notification email
            if record.borrower_email:
                self._send_borrowing_email()

    def action_return(self):
        """Trả sách - always show wizard for flexibility"""
        for record in self:
            # Get all quant lines in borrowed/overdue state
            quant_lines_to_return = record.borrowing_line_ids.mapped('quant_line_ids').filtered(
                lambda ql: ql.state in ('borrowed', 'overdue')
            )

            if not quant_lines_to_return:
                raise exceptions.ValidationError('Không có sách nào để trả.')

            # Always show wizard to allow user to select which quants to return
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
            # Mark all borrowed/overdue quant lines as lost
            for line in record.borrowing_line_ids:
                borrowed_quants = line.quant_line_ids.filtered(
                    lambda ql: ql.state in ('borrowed', 'overdue')
                )
                borrowed_quants.action_mark_lost()

    def action_cancel(self):
        """Hủy phiếu mượn"""
        for record in self:
            # Cancel all quant lines
            for line in record.borrowing_line_ids:
                for quant_line in line.quant_line_ids:
                    quant_line.action_cancel()

    def action_set_to_draft(self):
        """Chuyển về nháp"""
        for record in self:
            # Set all quant lines to draft
            for line in record.borrowing_line_ids:
                for quant_line in line.quant_line_ids:
                    if quant_line.state in ('borrowed', 'overdue'):
                        quant_line.quant_id.write({
                            'state': 'available',
                            'current_borrowing_id': False
                        })
                    quant_line.state = 'draft'

    def action_request_extension(self):
        """Request to extend borrowing deadline (one-time only)"""
        self.ensure_one()

        # Validation checks
        if self.state not in ('borrowed', 'overdue'):
            raise exceptions.UserError('Chỉ có thể gia hạn khi đang mượn sách.')

        if self.extension_requested:
            raise exceptions.UserError(
                'Bạn đã yêu cầu gia hạn một lần rồi. Mỗi phiếu mượn chỉ được gia hạn một lần duy nhất.'
            )

        # Check if there are active reservations for any books in this borrowing
        reserved_books = self.env['library.reservation'].search([
            ('book_id', 'in', self.borrowing_line_ids.mapped('book_id').ids),
            ('state', 'in', ['active', 'available'])
        ])

        if reserved_books:
            book_names = ', '.join(reserved_books.mapped('book_id.name')[:3])
            raise exceptions.UserError(
                f'Không thể gia hạn vì có người đang đặt trước các sách: {book_names}...'
            )

        # Get extension days from config
        config = self.env['ir.config_parameter'].sudo()
        extension_days = int(config.get_param('library.extension_days', default=7))

        # Save original due date if not already saved
        if not self.original_due_date:
            self.original_due_date = self.due_date

        # Extend due date
        new_due_date = self.due_date + timedelta(days=extension_days)

        self.write({
            'due_date': new_due_date,
            'extension_requested': True,
            'extension_date': fields.Date.today()
        })

        # Log the extension in chatter
        self.message_post(
            body=f'<p>Người mượn đã yêu cầu gia hạn.</p>'
                 f'<ul>'
                 f'<li>Hạn trả gốc: <strong>{self.original_due_date}</strong></li>'
                 f'<li>Hạn trả mới: <strong>{new_due_date}</strong></li>'
                 f'<li>Gia hạn thêm: <strong>{extension_days} ngày</strong></li>'
                 f'</ul>',
            subject='Yêu cầu gia hạn'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Gia hạn thành công!',
                'message': f'Hạn trả mới của bạn là {new_due_date.strftime("%d/%m/%Y")}',
                'type': 'success',
                'sticky': False,
            }
        }

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
        """Scheduled action to update overdue quant lines"""
        today = fields.Date.today()

        # Update overdue QUANT lines (not book lines)
        QuantLine = self.env['library.borrowing.quant.line']
        overdue_quant_lines = QuantLine.search([
            ('state', '=', 'borrowed'),
            ('due_date', '<', today)
        ])
        overdue_quant_lines.write({'state': 'overdue'})

        # Send overdue notification (borrowing and line states will be computed automatically)
        borrowings_to_notify = overdue_quant_lines.mapped('borrowing_id').filtered(
            lambda b: b.state == 'overdue'
        )
        for borrowing in borrowings_to_notify:
            if borrowing.borrower_email:
                borrowing._send_overdue_email()

    @api.model
    def _cron_send_due_reminders(self):
        """Scheduled action to send due date reminders"""
        config = self.env['ir.config_parameter'].sudo()
        reminder_days = int(config.get_param(
            'library.reminder_days_before', default=2))

        reminder_date = fields.Date.today() + timedelta(days=reminder_days)

        # Find QUANT lines with upcoming due dates
        QuantLine = self.env['library.borrowing.quant.line']
        upcoming_quant_lines = QuantLine.search([
            ('state', '=', 'borrowed'),
            ('due_date', '=', reminder_date)
        ])

        # Send reminders per borrowing (not per quant line)
        borrowings = upcoming_quant_lines.mapped('borrowing_id')
        for borrowing in borrowings:
            if borrowing.borrower_email:
                borrowing._send_due_reminder_email()

    def on_barcode_scanned(self, barcode):
        """
        Handle barcode scanning event - adds quant to borrowing
        Supports two-layer structure: finds or creates book line, then adds quant line
        """
        # Search for quant with matching registration_number
        quant = self.env['library.book.quant'].search([
            ('registration_number', '=', barcode),
            ('state', '=', 'available'),
            ('can_borrow', '=', True)
        ], limit=1)

        if not quant:
            return {
                'warning': {
                    'title': 'Không tìm thấy',
                    'message': f'Không tìm thấy sách có số ĐKCB "{barcode}" hoặc sách không khả dụng để mượn.'
                }
            }

        # Check if quant already exists in current borrowing
        existing_quant_line = self.env['library.borrowing.quant.line'].search([
            ('borrowing_id', '=', self.id),
            ('quant_id', '=', quant.id),
            ('state', '!=', 'cancelled')
        ], limit=1)

        if existing_quant_line:
            return {
                'warning': {
                    'title': 'Đã tồn tại',
                    'message': f'Sách [{quant.registration_number}] "{quant.book_id.name}" đã có trong danh sách.'
                }
            }

        # Calculate default due date
        # Try to get from book's resource, otherwise use system default
        # if quant.book_id.resource_ids:
        #     default_days = quant.book_id.resource_ids[0].default_borrowing_days
        # else:
        config = self.env['ir.config_parameter'].sudo()
        default_days = int(config.get_param('library.default_borrowing_days', default=14))

        due_date = self.borrow_date + timedelta(days=default_days)

        # Find or create book line for this book
        book_line = self.borrowing_line_ids.filtered(
            lambda l: l.book_id.id == quant.book_id.id
        )

        if not book_line:
            # Create new book line
            book_line = self.env['library.borrowing.line'].create({
                'borrowing_id': self.id,
                'book_id': quant.book_id.id,
                'requested_quantity': 1,
                'due_date': due_date,
            })
        else:
            book_line = book_line[0]
            # Increment requested quantity
            book_line.requested_quantity += 1

        # Add quant line under the book line
        self.env['library.borrowing.quant.line'].create({
            'line_id': book_line.id,
            'quant_id': quant.id,
            'due_date': due_date,
            'state': 'draft'
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã thêm [{quant.registration_number}] "{quant.book_id.name}"',
                'type': 'success',
                'sticky': False,
            }
        }
