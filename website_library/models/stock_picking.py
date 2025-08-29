# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_library_borrowing = fields.Boolean(
        string='Is Library Borrowing',
        default=False,
        help='Indicates this is a library borrowing transfer'
    )
    library_card_id = fields.Many2one(
        'library.card',
        string='Library Card',
        help='Library card used for borrowing'
    )
    borrowing_due_date = fields.Date(
        string='Due Date',
        help='Date when books should be returned'
    )
    is_book_return = fields.Boolean(
        string='Is Book Return',
        default=False,
        help='Indicates this is a book return transfer'
    )
    return_location_info = fields.Text(
        string='Return Location Info',
        help='Information about where to return the books'
    )

    def button_validate(self):
        """Override validate to handle library-specific logic"""
        result = super().button_validate()
        
        for picking in self:
            if picking.is_library_borrowing and picking.state == 'done':
                # Update library card with borrowing info
                if picking.library_card_id:
                    picking.library_card_id._update_borrowing_count()
                
                # Send borrowing confirmation email
                picking._send_borrowing_confirmation()
            
            elif picking.is_book_return and picking.state == 'done':
                # Send return confirmation email
                picking._send_return_confirmation()
        
        return result

    def _send_borrowing_confirmation(self):
        """Send email confirmation for book borrowing"""
        self.ensure_one()
        template = self.env.ref('website_library.email_template_book_borrowed', raise_if_not_found=False)
        if template and self.partner_id.email:
            template.send_mail(self.id, force_send=True)

    def _send_return_confirmation(self):
        """Send email confirmation for book return"""
        self.ensure_one()
        template = self.env.ref('website_library.email_template_book_returned', raise_if_not_found=False)
        if template and self.partner_id.email:
            template.send_mail(self.id, force_send=True)

    def action_create_return_picking(self):
        """Create return picking for borrowed books"""
        self.ensure_one()
        
        if not self.is_library_borrowing or self.state != 'done':
            return False
        
        # Check if return already exists
        existing_return = self.env['stock.picking'].search([
            ('origin', '=', f'Return of {self.name}')
        ])
        if existing_return:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': existing_return[0].id,
                'view_mode': 'form',
            }
        
        # Get return location
        return_location = self.env.ref('library.stock_location_library_returns', raise_if_not_found=False)
        if not return_location:
            return_location = self.location_id  # Default to original location
        
        # Create return picking
        return_picking_vals = {
            'picking_type_id': self.picking_type_id.return_picking_type_id.id or self.picking_type_id.id,
            'location_id': self.location_dest_id.id,  # From borrowing location
            'location_dest_id': return_location.id,   # To return location
            'origin': f'Return of {self.name}',
            'partner_id': self.partner_id.id,
            'scheduled_date': fields.Datetime.now(),
            'is_book_return': True,
            'library_card_id': self.library_card_id.id,
            'return_location_info': return_location.name if return_location else '',
        }
        return_picking = self.env['stock.picking'].create(return_picking_vals)
        
        # Create return moves for each borrowed book
        for move in self.move_ids:
            if move.state == 'done':
                return_move_vals = {
                    'name': f'Return: {move.product_id.name}',
                    'product_id': move.product_id.id,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.id,
                    'picking_id': return_picking.id,
                    'location_id': self.location_dest_id.id,
                    'location_dest_id': return_location.id,
                    'origin_returned_move_id': move.id,
                }
                return_move = self.env['stock.move'].create(return_move_vals)
                
                # Copy move lines with lots/serials
                for move_line in move.move_line_ids:
                    return_move_line_vals = {
                        'move_id': return_move.id,
                        'product_id': move_line.product_id.id,
                        'lot_id': move_line.lot_id.id,
                        'quantity': move_line.quantity,
                        'product_uom_id': move_line.product_uom_id.id,
                        'location_id': self.location_dest_id.id,
                        'location_dest_id': return_location.id,
                        'picking_id': return_picking.id,
                    }
                    self.env['stock.move.line'].create(return_move_line_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': return_picking.id,
            'view_mode': 'form',
        }