# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = ['product.template', 'website.seo.metadata', 'website.published.multi.mixin']
    _name = 'product.template'

    def can_access_from_current_website(self):
        """Check if book can be accessed from current website"""
        self.ensure_one()
        return self.sale_ok and self.categ_id.book_categ

    @api.model
    def get_available_serials(self):
        """Get available serial numbers for this book"""
        self.ensure_one()
        available_serials = []
        
        for variant in self.product_variant_ids:
            for lot in variant.lot_ids:
                # Check if this serial is available (in stock)
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', variant.id),
                    ('lot_id', '=', lot.id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0)
                ])
                if quants:
                    available_serials.append({
                        'id': lot.id,
                        'name': lot.name,
                        'product_id': variant.id,
                    })
        
        return available_serials

    def action_view_website(self):
        """View book on website"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/library/book/{self.id}',
            'target': 'new',
        }

    def _default_website_meta(self):
        """Set default website meta information"""
        res = super()._default_website_meta()
        if self.description_sale:
            res['default_opengraph']['og:description'] = self.description_sale
            res['default_twitter']['twitter:description'] = self.description_sale
        res['default_opengraph']['og:title'] = self.name
        res['default_twitter']['twitter:title'] = self.name
        if self.image_1920:
            image_url = f'/web/image/product.template/{self.id}/image_1920'
            res['default_opengraph']['og:image'] = image_url
            res['default_twitter']['twitter:image'] = image_url
        return res

    def _compute_website_url(self):
        """Compute website URL for books"""
        for product in self:
            product.website_url = f"/library/book/{product.id}"

    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the book on the website')