# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class LibraryReturnBookWizard(models.TransientModel):
    _name = 'library.return.book.wizard'
    _description = 'Return Borrowed Books Wizard'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Borrowing Order',
        required=True,
        help='The original borrowing order'
    )
    picking_ids = fields.Many2many(
        'stock.picking',
        string='Borrowing Transfers',
        help='Available borrowing transfers to return'
    )
    return_line_ids = fields.One2many(
        'library.return.book.line',
        'wizard_id',
        string='Books to Return'
    )
    return_location_id = fields.Many2one(
        'stock.location',
        string='Return Location',
        domain=[('usage', '=', 'internal')],
        help='Location where books will be returned'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes for the return'
    )

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        result = super().default_get(fields_list)
        
        if 'sale_order_id' in result:
            order = self.env['sale.order'].browse(result['sale_order_id'])
            
            # Get borrowing pickings that are done but not returned
            borrowing_pickings = order.picking_ids.filtered(
                lambda p: p.is_library_borrowing and p.state == 'done'
            )
            
            # Check which ones don't have returns yet
            available_pickings = []
            for picking in borrowing_pickings:
                existing_return = self.env['stock.picking'].search([
                    ('origin', '=', f'Return of {picking.name}')
                ])
                if not existing_return:
                    available_pickings.append(picking.id)
            
            result['picking_ids'] = [(6, 0, available_pickings)]
            
            # Get default return location
            return_location = self.env.ref('library.stock_location_library_returns', raise_if_not_found=False)
            if return_location:
                result['return_location_id'] = return_location.id
        
        return result

    @api.onchange('picking_ids')
    def _onchange_picking_ids(self):
        """Update return lines based on selected pickings"""
        lines = []
        for picking in self.picking_ids:
            for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
                for move_line in move.move_line_ids:
                    lines.append((0, 0, {
                        'picking_id': picking.id,
                        'move_id': move.id,
                        'move_line_id': move_line.id,
                        'product_id': move_line.product_id.id,
                        'lot_id': move_line.lot_id.id,
                        'quantity': move_line.quantity,
                        'to_return': True,
                    }))
        self.return_line_ids = lines

    def create_return_picking(self):
        """Create return picking for selected books"""
        if not self.return_line_ids.filtered('to_return'):
            raise ValidationError(_('Please select at least one book to return.'))
        
        if not self.return_location_id:
            raise ValidationError(_('Please select a return location.'))
        
        # Group by original picking
        pickings_to_return = {}
        for line in self.return_line_ids.filtered('to_return'):
            if line.picking_id not in pickings_to_return:
                pickings_to_return[line.picking_id] = []
            pickings_to_return[line.picking_id].append(line)
        
        created_pickings = []
        
        for original_picking, lines in pickings_to_return.items():
            # Check if return already exists
            existing_return = self.env['stock.picking'].search([
                ('origin', '=', f'Return of {original_picking.name}')
            ])
            if existing_return:
                continue
            
            # Create return picking
            return_picking_vals = {
                'picking_type_id': original_picking.picking_type_id.return_picking_type_id.id or original_picking.picking_type_id.id,
                'location_id': original_picking.location_dest_id.id,
                'location_dest_id': self.return_location_id.id,
                'origin': f'Return of {original_picking.name}',
                'partner_id': original_picking.partner_id.id,
                'scheduled_date': fields.Datetime.now(),
                'is_book_return': True,
                'library_card_id': original_picking.library_card_id.id,
                'return_location_info': self.return_location_id.name,
                'note': self.notes,
            }
            return_picking = self.env['stock.picking'].create(return_picking_vals)
            created_pickings.append(return_picking)
            
            # Group lines by product and lot
            moves_to_create = {}
            for line in lines:
                key = (line.product_id.id, line.lot_id.id if line.lot_id else False)
                if key not in moves_to_create:
                    moves_to_create[key] = {
                        'product_id': line.product_id,
                        'lot_id': line.lot_id,
                        'quantity': 0,
                        'lines': []
                    }
                moves_to_create[key]['quantity'] += line.quantity
                moves_to_create[key]['lines'].append(line)
            
            # Create return moves
            for (product_id, lot_id), move_data in moves_to_create.items():
                return_move_vals = {
                    'name': f'Return: {move_data["product_id"].name}',
                    'product_id': product_id,
                    'product_uom_qty': move_data['quantity'],
                    'product_uom': move_data['product_id'].uom_id.id,
                    'picking_id': return_picking.id,
                    'location_id': original_picking.location_dest_id.id,
                    'location_dest_id': self.return_location_id.id,
                }
                return_move = self.env['stock.move'].create(return_move_vals)
                
                # Create move line
                return_move_line_vals = {
                    'move_id': return_move.id,
                    'product_id': product_id,
                    'lot_id': lot_id,
                    'quantity': move_data['quantity'],
                    'product_uom_id': move_data['product_id'].uom_id.id,
                    'location_id': original_picking.location_dest_id.id,
                    'location_dest_id': self.return_location_id.id,
                    'picking_id': return_picking.id,
                }
                self.env['stock.move.line'].create(return_move_line_vals)
        
        if not created_pickings:
            raise ValidationError(_('No return transfers were created. Returns may already exist.'))
        
        # Return action to view created pickings
        if len(created_pickings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': created_pickings[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', [p.id for p in created_pickings])],
                'target': 'current',
            }


class LibraryReturnBookLine(models.TransientModel):
    _name = 'library.return.book.line'
    _description = 'Return Book Line'

    wizard_id = fields.Many2one(
        'library.return.book.wizard',
        string='Wizard',
        required=True
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Original Picking',
        required=True
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Original Move',
        required=True
    )
    move_line_id = fields.Many2one(
        'stock.move.line',
        string='Original Move Line',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Book',
        required=True
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number'
    )
    quantity = fields.Float(
        string='Quantity',
        required=True
    )
    to_return = fields.Boolean(
        string='Return',
        default=True,
        help='Check to include this book in the return'
    )