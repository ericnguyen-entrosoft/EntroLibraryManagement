# -*- coding: utf-8 -*-

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """Add website_library to frontend translation modules"""
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['website_library']

    def _get_values(self, website=None):
        """Add library-specific values to website context"""
        values = super()._get_values(website)
        
        if request and hasattr(request, 'website') and request.website:
            # Add library-specific website values
            values.update({
                'library_categories': request.env['product.public.category'].search([]),
                'library_authors': request.env['library.author'].search([]),
            })
            
            # Add current user's library information if logged in
            if not request.env.user._is_public():
                values.update({
                    'user_library_card': request.env.user.partner_id.active_library_card,
                    'user_borrowing_count': request.env.user.partner_id.borrowing_count,
                })
        
        return values