# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Borrower information
    is_borrower = fields.Boolean(string='Là độc giả', default=False)
    borrower_type_id = fields.Many2one('library.borrower.type', string='Loại độc giả')

    borrower_code = fields.Char(string='Mã độc giả', copy=False)
    membership_date = fields.Date(string='Ngày đăng ký')
    membership_expiry = fields.Date(string='Hạn thẻ')
    is_membership_active = fields.Boolean(
        string='Thẻ còn hiệu lực',
        compute='_compute_membership_active',
        store=True
    )

    # Borrowing limits (can override system defaults)
    max_books = fields.Integer(
        string='Số sách tối đa',
        help='Để trống để sử dụng giá trị mặc định của hệ thống'
    )
    max_days = fields.Integer(
        string='Số ngày mượn tối đa',
        help='Để trống để sử dụng giá trị mặc định của hệ thống'
    )

    # Relations
    borrowing_ids = fields.One2many('library.borrowing', 'borrower_id', string='Lịch sử mượn')
    reservation_ids = fields.One2many('library.reservation', 'borrower_id', string='Đặt trước')

    # Statistics
    borrowing_count = fields.Integer(string='Tổng số phiếu mượn', compute='_compute_borrowing_stats', store=True)
    current_borrowing_count = fields.Integer(string='Đang mượn (số sách)', compute='_compute_borrowing_stats', store=True)
    overdue_count = fields.Integer(string='Quá hạn (số sách)', compute='_compute_borrowing_stats', store=True)
    total_fine = fields.Float(string='Tổng tiền phạt', compute='_compute_borrowing_stats', store=True)
    reservation_count = fields.Integer(string='Đang đặt trước', compute='_compute_borrowing_stats', store=True)

    # Notes
    borrower_notes = fields.Text(string='Ghi chú độc giả')

    @api.depends('membership_expiry')
    def _compute_membership_active(self):
        today = fields.Date.today()
        for record in self:
            if record.membership_expiry:
                record.is_membership_active = record.membership_expiry >= today
            else:
                record.is_membership_active = False

    @api.depends('borrowing_ids.state', 'borrowing_ids.fine_amount',
                 'borrowing_ids.borrowing_line_ids.state', 'reservation_ids.state')
    def _compute_borrowing_stats(self):
        for partner in self:
            all_borrowings = partner.borrowing_ids
            partner.borrowing_count = len(all_borrowings)

            # Count books from borrowing lines instead of borrowings
            current_books = 0
            overdue_books = 0
            for borrowing in all_borrowings:
                current_books += len(borrowing.borrowing_line_ids.filtered(
                    lambda l: l.state in ('borrowed', 'overdue')
                ))
                overdue_books += len(borrowing.borrowing_line_ids.filtered(
                    lambda l: l.state == 'overdue'
                ))

            partner.current_borrowing_count = current_books
            partner.overdue_count = overdue_books
            partner.total_fine = sum(all_borrowings.filtered(
                lambda b: b.state in ('borrowed', 'overdue')
            ).mapped('fine_amount'))
            partner.reservation_count = len(partner.reservation_ids.filtered(
                lambda r: r.state in ('active', 'available')
            ))

    def action_view_borrowings(self):
        """View borrower's borrowing history"""
        self.ensure_one()
        return {
            'name': 'Lịch sử mượn sách',
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'view_mode': 'list,form',
            'domain': [('borrower_id', '=', self.id)],
            'context': {'default_borrower_id': self.id}
        }

    def action_view_reservations(self):
        """View borrower's reservations"""
        self.ensure_one()
        return {
            'name': 'Đặt trước',
            'type': 'ir.actions.act_window',
            'res_model': 'library.reservation',
            'view_mode': 'list,form',
            'domain': [('borrower_id', '=', self.id)],
            'context': {'default_borrower_id': self.id}
        }

    @api.model
    def create(self, vals):
        if vals.get('is_borrower') and not vals.get('borrower_code'):
            vals['borrower_code'] = self.env['ir.sequence'].next_by_code('library.borrower') or 'New'
        return super(ResPartner, self).create(vals)

    def write(self, vals):
        if 'is_borrower' in vals and vals['is_borrower']:
            for record in self:
                if not record.borrower_code:
                    vals['borrower_code'] = self.env['ir.sequence'].next_by_code('library.borrower') or 'New'
        return super(ResPartner, self).write(vals)

    def get_or_create_draft_borrowing(self):
        """
        Get or create draft borrowing for this borrower (like shopping cart)
        Returns existing draft borrowing or creates a new one
        """
        self.ensure_one()

        if not self.is_borrower:
            from odoo.exceptions import UserError
            raise UserError('Bạn cần đăng ký làm độc giả để mượn sách.')

        if not self.is_membership_active:
            from odoo.exceptions import UserError
            raise UserError('Thẻ độc giả của bạn đã hết hạn. Vui lòng gia hạn.')

        # Find existing draft borrowing
        draft_borrowing = self.env['library.borrowing'].search([
            ('borrower_id', '=', self.id),
            ('state', '=', 'draft')
        ], order='borrow_date desc', limit=1)

        if not draft_borrowing:
            # Create new draft borrowing
            draft_borrowing = self.env['library.borrowing'].create({
                'borrower_id': self.id,
                'borrow_date': fields.Date.today(),
            })

        return draft_borrowing
