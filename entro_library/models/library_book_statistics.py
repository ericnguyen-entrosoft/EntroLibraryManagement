# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class LibraryBookStatistics(models.Model):
    _name = 'library.book.statistics'
    _description = 'Thống kê sách theo mã'
    _auto = False
    _order = 'code'

    code = fields.Char(string='Mã', readonly=True)
    name = fields.Char(string='Tên sách', readonly=True)
    author_ids = fields.Many2many(
        'library.author',
        string='Tác giả',
        readonly=True,
        compute='_compute_authors'
    )
    author_names = fields.Char(string='Tác giả', readonly=True)
    category_id = fields.Many2one('library.category', string='Nhóm', readonly=True)
    number_available_qty = fields.Integer(string='Số lượng có sẵn', readonly=True)
    number_borrowed_qty = fields.Integer(string='Số lượng đang mượn', readonly=True)
    total_qty = fields.Integer(string='Tổng số lượng', readonly=True)

    def init(self):
        """Create the view - now using library_book_quant for quantities"""
        tools.drop_view_if_exists(self.env.cr, 'library_book_statistics')
        try:
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW library_book_statistics AS (
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY lb.code) as id,
                        lb.code,
                        MAX(lb.name) as name,
                        COALESCE(STRING_AGG(DISTINCT a.name, ', ' ORDER BY a.name), '') as author_names,
                        MAX(lb.category_id) as category_id,
                        COUNT(CASE WHEN lbq.state = 'available' THEN 1 END) as number_available_qty,
                        COUNT(CASE WHEN lbq.state = 'borrowed' THEN 1 END) as number_borrowed_qty,
                        COUNT(lbq.id) as total_qty
                    FROM library_book lb
                    LEFT JOIN library_book_quant lbq ON lb.id = lbq.book_id
                    LEFT JOIN library_book_author_rel lbar ON lb.id = lbar.book_id
                    LEFT JOIN library_author a ON lbar.author_id = a.id
                    WHERE lb.code IS NOT NULL
                    GROUP BY lb.code
                )
            """)
        except Exception:
            # If tables don't exist yet, skip view creation
            # It will be created on next module upgrade
            pass

    @api.depends('code')
    def _compute_authors(self):
        """Compute author_ids from the actual library.book records"""
        for record in self:
            if record.code:
                books = self.env['library.book'].search([('code', '=', record.code)], limit=1)
                if books:
                    record.author_ids = books.author_ids
                else:
                    record.author_ids = False
            else:
                record.author_ids = False

    def action_view_books(self):
        """View books with this code in storage location view"""
        self.ensure_one()
        return {
            'name': 'Vị trí lưu trữ',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'view_id': self.env.ref('entro_library.view_library_storage_location_list').id,
            'domain': [('code', '=', self.code)],
            'context': {'default_code': self.code}
        }
