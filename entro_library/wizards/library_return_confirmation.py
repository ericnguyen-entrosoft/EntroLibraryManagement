# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class LibraryReturnConfirmationLine(models.TransientModel):
    _name = 'library.return.confirmation.line'
    _description = 'Return Confirmation Line'

    return_confirmation_id = fields.Many2one('library.return.confirmation', 'Return Confirmation')
    borrowing_line_id = fields.Many2one('library.borrowing.line', 'Borrowing Line', required=True)
    quant_id = fields.Many2one(related='borrowing_line_id.quant_id', string='Số ĐKCB', readonly=True)
    registration_number = fields.Char(related='quant_id.registration_number')
    book_id = fields.Many2one(related='borrowing_line_id.book_id', string='Sách', readonly=True)
    due_date = fields.Date(related='borrowing_line_id.due_date', string='Hạn trả', readonly=True)
    late_days = fields.Integer(related='borrowing_line_id.late_days', string='Late Days', readonly=True)
    line_state = fields.Selection(related='borrowing_line_id.state', string='State', readonly=True)
    to_return = fields.Boolean(string='Trả', default=True)


class LibraryReturnConfirmation(models.TransientModel):
    _name = 'library.return.confirmation'
    _description = 'Return Confirmation'

    borrowing_id = fields.Many2one('library.borrowing', 'Borrowing', required=True, readonly=True)
    return_confirmation_line_ids = fields.One2many(
        'library.return.confirmation.line',
        'return_confirmation_id',
        string='Return Confirmation Lines')

    @api.model
    def default_get(self, fields_list):
        """Populate wizard with all borrowed/overdue lines"""
        res = super(LibraryReturnConfirmation, self).default_get(fields_list)

        borrowing_id = self.env.context.get('default_borrowing_id')
        if borrowing_id and 'return_confirmation_line_ids' in fields_list:
            borrowing = self.env['library.borrowing'].browse(borrowing_id)
            res['borrowing_id'] = borrowing_id

            # Get all lines that are borrowed or overdue
            borrowed_lines = borrowing.borrowing_line_ids.filtered(
                lambda l: l.state in ('borrowed', 'overdue')
            )

            line_vals = []
            for line in borrowed_lines:
                line_vals.append((0, 0, {
                    'borrowing_line_id': line.id,
                    'to_return': True,  # Default to return all
                }))
            res['return_confirmation_line_ids'] = line_vals

        return res

    def process(self):
        """Process return - create new borrowing for books not marked to return"""
        self.ensure_one()

        borrowing_ids = self.env.context.get('button_validate_borrowing_ids')
        if not borrowing_ids:
            return True

        borrowing = self.env['library.borrowing'].browse(borrowing_ids[0])

        # Separate lines based on to_return flag
        wizard_lines_to_return = self.return_confirmation_line_ids.filtered(lambda l: l.to_return)
        wizard_lines_to_keep = self.return_confirmation_line_ids.filtered(lambda l: not l.to_return)

        # Process lines marked to return
        borrowing.return_date = fields.Date.today()
        for wizard_line in wizard_lines_to_return:
            wizard_line.borrowing_line_id.action_return()

        # Create new borrowing for lines not marked to return
        new_borrowing = False
        if wizard_lines_to_keep:
            lines_to_move = wizard_lines_to_keep.mapped('borrowing_line_id')
            new_borrowing = self._create_new_borrowing(borrowing, lines_to_move)

        # Borrowing state will be computed automatically based on line states

        # Show new borrowing if created
        if new_borrowing:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Phiếu mượn mới',
                'res_model': 'library.borrowing',
                'res_id': new_borrowing.id,
                'view_mode': 'form',
                'target': 'current',
            }

        return {'type': 'ir.actions.act_window_close'}

    def process_cancel_new_borrowing(self):
        """Return all books without creating new borrowing"""
        self.ensure_one()

        borrowing_ids = self.env.context.get('button_validate_borrowing_ids')
        if not borrowing_ids:
            return True

        borrowing = self.env['library.borrowing'].browse(borrowing_ids[0])

        # Return all books
        borrowing.return_date = fields.Date.today()
        unreturned_lines = borrowing.borrowing_line_ids.filtered(
            lambda l: l.state in ('borrowed', 'overdue')
        )
        for line in unreturned_lines:
            line.action_return()

        # Borrowing state will be computed automatically based on line states

        return {'type': 'ir.actions.act_window_close'}

    def _create_new_borrowing(self, old_borrowing, lines_to_keep):
        """Create new borrowing for books still borrowed/overdue"""
        # Create new borrowing with same information
        new_borrowing = self.env['library.borrowing'].create({
            'borrower_id': old_borrowing.borrower_id.id,
            'borrow_date': fields.Date.today(),
            'librarian_id': self.env.user.id,
            'notes': f'Tạo từ phiếu mượn {old_borrowing.name} do trả một phần',
        })

        # Move unreturned lines to new borrowing
        for old_line in lines_to_keep:
            # Store the original state before cancelling
            original_state = old_line.state

            # Update old line to cancelled FIRST to avoid constraint violation
            old_line.state = 'cancelled'

            # Create new line in new borrowing with the original state
            self.env['library.borrowing.line'].create({
                'borrowing_id': new_borrowing.id,
                'quant_id': old_line.quant_id.id,
                'due_date': old_line.due_date,
                'state': original_state if original_state in ('borrowed', 'overdue') else 'borrowed',
            })

            # Update quant to point to new borrowing
            old_line.quant_id.current_borrowing_id = new_borrowing.id

        # New borrowing state will be computed automatically based on line states

        # Add note to old borrowing
        old_borrowing.message_post(
            body=f'Một phần sách được chuyển sang phiếu mượn mới: {new_borrowing.name}'
        )

        # Add note to new borrowing
        new_borrowing.message_post(
            body=f'Phiếu mượn này được tạo từ phiếu mượn {old_borrowing.name}'
        )

        return new_borrowing
