# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import mimetypes
import base64


class LibraryMedia(models.Model):
    _name = 'library.media'
    _description = 'Phương tiện thư viện'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, name'

    name = fields.Char(string='Tiêu đề', required=True, tracking=True, index=True)

    # Media Type and Storage
    media_type = fields.Selection([
        ('video', 'Video'),
        ('audio', 'Âm thanh'),
        ('image', 'Hình ảnh'),
        ('document', 'Tài liệu')
    ], string='Loại phương tiện', required=True, default='video', tracking=True)

    storage_type = fields.Selection([
        ('file', 'Tệp tải lên'),
        ('url', 'Liên kết URL')
    ], string='Loại lưu trữ', required=True, default='file', tracking=True)

    # File Storage
    file = fields.Binary(string='Tệp', attachment=True)
    filename = fields.Char(string='Tên tệp')
    file_size = fields.Float(string='Kích thước (MB)', compute='_compute_file_info', store=True)
    mime_type = fields.Char(string='Định dạng', compute='_compute_file_info', store=True)

    # URL Storage
    file_url = fields.Char(string='Liên kết URL', help='YouTube, Vimeo, hoặc URL trực tiếp')

    # Media Properties
    duration = fields.Integer(string='Thời lượng (giây)', help='Thời lượng cho video/âm thanh')
    duration_display = fields.Char(string='Thời lượng', compute='_compute_duration_display')
    thumbnail = fields.Binary(string='Ảnh thu nhỏ', attachment=True)

    # Relationships
    book_ids = fields.Many2many(
        'library.book',
        'library_media_book_rel',
        'media_id',
        'book_id',
        string='Sách liên quan'
    )
    resource_ids = fields.Many2many(
        'library.resource',
        'library_media_resource_rel',
        'media_id',
        'resource_id',
        string='Tài nguyên'
    )
    category_id = fields.Many2one('library.media.category', string='Danh mục', tracking=True)
    playlist_ids = fields.Many2many(
        'library.media.playlist',
        'library_playlist_media_rel',
        'media_id',
        'playlist_id',
        string='Danh sách phát'
    )

    # Metadata
    description = fields.Html(string='Mô tả')
    keywords = fields.Char(string='Từ khóa', help='Từ khóa để tìm kiếm, cách nhau bởi dấu phẩy')
    author = fields.Char(string='Tác giả/Người tạo')
    language_id = fields.Many2one('res.lang', string='Ngôn ngữ')
    publication_date = fields.Date(string='Ngày xuất bản')

    # Access Control
    access_level = fields.Selection([
        ('public', 'Công khai'),
        ('members', 'Thành viên'),
        ('restricted', 'Hạn chế')
    ], string='Mức độ truy cập', default='public', required=True, tracking=True)

    is_downloadable = fields.Boolean(string='Cho phép tải xuống', default=True)

    # Statistics
    view_count = fields.Integer(string='Lượt xem', default=0, readonly=True)
    download_count = fields.Integer(string='Lượt tải', default=0, readonly=True)

    # Status
    active = fields.Boolean(string='Hoạt động', default=True)

    # Related counts
    book_count = fields.Integer(string='Số sách', compute='_compute_counts', store=True)

    @api.depends('file', 'filename')
    def _compute_file_info(self):
        for media in self:
            if media.file and media.filename:
                try:
                    # Calculate file size in MB
                    file_data = base64.b64decode(media.file)
                    media.file_size = len(file_data) / (1024 * 1024)
                except Exception:
                    media.file_size = 0

                # Detect MIME type
                mime_type, _ = mimetypes.guess_type(media.filename)
                media.mime_type = mime_type or 'application/octet-stream'
            else:
                media.file_size = 0
                media.mime_type = False

    @api.depends('duration')
    def _compute_duration_display(self):
        for media in self:
            if media.duration:
                hours = media.duration // 3600
                minutes = (media.duration % 3600) // 60
                seconds = media.duration % 60

                if hours > 0:
                    media.duration_display = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    media.duration_display = f"{minutes}:{seconds:02d}"
            else:
                media.duration_display = False

    @api.depends('book_ids')
    def _compute_counts(self):
        for media in self:
            media.book_count = len(media.book_ids)

    @api.constrains('storage_type', 'file', 'file_url')
    def _check_storage(self):
        for media in self:
            if media.storage_type == 'file' and not media.file:
                raise exceptions.ValidationError('Vui lòng tải lên tệp hoặc chọn loại lưu trữ URL.')
            if media.storage_type == 'url' and not media.file_url:
                raise exceptions.ValidationError('Vui lòng nhập URL cho phương tiện.')

    @api.onchange('storage_type')
    def _onchange_storage_type(self):
        if self.storage_type == 'file':
            self.file_url = False
        elif self.storage_type == 'url':
            self.file = False
            self.filename = False

    def action_play(self):
        """Open media player"""
        self.ensure_one()
        # Increment view count
        self.view_count += 1

        # Log view if needed
        self.env['library.media.view.log'].create({
            'media_id': self.id,
            'user_id': self.env.user.id,
            'view_date': fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'library.media',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'form_view_initial_mode': 'readonly', 'show_player': True}
        }

    def action_download(self):
        """Download media file"""
        self.ensure_one()
        if not self.is_downloadable:
            raise exceptions.UserError('Phương tiện này không được phép tải xuống.')

        if self.storage_type != 'file' or not self.file:
            raise exceptions.UserError('Không có tệp để tải xuống.')

        # Increment download count
        self.download_count += 1

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/library.media/{self.id}/file/{self.filename}?download=true',
            'target': 'self',
        }

    def action_view_books(self):
        """View related books"""
        self.ensure_one()
        return {
            'name': f'Sách - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.book_ids.ids)],
            'context': {'default_media_ids': [(4, self.id)]}
        }


class LibraryMediaViewLog(models.Model):
    _name = 'library.media.view.log'
    _description = 'Lịch sử xem phương tiện'
    _order = 'view_date desc'

    media_id = fields.Many2one('library.media', string='Phương tiện', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Người dùng', required=True, ondelete='cascade', index=True)
    view_date = fields.Datetime(string='Ngày xem', required=True, default=fields.Datetime.now)
    duration_played = fields.Integer(string='Thời gian xem (giây)')

    # Related fields for reporting
    media_name = fields.Char(related='media_id.name', string='Tên phương tiện', store=True, readonly=True)
    media_type = fields.Selection(related='media_id.media_type', string='Loại', store=True, readonly=True)
    user_name = fields.Char(related='user_id.name', string='Tên người dùng', store=True, readonly=True)
