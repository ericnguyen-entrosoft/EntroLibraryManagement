# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryResource(models.Model):
    _name = 'library.resource'
    _description = 'Kho tài nguyên thư viện'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Tên kho tài nguyên', required=True, tracking=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    code = fields.Char(string='Mã', required=True, copy=False, tracking=True)

    # Policy and description
    description = fields.Html(string='Mô tả')
    policy = fields.Html(string='Chính sách', help='Chính sách sử dụng tài nguyên này')

    # Borrowing limits
    max_books_per_borrower = fields.Integer(
        string='Số sách tối đa mỗi người mượn',
        default=3,
        help='Giới hạn số lượng sách từ tài nguyên này mà một người có thể mượn cùng lúc. '
             'Ví dụ: Sách quý hiếm = 1, Sách thông thường = 5'
    )
    default_borrowing_days = fields.Integer(
        string='Số ngày mượn mặc định',
        default=14,
        help='Số ngày mượn mặc định cho sách trong tài nguyên này'
    )
    allow_borrowing = fields.Boolean(
        string='Cho phép mượn về',
        default=True,
        help='Tài nguyên này có cho phép mượn sách về nhà không. '
             'Ví dụ: Tài liệu tham khảo chỉ đọc tại chỗ = False'
    )

    # Icon/Color for UI
    color = fields.Integer(string='Màu', default=0)
    icon = fields.Char(string='Icon', default='fa-book', help='Font Awesome icon class')

    # Book assignments
    book_ids = fields.Many2many(
        'library.book',
        'library_resource_book_rel',
        'resource_id',
        'book_id',
        string='Sách'
    )
    book_count = fields.Integer(
        string='Số lượng sách',
        compute='_compute_book_count',
        store=True
    )

    # Statistics
    available_book_count = fields.Integer(
        string='Sách có sẵn',
        compute='_compute_statistics'
    )
    borrowed_book_count = fields.Integer(
        string='Đang mượn',
        compute='_compute_statistics'
    )

    # Status
    active = fields.Boolean(string='Hoạt động', default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Mã kho tài nguyên phải là duy nhất!'),
    ]

    @api.depends('book_ids')
    def _compute_book_count(self):
        for resource in self:
            resource.book_count = len(resource.book_ids)

    @api.depends('book_ids', 'book_ids.available_quant_count', 'book_ids.borrowed_quant_count')
    def _compute_statistics(self):
        for resource in self:
            resource.available_book_count = sum(resource.book_ids.mapped('available_quant_count') or [0])
            resource.borrowed_book_count = sum(resource.book_ids.mapped('borrowed_quant_count') or [0])

    def action_view_books(self):
        """View books assigned to this resource"""
        self.ensure_one()
        return {
            'name': f'Sách - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.book_ids.ids)],
            'context': {
                'default_resource_ids': [(4, self.id)],
            }
        }

    def check_borrowing_limit(self, borrower_id, book_id=None, exclude_borrowing_id=None):
        """
        Check if borrower can borrow from this resource
        Returns: (can_borrow: bool, message: str, current_count: int)
        """
        self.ensure_one()

        # Check if resource allows borrowing
        if not self.allow_borrowing:
            return False, f'Tài nguyên "{self.name}" không cho phép mượn về nhà.', 0

        # Count current borrowed books from this resource by the borrower
        BorrowingLine = self.env['library.borrowing.line']

        # Build domain to find active borrowing lines from this resource
        domain = [
            ('borrower_id', '=', borrower_id),
            ('state', 'in', ('draft', 'borrowed', 'overdue')),
            ('quant_line_ids.quant_id.location_id.resource_id', '=', self.id)
        ]

        if exclude_borrowing_id:
            domain.append(('borrowing_id', '!=', exclude_borrowing_id))

        current_borrowed_lines = BorrowingLine.search(domain)
        current_count = len(current_borrowed_lines)

        # Check if adding this book would exceed limit
        if book_id:
            # If adding a new book, check if it's from this resource
            book = self.env['library.book'].browse(book_id)
            if self.id in book.resource_ids.ids:
                # Would be adding one more book from this resource
                if current_count >= self.max_books_per_borrower:
                    return False, (
                        f'Bạn đã đạt giới hạn {self.max_books_per_borrower} quyển sách '
                        f'từ tài nguyên "{self.name}". Hiện tại: {current_count} quyển.'
                    ), current_count

        return True, '', current_count

    def get_borrower_stats(self, borrower_id):
        """Get borrowing statistics for a borrower in this resource"""
        self.ensure_one()

        can_borrow, message, current_count = self.check_borrowing_limit(borrower_id)

        return {
            'resource_id': self.id,
            'resource_name': self.name,
            'max_books': self.max_books_per_borrower,
            'current_books': current_count,
            'remaining_slots': max(0, self.max_books_per_borrower - current_count),
            'can_borrow': can_borrow,
            'message': message,
            'allow_borrowing': self.allow_borrowing,
        }
