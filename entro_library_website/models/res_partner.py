# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Portal statistics
    borrowing_count = fields.Integer(
        string='Số lần mượn',
        compute='_compute_borrowing_stats',
        help='Tổng số lần mượn sách'
    )
    active_borrowing_count = fields.Integer(
        string='Đang mượn',
        compute='_compute_borrowing_stats',
        help='Số phiếu mượn đang hoạt động'
    )
    reservation_count = fields.Integer(
        string='Đặt trước',
        compute='_compute_borrowing_stats',
        help='Số đặt trước đang chờ'
    )

    def _compute_borrowing_stats(self):
        """Compute borrowing statistics for portal"""
        for partner in self:
            borrowings = self.env['library.borrowing'].search([
                ('borrower_id', '=', partner.id)
            ])
            partner.borrowing_count = len(borrowings)
            partner.active_borrowing_count = len(borrowings.filtered(
                lambda b: b.state in ['draft', 'borrowed']
            ))
            partner.reservation_count = self.env['library.reservation'].search_count([
                ('borrower_id', '=', partner.id),
                ('state', 'in', ['active', 'available'])
            ])
