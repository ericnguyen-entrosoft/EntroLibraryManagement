# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryBookCategory(models.Model):
    _name = 'library.book.category'
    _description = 'Nhóm tài nguyên sách'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh mục', required=True, translate=True, index=True)
    slug = fields.Char(string='Slug', help='URL-friendly name (e.g., phat-hoc)', index=True)
    parent_id = fields.Many2one(
        'library.book.category',
        string='Danh mục cha',
        ondelete='cascade',
        index=True
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('library.book.category', 'parent_id', string='Danh mục con')

    sequence = fields.Integer(string='Thứ tự', default=10)
    color = fields.Integer(string='Màu', default=0)

    # Website Menu
    is_website_menu = fields.Boolean(
        string='Hiển thị trên Website Menu',
        default=False,
        help='Hiển thị danh mục này trên menu website'
    )
    website_menu_type = fields.Selection([
        ('main', 'Menu chính'),
        ('sub', 'Menu con')
    ], string='Loại menu', compute='_compute_website_menu_type', store=True)

    icon = fields.Char(
        string='Icon',
        help='FontAwesome icon class (ví dụ: fa-book, fa-graduation-cap)',
        default='fa-folder'
    )

    # Access Control
    access_level = fields.Selection([
        ('public', 'Công khai'),
        ('members', 'Thành viên'),
        ('restricted', 'Hạn chế')
    ], string='Mức độ truy cập', default='public', required=True,
       help='Kiểm soát ai có thể xem sách trong danh mục này')

    # Book relationship
    book_ids = fields.One2many('library.book', 'book_category_id', string='Sách')
    book_count = fields.Integer(string='Số sách', compute='_compute_book_count', store=True)

    # Description
    description = fields.Text(string='Mô tả')

    # Status
    active = fields.Boolean(string='Hoạt động', default=True)

    # Complete name with hierarchy
    complete_name = fields.Char(
        string='Tên đầy đủ',
        compute='_compute_complete_name',
        store=True,
        recursive=True
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name, parent_id)', 'Tên danh mục phải là duy nhất trong cùng cấp!'),
    ]

    @api.depends('parent_id')
    def _compute_website_menu_type(self):
        """Tự động xác định loại menu dựa trên parent"""
        for category in self:
            if category.parent_id:
                category.website_menu_type = 'sub'
            else:
                category.website_menu_type = 'main'

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name

    @api.depends('book_ids')
    def _compute_book_count(self):
        for category in self:
            category.book_count = len(category.book_ids)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise models.ValidationError('Lỗi! Bạn không thể tạo danh mục đệ quy.')

    def action_view_books(self):
        """View books in this category (including child categories)"""
        self.ensure_one()

        # Get all child categories recursively
        all_category_ids = [self.id]
        if self.child_ids:
            all_category_ids += self.child_ids.ids
            # Recursive search for nested children
            for child in self.child_ids:
                all_category_ids += child.child_ids.ids

        return {
            'name': f'Sách - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'kanban,tree,form',
            'domain': [('book_category_id', 'in', all_category_ids)],
            'context': {'default_book_category_id': self.id}
        }

    def get_website_url(self):
        """Get URL for this category on website"""
        self.ensure_one()
        return f'/thu-vien/{self.slug}' if self.slug else f'/thu-vien?book_category_id={self.id}'
