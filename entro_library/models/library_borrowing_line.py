# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import timedelta


class LibraryBorrowingLine(models.Model):
    _name = 'library.borrowing.line'
    _description = 'Chi tiết mượn sách (cấp sách)'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Thứ tự', default=10)

    # Header link
    borrowing_id = fields.Many2one(
        'library.borrowing',
        string='Phiếu mượn',
        required=True,
        ondelete='cascade',
        index=True
    )
    borrower_id = fields.Many2one(
        related='borrowing_id.borrower_id',
        store=True,
        index=True,
        string='Người mượn'
    )
    borrow_date = fields.Date(
        related='borrowing_id.borrow_date',
        store=True,
        readonly=True,
        string='Ngày mượn'
    )

    # Book demand (no specific quant required at this level)
    book_id = fields.Many2one(
        'library.book',
        string='Sách',
        required=True,
        domain="[('can_borrow', '=', True)]",
        index=True
    )
    book_name = fields.Char(
        related='book_id.name',
        string='Tên sách',
        store=True
    )

    # Quantities (demand vs fulfillment)
    requested_quantity = fields.Integer(
        string='SL yêu cầu',
        default=1,
        required=True,
        help='Số bản sao người dùng muốn mượn'
    )
    fulfilled_quantity = fields.Integer(
        string='Đã cấp',
        compute='_compute_quantities',
        store=True,
        help='Số bản sao đã được phân bổ quant cụ thể'
    )
    borrowed_quantity = fields.Integer(
        string='Đang mượn',
        compute='_compute_quantities',
        store=True
    )
    returned_quantity = fields.Integer(
        string='Đã trả',
        compute='_compute_quantities',
        store=True
    )

    # Dates (default for all quants under this line)
    due_date = fields.Date(
        string='Hạn trả',
        required=True
    )

    # State (computed from quant lines)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('partial', 'Phân bổ 1 phần'),
        ('allocated', 'Đã phân bổ'),
        ('borrowed', 'Đang mượn'),
        ('partial_return', 'Trả 1 phần'),
        ('returned', 'Đã trả'),
        ('overdue', 'Quá hạn'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', compute='_compute_state', store=True, default='draft', required=True)

    # Quant lines (actual fulfillment)
    quant_line_ids = fields.One2many(
        'library.borrowing.quant.line',
        'line_id',
        string='Bản sao cụ thể'
    )

    # Available quants for selection (dynamic domain)
    available_quant_ids = fields.Many2many(
        'library.book.quant',
        string='Bản sao có sẵn',
        compute='_compute_available_quant_ids'
    )

    # Aggregated fields from quant lines
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

    # Additional info
    notes = fields.Text(string='Ghi chú')

    @api.depends('quant_line_ids', 'quant_line_ids.state')
    def _compute_quantities(self):
        """Compute fulfilled, borrowed, and returned quantities from quant lines"""
        for line in self:
            quant_lines = line.quant_line_ids
            line.fulfilled_quantity = len(quant_lines)
            line.borrowed_quantity = len(
                quant_lines.filtered(lambda q: q.state in ('borrowed', 'overdue'))
            )
            line.returned_quantity = len(
                quant_lines.filtered(lambda q: q.state == 'returned')
            )

    @api.depends('quant_line_ids.state', 'requested_quantity', 'fulfilled_quantity')
    def _compute_state(self):
        """Compute line state based on quant line states and quantities"""
        for line in self:
            quant_lines = line.quant_line_ids

            if not quant_lines:
                line.state = 'draft'
            elif line.fulfilled_quantity < line.requested_quantity:
                # Partially allocated
                if any(ql.state in ('borrowed', 'overdue') for ql in quant_lines):
                    line.state = 'borrowed'
                else:
                    line.state = 'partial'
            elif all(ql.state == 'returned' for ql in quant_lines):
                line.state = 'returned'
            elif all(ql.state == 'cancelled' for ql in quant_lines):
                line.state = 'cancelled'
            elif any(ql.state == 'overdue' for ql in quant_lines):
                line.state = 'overdue'
            elif any(ql.state == 'borrowed' for ql in quant_lines):
                if line.returned_quantity > 0:
                    line.state = 'partial_return'
                else:
                    line.state = 'borrowed'
            elif all(ql.state == 'draft' for ql in quant_lines):
                if line.fulfilled_quantity == line.requested_quantity:
                    line.state = 'allocated'
                else:
                    line.state = 'partial'
            else:
                line.state = 'allocated'

    @api.depends('quant_line_ids.late_days', 'quant_line_ids.is_overdue')
    def _compute_late_info(self):
        """Get maximum late days from all quant lines"""
        for line in self:
            if line.quant_line_ids:
                max_late_days = max(line.quant_line_ids.mapped('late_days') or [0])
                line.late_days = max_late_days
                line.is_overdue = any(line.quant_line_ids.mapped('is_overdue'))
            else:
                line.late_days = 0
                line.is_overdue = False

    @api.depends('quant_line_ids.fine_amount')
    def _compute_fine_amount(self):
        """Sum fine amounts from all quant lines"""
        for line in self:
            line.fine_amount = sum(line.quant_line_ids.mapped('fine_amount'))

    @api.depends('book_id')
    def _compute_available_quant_ids(self):
        """Compute available quants for the selected book"""
        for line in self:
            if line.book_id:
                # Find available quants for this book that can be borrowed
                available_quants = self.env['library.book.quant'].search([
                    ('book_id', '=', line.book_id.id),
                    ('state', '=', 'available'),
                    ('can_borrow', '=', True),
                    ('registration_number', '!=', False),
                    ('location_id.is_borrow_location', '=', True)
                ])
                line.available_quant_ids = available_quants
            else:
                line.available_quant_ids = False

    @api.onchange('book_id')
    def _onchange_book_id(self):
        """Clear quant lines when book changes"""
        if self.book_id and self.quant_line_ids:
            # Warn user if changing book with existing quant allocations
            return {
                'warning': {
                    'title': 'Cảnh báo',
                    'message': 'Thay đổi sách sẽ xóa các phân bổ bản sao hiện tại.'
                }
            }

    @api.onchange('requested_quantity')
    def _onchange_requested_quantity(self):
        """Validate requested quantity"""
        if self.requested_quantity < 1:
            self.requested_quantity = 1
            return {
                'warning': {
                    'title': 'Cảnh báo',
                    'message': 'Số lượng yêu cầu phải lớn hơn 0.'
                }
            }

    @api.constrains('requested_quantity')
    def _check_requested_quantity(self):
        """Ensure requested quantity is positive"""
        for line in self:
            if line.requested_quantity < 1:
                raise exceptions.ValidationError('Số lượng yêu cầu phải lớn hơn 0!')

    def action_allocate_quants(self):
        """
        Automatically allocate available quants to fulfill requested quantity
        Similar to stock.move._action_assign()
        """
        self.ensure_one()

        remaining = self.requested_quantity - self.fulfilled_quantity
        if remaining <= 0:
            raise exceptions.UserError('Đã đủ số lượng yêu cầu.')

        # Find available quants
        available_quants = self.env['library.book.quant'].search([
            ('book_id', '=', self.book_id.id),
            ('state', '=', 'available'),
            ('can_borrow', '=', True),
            ('registration_number', '!=', False),
            ('location_id.is_borrow_location', '=', True),
            ('id', 'not in', self.quant_line_ids.mapped('quant_id').ids)
        ], limit=remaining, order='location_id, registration_number')

        if not available_quants:
            raise exceptions.UserError(
                f'Không có bản sao nào khả dụng để phân bổ cho "{self.book_id.name}".'
            )

        # Create quant lines
        created_count = 0
        for quant in available_quants:
            self.env['library.borrowing.quant.line'].create({
                'line_id': self.id,
                'quant_id': quant.id,
                'due_date': self.due_date,
                'state': 'draft'
            })
            created_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã phân bổ {created_count} bản sao.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_clear_quants(self):
        """Remove all draft quant allocations"""
        self.ensure_one()

        draft_quants = self.quant_line_ids.filtered(lambda q: q.state == 'draft')
        if not draft_quants:
            raise exceptions.UserError('Không có bản sao nào ở trạng thái nháp để xóa.')

        count = len(draft_quants)
        draft_quants.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã xóa {count} bản sao.',
                'type': 'info',
                'sticky': False,
            }
        }

    def action_view_quant_lines(self):
        """Open detailed view of quant lines"""
        self.ensure_one()

        return {
            'name': f'Bản sao - {self.book_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing.quant.line',
            'view_mode': 'list,form',
            'domain': [('line_id', '=', self.id)],
            'context': {
                'default_line_id': self.id,
                'default_due_date': self.due_date,
            }
        }

    def action_confirm_all(self):
        """Confirm all quant lines under this book line"""
        for line in self:
            draft_quants = line.quant_line_ids.filtered(lambda q: q.state == 'draft')
            draft_quants.action_confirm()

    def action_return_all(self):
        """Return all borrowed quant lines under this book line"""
        for line in self:
            borrowed_quants = line.quant_line_ids.filtered(
                lambda q: q.state in ('borrowed', 'overdue')
            )
            borrowed_quants.action_return()
