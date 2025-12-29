# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MediaVipassanaCategory(models.Model):
    _name = 'media.vipassana.category'
    _description = 'Danh mục Thiền Vipassana'
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh mục', required=True, translate=True, index=True)
    description = fields.Text(string='Mô tả')
    sequence = fields.Integer(string='Thứ tự', default=10)
    active = fields.Boolean(string='Hoạt động', default=True)
    color = fields.Integer(string='Màu', default=0)

    # Relationship with media
    media_ids = fields.Many2many(
        'library.media',
        'library_media_vipassana_category_rel',
        'category_id',
        'media_id',
        string='Phương tiện'
    )
    media_count = fields.Integer(string='Số phương tiện', compute='_compute_media_count', store=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Tên danh mục phải là duy nhất!'),
    ]

    @api.depends('media_ids')
    def _compute_media_count(self):
        for category in self:
            category.media_count = len(category.media_ids)

    def action_view_media(self):
        """View media in this category"""
        self.ensure_one()
        return {
            'name': f'Phương tiện - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.media',
            'view_mode': 'kanban,list,form',
            'domain': [('vipassana_category_ids', 'in', self.id)],
            'context': {'default_vipassana_category_ids': [(4, self.id)]}
        }
