# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    library_card_ids = fields.One2many('library.card', 'partner_id', 'Library Cards')
    active_library_card = fields.Many2one(
        'library.card', 
        'Active Library Card',
        compute='_compute_active_library_card',
        help="Current active library card for this user"
    )
    borrowing_order_ids = fields.One2many(
        'sale.order', 
        'partner_id', 
        'Library Borrowing Orders',
        domain=[('is_library_borrowing', '=', True)]
    )
    borrowing_count = fields.Integer(
        'Borrowing Orders Count',
        compute='_compute_borrowing_count'
    )

    @api.depends('library_card_ids.state')
    def _compute_active_library_card(self):
        for partner in self:
            active_card = partner.library_card_ids.filtered(lambda c: c.state == 'running')
            partner.active_library_card = active_card[0] if active_card else False

    @api.depends('borrowing_order_ids')
    def _compute_borrowing_count(self):
        for partner in self:
            partner.borrowing_count = len(partner.borrowing_order_ids)

    def action_view_borrowing_orders(self):
        """View borrowing orders for this partner"""
        action = self.env['ir.actions.act_window']._for_xml_id('website_library.action_library_borrowing_orders')
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.id,
            'default_is_library_borrowing': True,
        }
        return action

    def _get_website_library_domain(self):
        """Domain for website library products"""
        return [
            ('website_published', '=', True),
            ('sale_ok', '=', True),
            ('categ_id.book_categ', '=', True)
        ]