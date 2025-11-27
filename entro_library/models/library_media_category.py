# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryMediaCategory(models.Model):
    _name = 'library.media.category'
    _description = 'Danh mục phương tiện'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh mục', required=True, translate=True, index=True)
    parent_id = fields.Many2one(
        'library.media.category',
        string='Danh mục cha',
        ondelete='cascade',
        index=True
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('library.media.category', 'parent_id', string='Danh mục con')

    sequence = fields.Integer(string='Thứ tự', default=10)
    color = fields.Integer(string='Màu', default=0)

    # Media relationship
    media_ids = fields.One2many('library.media', 'category_id', string='Phương tiện')
    media_count = fields.Integer(string='Số phương tiện', compute='_compute_media_count', store=True)

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

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name

    @api.depends('media_ids')
    def _compute_media_count(self):
        for category in self:
            category.media_count = len(category.media_ids)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise models.ValidationError('Lỗi! Bạn không thể tạo danh mục đệ quy.')

    def action_view_media(self):
        """View media in this category"""
        self.ensure_one()
        return {
            'name': f'Phương tiện - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.media',
            'view_mode': 'kanban,list,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id}
        }
