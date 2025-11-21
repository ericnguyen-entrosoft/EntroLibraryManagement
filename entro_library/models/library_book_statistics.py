# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class LibraryBookStatistics(models.Model):
    _name = 'library.book.statistics'
    _description = 'Thống kê sách'
    _auto = False
    _order = 'name'

    book_id = fields.Many2one('library.book', string='Sách', readonly=True)
    name = fields.Char(string='Tên sách', readonly=True)
    author_ids = fields.Many2many(
        'library.author',
        string='Tác giả',
        readonly=True,
        compute='_compute_authors'
    )
    author_names = fields.Char(string='Tác giả', readonly=True)
    category_id = fields.Many2one('library.category', string='Nhóm', readonly=True)
    number_available_qty = fields.Integer(string='Có sẵn', readonly=True)
    number_borrowed_qty = fields.Integer(string='Đang mượn', readonly=True)
    total_qty = fields.Integer(string='Tổng', readonly=True)

    def init(self):
        """Create the view - now using library_book_quant for quantities"""
        tools.drop_view_if_exists(self.env.cr, 'library_book_statistics')
        try:
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW library_book_statistics AS (
                    SELECT
                        lb.id,
                        lb.id as book_id,
                        lb.name,
                        COALESCE(STRING_AGG(DISTINCT a.name, ', ' ORDER BY a.name), '') as author_names,
                        lb.category_id,
                        COUNT(CASE WHEN lbq.state = 'available' THEN 1 END) as number_available_qty,
                        COUNT(CASE WHEN lbq.state = 'borrowed' THEN 1 END) as number_borrowed_qty,
                        COUNT(lbq.id) as total_qty
                    FROM library_book lb
                    LEFT JOIN library_book_quant lbq ON lb.id = lbq.book_id
                    LEFT JOIN library_book_author_rel lbar ON lb.id = lbar.book_id
                    LEFT JOIN library_author a ON lbar.author_id = a.id
                    GROUP BY lb.id, lb.name, lb.category_id
                )
            """)
        except Exception:
            # If tables don't exist yet, skip view creation
            # It will be created on next module upgrade
            pass

    @api.depends('book_id')
    def _compute_authors(self):
        """Compute author_ids from the actual library.book records"""
        for record in self:
            if record.book_id:
                record.author_ids = record.book_id.author_ids
            else:
                record.author_ids = False

    def action_view_books(self):
        """View book details"""
        self.ensure_one()
        return {
            'name': 'Chi tiết sách',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'form',
            'res_id': self.book_id.id,
        }
