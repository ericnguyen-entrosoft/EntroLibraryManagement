# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryMenuCategory(models.Model):
    _name = 'library.menu.category'
    _description = 'Danh mục menu thư viện'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh mục', required=True, translate=True)
    complete_name = fields.Char(
        string='Tên đầy đủ',
        compute='_compute_complete_name',
        store=True,
        recursive=True
    )
    parent_id = fields.Many2one(
        'library.menu.category',
        string='Danh mục cha',
        ondelete='cascade',
        index=True
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'library.menu.category',
        'parent_id',
        string='Danh mục con'
    )

    # Menu properties
    url_key = fields.Char(
        string='URL Key',
        required=True,
        help='URL slug cho danh mục này (vd: thien-vipassana, phap-thoai)',
        index=True
    )
    full_url = fields.Char(
        string='URL đầy đủ',
        compute='_compute_full_url',
        store=True,
        recursive=True
    )

    # Display properties
    sequence = fields.Integer(string='Thứ tự', default=10)
    icon = fields.Char(string='Icon CSS', help='Font Awesome icon class (vd: fa-book)')
    description = fields.Text(string='Mô tả')
    banner_image = fields.Binary(
        string='Ảnh banner',
        help='Ảnh nền cho banner trang danh mục (khuyến nghị: 1920x400px)',
        attachment=True
    )

    # Status
    active = fields.Boolean(string='Hoạt động', default=True)

    # Menu type
    menu_type = fields.Selection([
        ('tai_lieu_so', 'Tài liệu số'),
        ('sach', 'Sách'),
        ('other', 'Khác')
    ], string='Loại menu', default='tai_lieu_so', required=True)

    # Statistics
    media_count = fields.Integer(
        string='Số phương tiện',
        compute='_compute_media_count',
        store=False
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f'{category.parent_id.complete_name} / {category.name}'
            else:
                category.complete_name = category.name

    @api.depends('url_key', 'parent_id.full_url')
    def _compute_full_url(self):
        for category in self:
            if category.parent_id:
                category.full_url = f'{category.parent_id.full_url}/{category.url_key}'
            else:
                # Root categories get base URL
                if category.menu_type == 'tai_lieu_so':
                    category.full_url = f'/media/{category.url_key}'
                elif category.menu_type == 'sach':
                    category.full_url = f'/thu-vien/{category.url_key}'
                else:
                    category.full_url = f'/{category.url_key}'

    def _compute_media_count(self):
        for category in self:
            # Get all child categories including this one
            all_category_ids = self.search([
                ('id', 'child_of', category.id)
            ]).ids

            # Count media in this category and all children
            category.media_count = self.env['library.media'].search_count([
                ('menu_category_id', 'in', all_category_ids)
            ])

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise models.ValidationError('Không thể tạo danh mục đệ quy!')

    def name_get(self):
        """Display complete name in many2one fields"""
        result = []
        for category in self:
            result.append((category.id, category.complete_name))
        return result

    def action_view_media(self):
        """View all media in this category and subcategories"""
        self.ensure_one()
        all_category_ids = self.search([
            ('id', 'child_of', self.id)
        ]).ids

        return {
            'name': f'Phương tiện - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.media',
            'view_mode': 'list,form',
            'domain': [('menu_category_id', 'in', all_category_ids)],
            'context': {'default_menu_category_id': self.id}
        }
