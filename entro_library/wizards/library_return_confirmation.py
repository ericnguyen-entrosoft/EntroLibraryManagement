# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class LibraryReturnConfirmationLine(models.TransientModel):
    _name = 'library.return.confirmation.line'
    _description = 'Return Confirmation Line (Quant Level)'

    return_confirmation_id = fields.Many2one('library.return.confirmation', 'Return Confirmation')

    # Reference to quant line (not borrowing line anymore)
    quant_line_id = fields.Many2one(
        'library.borrowing.quant.line',
        string='Quant Line',
        required=True
    )

    # Related fields from quant line
    quant_id = fields.Many2one(
        related='quant_line_id.quant_id',
        string='Bản sao',
        readonly=True
    )
    registration_number = fields.Char(
        related='quant_line_id.registration_number',
        string='Số ĐKCB',
        readonly=True
    )
    book_id = fields.Many2one(
        related='quant_line_id.book_id',
        string='Sách',
        readonly=True
    )
    due_date = fields.Date(
        related='quant_line_id.due_date',
        string='Hạn trả',
        readonly=True
    )
    late_days = fields.Integer(
        related='quant_line_id.late_days',
        string='Số ngày trễ',
        readonly=True
    )
    fine_amount = fields.Float(
        related='quant_line_id.fine_amount',
        string='Tiền phạt',
        readonly=True
    )
    location_id = fields.Many2one(
        related='quant_line_id.location_id',
        string='Vị trí',
        readonly=True
    )
    quant_state = fields.Selection(
        related='quant_line_id.state',
        string='Trạng thái',
        readonly=True
    )

    to_return = fields.Boolean(string='Trả', default=True)


class LibraryReturnConfirmation(models.TransientModel):
    _name = 'library.return.confirmation'
    _description = 'Return Confirmation'

    borrowing_id = fields.Many2one('library.borrowing', 'Borrowing', required=True, readonly=True)
    return_confirmation_line_ids = fields.One2many(
        'library.return.confirmation.line',
        'return_confirmation_id',
        string='Danh sách trả')

    total_fine_amount = fields.Float(
        string='Tổng tiền phạt',
        compute='_compute_total_fine',
        store=False
    )

    @api.depends('return_confirmation_line_ids.fine_amount', 'return_confirmation_line_ids.to_return')
    def _compute_total_fine(self):
        """Calculate total fine for books being returned"""
        for wizard in self:
            lines_to_return = wizard.return_confirmation_line_ids.filtered(lambda l: l.to_return)
            wizard.total_fine_amount = sum(lines_to_return.mapped('fine_amount'))

    @api.model
    def default_get(self, fields_list):
        """Populate wizard with all borrowed/overdue quant lines"""
        res = super(LibraryReturnConfirmation, self).default_get(fields_list)

        borrowing_id = self.env.context.get('default_borrowing_id')
        if borrowing_id and 'return_confirmation_line_ids' in fields_list:
            borrowing = self.env['library.borrowing'].browse(borrowing_id)
            res['borrowing_id'] = borrowing_id

            # Get all QUANT LINES that are borrowed or overdue
            borrowed_quant_lines = self.env['library.borrowing.quant.line'].search([
                ('borrowing_id', '=', borrowing_id),
                ('state', 'in', ('borrowed', 'overdue'))
            ])

            line_vals = []
            for quant_line in borrowed_quant_lines:
                line_vals.append((0, 0, {
                    'quant_line_id': quant_line.id,
                    'to_return': True,  # Default to return all
                }))
            res['return_confirmation_line_ids'] = line_vals

        return res

    def process(self):
        """Process return - return selected quant lines"""
        self.ensure_one()

        borrowing_ids = self.env.context.get('button_validate_borrowing_ids')
        if not borrowing_ids:
            return True

        borrowing = self.env['library.borrowing'].browse(borrowing_ids[0])

        # Separate lines based on to_return flag
        wizard_lines_to_return = self.return_confirmation_line_ids.filtered(lambda l: l.to_return)
        wizard_lines_to_keep = self.return_confirmation_line_ids.filtered(lambda l: not l.to_return)

        if not wizard_lines_to_return:
            raise exceptions.UserError('Vui lòng chọn ít nhất một sách để trả.')

        # Process quant lines marked to return
        for wizard_line in wizard_lines_to_return:
            wizard_line.quant_line_id.action_return()

        # Update borrowing return date if all returned
        all_quant_lines = borrowing.borrowing_line_ids.mapped('quant_line_ids')
        if all(ql.state == 'returned' for ql in all_quant_lines):
            borrowing.return_date = fields.Date.today()

        # Show notification with summary
        returned_count = len(wizard_lines_to_return)
        total_fine = sum(wizard_lines_to_return.mapped('fine_amount'))

        message = f'Đã trả {returned_count} bản sao.'
        if total_fine > 0:
            message += f' Tổng tiền phạt: {total_fine:,.0f} VNĐ.'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Trả sách thành công!',
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }

    def process_return_all(self):
        """Return all books"""
        self.ensure_one()

        # Mark all lines to return
        self.return_confirmation_line_ids.write({'to_return': True})

        # Process return
        return self.process()
