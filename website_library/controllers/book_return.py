# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError


class LibraryBookReturn(http.Controller):
    
    @http.route(['/library/my-books'], type='http', auth="user", website=True)
    def my_borrowed_books(self, **post):
        """Display user's currently borrowed books"""
        partner = request.env.user.partner_id
        
        # Get current borrowing orders (confirmed sales orders with deliveries)
        borrowed_orders = request.env['sale.order'].search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
            ('origin', 'like', 'Website Library Borrowing')
        ])
        
        # Filter orders that have active borrowings (delivered but not returned)
        active_borrowings = []
        for order in borrowed_orders:
            # Check if there are deliveries that haven't been returned
            delivered_pickings = order.picking_ids.filtered(
                lambda p: p.state == 'done' and p.picking_type_id.code == 'outgoing'
            )
            returned_pickings = request.env['stock.picking'].search([
                ('origin', 'like', f'Return of {order.name}'),
                ('state', '=', 'done')
            ])
            
            # If delivered but not fully returned
            if delivered_pickings and len(delivered_pickings) > len(returned_pickings):
                active_borrowings.append(order)
        
        values = {
            'borrowed_orders': active_borrowings,
            'partner': partner,
        }
        return request.render("website_library.my_borrowed_books", values)
    
    @http.route(['/library/return-info'], type='http', auth="public", website=True)
    def return_info(self, **post):
        """Display information about book return locations and process"""
        # Get return locations from stock locations
        return_locations = request.env['stock.location'].search([
            ('name', 'ilike', 'return'),
            ('usage', '=', 'internal')
        ])
        
        values = {
            'return_locations': return_locations,
        }
        return request.render("website_library.return_info", values)