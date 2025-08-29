# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('product_tmpl_id.website_published')
    def _compute_website_published(self):
        for product in self:
            product.website_published = product.product_tmpl_id.website_published

    website_published = fields.Boolean(
        'Published on Website',
        compute='_compute_website_published',
        store=True,
        readonly=False
    )

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, parent_combination=False, only_template=False):
        """Override to include library-specific information"""
        combination_info = super()._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty,
            pricelist=pricelist, parent_combination=parent_combination, only_template=only_template
        )
        
        if self.categ_id.book_categ:
            combination_info.update({
                'is_book': True,
                'availability': self.availability,
                'available_lots': self.available_lots,
                'total_lots': self.total_lots,
                'isbn': self.isbn,
                'author': self.author.name if self.author else '',
            })
        
        return combination_info

    def website_can_be_displayed(self):
        """Check if book can be displayed on website"""
        return super().website_can_be_displayed() and self.categ_id.book_categ