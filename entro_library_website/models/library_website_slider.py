# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryWebsiteSlider(models.Model):
    _name = 'library.website.slider'
    _description = 'Website Hero Slider'
    _order = 'sequence, id'

    name = fields.Char(string='Slide Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    image = fields.Image(string='Slide Image', required=True, max_width=1920, max_height=1080)

    # Text overlay
    title = fields.Char(string='Title', translate=True, help='Main heading on the slide')
    subtitle = fields.Char(string='Subtitle', translate=True, help='Subheading or description')

    # Button (optional)
    button_text = fields.Char(string='Button Text', translate=True)
    button_url = fields.Char(string='Button URL')

    # Display settings
    show_search = fields.Boolean(string='Show Search Bar', default=True)
    text_position = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right')
    ], string='Text Position', default='center')

    overlay_opacity = fields.Float(
        string='Overlay Opacity',
        default=0.3,
        help='Darkness overlay (0.0 = transparent, 1.0 = black)'
    )

    # Status
    active = fields.Boolean(string='Active', default=True)
    is_published = fields.Boolean(string='Published', default=True)
