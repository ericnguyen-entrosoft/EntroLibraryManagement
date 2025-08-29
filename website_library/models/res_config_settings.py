# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Library Website Settings
    library_default_borrowing_days = fields.Integer(
        'Default Borrowing Period (Days)',
        default=14,
        config_parameter='website_library.default_borrowing_days',
        help="Default number of days for book borrowing"
    )
    library_max_books_per_user = fields.Integer(
        'Maximum Books per User',
        default=5,
        config_parameter='website_library.max_books_per_user',
        help="Maximum number of books a user can borrow at once"
    )
    library_auto_create_library_card = fields.Boolean(
        'Auto Create Library Card',
        default=True,
        config_parameter='website_library.auto_create_library_card',
        help="Automatically create library card for new portal users"
    )
    library_send_due_date_reminder = fields.Boolean(
        'Send Due Date Reminders',
        default=True,
        config_parameter='website_library.send_due_date_reminder',
        help="Send email reminders before book due date"
    )
    library_reminder_days_before = fields.Integer(
        'Reminder Days Before Due Date',
        default=2,
        config_parameter='website_library.reminder_days_before',
        help="Number of days before due date to send reminder"
    )

    # Website Display Settings
    website_library_ppg = fields.Integer(
        'Books per Page',
        default=20,
        related='website_id.shop_ppg',
        readonly=False,
        help="Number of books displayed per page on website"
    )
    website_library_ppr = fields.Integer(
        'Books per Row',
        default=4,
        related='website_id.shop_ppr',
        readonly=False,
        help="Number of books displayed per row on website"
    )

    @api.onchange('library_auto_create_library_card')
    def _onchange_auto_create_library_card(self):
        if self.library_auto_create_library_card:
            # Enable portal user auto-signup if not already enabled
            self.auth_signup_uninvited = 'b2c'