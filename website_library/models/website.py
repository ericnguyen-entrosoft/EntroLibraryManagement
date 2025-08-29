# -*- coding: utf-8 -*-

from odoo import fields, models, api


class Website(models.Model):
    _inherit = 'website'

    def sale_product_domain(self):
        """Override to filter books for library website"""
        domain = super().sale_product_domain()
        # Add filter for book categories only
        domain += [('categ_id.book_categ', '=', True)]
        return domain

    @api.model
    def get_library_categories(self):
        """Get all book categories for website display"""
        return self.env['product.category'].search([
            ('book_categ', '=', True)
        ])

    @api.model
    def get_library_authors(self):
        """Get all authors for website display"""
        return self.env['library.author'].search([])

    def _get_library_statistics(self):
        """Get library statistics for dashboard"""
        stats = {}
        
        # Total books
        stats['total_books'] = self.env['product.template'].search_count([
            ('categ_id.book_categ', '=', True)
        ])
        
        # Available books
        available_books = self.env['product.template'].search([
            ('categ_id.book_categ', '=', True),
            ('availability', '=', 'available')
        ])
        stats['available_books'] = len(available_books)
        
        # Currently borrowed
        borrowed_count = self.env['stock.picking'].search_count([
            ('is_library_borrowing', '=', True),
            ('state', '=', 'done')
        ])
        
        returned_count = self.env['stock.picking'].search_count([
            ('is_book_return', '=', True),
            ('state', '=', 'done')
        ])
        
        stats['currently_borrowed'] = borrowed_count - returned_count
        
        # Popular categories
        popular_categories = self.env['product.category'].search([
            ('book_categ', '=', True)
        ], order='name', limit=5)
        stats['popular_categories'] = popular_categories
        
        return stats