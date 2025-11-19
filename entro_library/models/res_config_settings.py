# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Borrowing settings
    default_borrowing_days = fields.Integer(
        string='Số ngày mượn mặc định',
        default=14,
        config_parameter='library.default_borrowing_days',
        help='Số ngày mặc định cho một lần mượn sách'
    )

    max_books_per_borrower = fields.Integer(
        string='Số sách tối đa mỗi người',
        default=5,
        config_parameter='library.max_books_per_borrower',
        help='Số lượng sách tối đa một người có thể mượn cùng lúc'
    )

    # Fine settings
    fine_rate_per_day = fields.Float(
        string='Phạt mỗi ngày (VNĐ)',
        default=5000,
        config_parameter='library.fine_rate_per_day',
        help='Số tiền phạt cho mỗi ngày trễ hạn'
    )

    grace_period_days = fields.Integer(
        string='Số ngày ân hạn',
        default=0,
        config_parameter='library.grace_period_days',
        help='Số ngày ân hạn trước khi tính phạt'
    )

    # Notification settings
    reminder_days_before = fields.Integer(
        string='Nhắc nhở trước (ngày)',
        default=2,
        config_parameter='library.reminder_days_before',
        help='Gửi email nhắc nhở bao nhiêu ngày trước khi đến hạn trả'
    )

    enable_email_notifications = fields.Boolean(
        string='Kích hoạt thông báo email',
        default=True,
        config_parameter='library.enable_email_notifications'
    )

    # Reservation settings
    reservation_hold_days = fields.Integer(
        string='Số ngày giữ sách đặt trước',
        default=3,
        config_parameter='library.reservation_hold_days',
        help='Số ngày giữ sách sau khi thông báo có sẵn cho người đặt trước'
    )

    # Membership settings
    default_membership_months = fields.Integer(
        string='Thời hạn thẻ mặc định (tháng)',
        default=12,
        config_parameter='library.default_membership_months',
        help='Thời hạn thẻ độc giả mặc định tính bằng tháng'
    )
