# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    library_card_id = fields.Many2one(
        'library.card',
        string='Library Card',
        help='Library card used for borrowing'
    )
    is_library_borrowing = fields.Boolean(
        string='Is Library Borrowing',
        default=False,
        help='Indicates this is a library book borrowing order'
    )
    borrowing_due_date = fields.Date(
        string='Due Date',
        help='Date when books should be returned'
    )

    @api.model
    def create(self, vals):
        """Override create to set library borrowing flag for website orders"""
        if vals.get('origin') == 'Website Library Borrowing':
            vals['is_library_borrowing'] = True
            # Set due date to 14 days from now
            vals['borrowing_due_date'] = fields.Date.add(fields.Date.today(), days=14)
        return super().create(vals)

    def action_confirm(self):
        """Override confirm to create borrowing deliveries"""
        result = super().action_confirm()
        
        for order in self:
            if order.is_library_borrowing:
                order._create_borrowing_delivery()
        
        return result

    def _create_borrowing_delivery(self):
        """Create delivery picking for book borrowing"""
        self.ensure_one()
        
        if not self.library_card_id:
            raise UserError(_('Library card is required for borrowing'))
        
        # Get borrowing location
        borrowing_location = self.env.ref('library.stock_location_library_borrowing', raise_if_not_found=False)
        if not borrowing_location:
            raise UserError(_('Borrowing location not found'))
        
        # Get warehouse
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not warehouse:
            raise UserError(_('No warehouse found'))
        
        # Create picking for borrowing (outgoing)
        picking_vals = {
            'picking_type_id': warehouse.out_type_id.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': borrowing_location.id,
            'origin': f'Library Borrowing: {self.name}',
            'partner_id': self.partner_id.id,
            'scheduled_date': fields.Datetime.now(),
            'is_library_borrowing': True,
            'library_card_id': self.library_card_id.id,
            'borrowing_due_date': self.borrowing_due_date,
        }
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create stock moves for each order line
        for line in self.order_line:
            if line.product_id.categ_id.book_categ:
                move_vals = {
                    'name': f'Borrow: {line.product_id.name}',
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'picking_id': picking.id,
                    'location_id': warehouse.lot_stock_id.id,
                    'location_dest_id': borrowing_location.id,
                    'sale_line_id': line.id,
                }
                move = self.env['stock.move'].create(move_vals)
                
                # If specific lot/serial is requested, assign it
                if hasattr(line, 'lot_id') and line.lot_id:
                    move_line_vals = {
                        'move_id': move.id,
                        'product_id': line.product_id.id,
                        'lot_id': line.lot_id.id,
                        'quantity': line.product_uom_qty,
                        'product_uom_id': line.product_uom.id,
                        'location_id': warehouse.lot_stock_id.id,
                        'location_dest_id': borrowing_location.id,
                        'picking_id': picking.id,
                    }
                    self.env['stock.move.line'].create(move_line_vals)

    def action_return_books(self):
        """Create return wizard for borrowed books"""
        self.ensure_one()
        
        return {
            'name': _('Return Books'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.return.book.wizard',
            'view_mode': 'form',
            'context': {
                'default_sale_order_id': self.id,
            },
            'target': 'new',
        }

    def action_view_borrowing_pickings(self):
        """View all pickings related to this borrowing order"""
        self.ensure_one()
        
        # Get all pickings (borrowing + returns)
        pickings = self.picking_ids
        return_pickings = self.env['stock.picking'].search([
            ('origin', 'like', f'Return of {self.name}')
        ])
        all_pickings = pickings | return_pickings
        
        action = {
            'name': _('Borrowing Transfers'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', all_pickings.ids)],
        }
        
        if len(all_pickings) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': all_pickings.id,
            })
            
        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number',
        help='Specific book serial number to borrow'
    )