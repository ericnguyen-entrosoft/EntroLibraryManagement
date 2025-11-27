# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LibraryMediaPlaylist(models.Model):
    _name = 'library.media.playlist'
    _description = 'Danh sách phát phương tiện'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Tên danh sách phát', required=True, tracking=True, index=True)
    sequence = fields.Integer(string='Thứ tự', default=10)

    # Media relationship
    media_ids = fields.Many2many(
        'library.media',
        'library_playlist_media_rel',
        'playlist_id',
        'media_id',
        string='Phương tiện'
    )
    media_count = fields.Integer(string='Số phương tiện', compute='_compute_media_count', store=True)

    # Ownership
    user_id = fields.Many2one(
        'res.users',
        string='Người tạo',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )
    is_public = fields.Boolean(string='Công khai', default=False, tracking=True)

    # Description
    description = fields.Html(string='Mô tả')
    cover_image = fields.Binary(string='Ảnh bìa', attachment=True)

    # Statistics
    total_duration = fields.Integer(
        string='Tổng thời lượng (giây)',
        compute='_compute_total_duration',
        store=True
    )
    total_duration_display = fields.Char(
        string='Tổng thời lượng',
        compute='_compute_total_duration'
    )

    # Status
    active = fields.Boolean(string='Hoạt động', default=True)

    @api.depends('media_ids')
    def _compute_media_count(self):
        for playlist in self:
            playlist.media_count = len(playlist.media_ids)

    @api.depends('media_ids.duration')
    def _compute_total_duration(self):
        for playlist in self:
            total = sum(playlist.media_ids.mapped('duration'))
            playlist.total_duration = total

            if total:
                hours = total // 3600
                minutes = (total % 3600) // 60
                seconds = total % 60

                if hours > 0:
                    playlist.total_duration_display = f"{hours} giờ {minutes} phút"
                else:
                    playlist.total_duration_display = f"{minutes} phút {seconds} giây"
            else:
                playlist.total_duration_display = '0 phút'

    def action_play_all(self):
        """Play all media in playlist"""
        self.ensure_one()
        if not self.media_ids:
            raise exceptions.UserError('Danh sách phát trống.')

        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'library.media',
            'view_mode': 'kanban,list',
            'domain': [('id', 'in', self.media_ids.ids)],
            'context': {'playlist_mode': True, 'playlist_id': self.id}
        }

    def action_view_media(self):
        """View media in playlist"""
        self.ensure_one()
        return {
            'name': f'Phương tiện - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.media',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', self.media_ids.ids)],
            'context': {'default_playlist_ids': [(4, self.id)]}
        }
