# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class LibraryResourceRequest(models.Model):
    _name = 'library.resource.request'
    _description = 'Yêu cầu bổ sung tài liệu thư viện'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # === THÔNG TIN CƠ BẢN ===
    name = fields.Char(
        string='Số yêu cầu',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    request_type = fields.Selection([
        ('book', 'Tài nguyên sách'),
        ('digital', 'Tài nguyên số')
    ], string='Loại tài nguyên', required=True, default='book', tracking=True)

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã gửi'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
        ('done', 'Hoàn thành')
    ], string='Trạng thái', default='draft', required=True, tracking=True)

    # === NGƯỜI YÊU CẦU ===
    requester_id = fields.Many2one(
        'res.partner',
        string='Người yêu cầu',
        required=True,
        default=lambda self: self.env.user.partner_id,
        tracking=True
    )

    # === THÔNG TIN TÀI LIỆU ===
    title = fields.Char(
        string='Tên tài liệu',
        required=True,
        tracking=True
    )

    author = fields.Char(
        string='Tác giả',
        tracking=True
    )

    publisher = fields.Char(
        string='Nhà xuất bản'
    )

    publication_year = fields.Integer(
        string='Năm xuất bản'
    )

    description = fields.Text(
        string='Mô tả',
        required=True
    )

    reason = fields.Text(
        string='Lý do đề xuất',
        help='Vì sao tài liệu này nên được bổ sung vào thư viện?'
    )

    # === CHO TÀI NGUYÊN SỐ ===
    format_type = fields.Selection([
        ('pdf', 'PDF'),
        ('ebook', 'E-Book'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Khác')
    ], string='Định dạng')

    resource_url = fields.Char(
        string='Link tài nguyên',
        help='Link đến video, PDF, hoặc tài nguyên số khác'
    )

    # === FILE ĐÍNH KÈM (CHỈ CHO SÁCH) ===
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'library_request_attachment_rel',
        'request_id',
        'attachment_id',
        string='File đính kèm'
    )

    cover_image = fields.Binary(
        string='Ảnh bìa'
    )

    # === CHO SÁCH ===
    isbn = fields.Char(string='ISBN')

    # === XỬ LÝ & PHÊ DUYỆT ===
    reviewer_id = fields.Many2one(
        'res.users',
        string='Người xét duyệt',
        tracking=True
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        readonly=True,
        tracking=True
    )

    approval_date = fields.Date(
        string='Ngày phê duyệt',
        readonly=True
    )

    rejection_reason = fields.Text(
        string='Lý do từ chối',
        tracking=True
    )

    # === TÀI NGUYÊN ĐÃ TẠO ===
    created_book_id = fields.Many2one(
        'library.book',
        string='Sách đã tạo',
        readonly=True
    )

    created_digital_resource_id = fields.Many2one(
        'library.media',
        string='Tài nguyên số đã tạo',
        readonly=True
    )

    notes = fields.Text(string='Ghi chú')

    submitted_date = fields.Datetime(
        string='Ngày gửi',
        readonly=True
    )

    # === CREATE & CONSTRAINTS ===
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'library.resource.request'
            ) or 'New'
        return super().create(vals)

    @api.constrains('request_type', 'resource_url')
    def _check_digital_resource_url(self):
        """Tài nguyên số bắt buộc phải có link"""
        for record in self:
            if record.request_type == 'digital' and not record.resource_url:
                raise ValidationError('Tài nguyên số phải có link tài nguyên!')

    @api.onchange('request_type')
    def _onchange_request_type(self):
        """Xóa các trường không liên quan khi đổi loại"""
        if self.request_type == 'book':
            self.format_type = False
            self.resource_url = False
        elif self.request_type == 'digital':
            self.isbn = False
            self.attachment_ids = [(5, 0, 0)]  # Xóa tất cả attachments

    # === WORKFLOW ACTIONS ===
    def action_submit(self):
        """Người dùng gửi yêu cầu"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Chỉ có thể gửi yêu cầu ở trạng thái Nháp')

        self.write({
            'state': 'submitted',
            'submitted_date': fields.Datetime.now()
        })

        # Gửi thông báo cho quản lý
        self._notify_managers()
        return True

    def action_approve(self):
        """Phê duyệt yêu cầu"""
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError('Chỉ có thể phê duyệt yêu cầu đã gửi')

        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Date.today()
        })

        # Tạo tài nguyên
        self._create_resource()

        # Gửi email thông báo
        self._send_approval_email()
        return True

    def action_reject(self):
        """Mở wizard từ chối"""
        self.ensure_one()
        return {
            'name': 'Từ chối yêu cầu',
            'type': 'ir.actions.act_window',
            'res_model': 'library.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def do_reject(self, reason):
        """Thực hiện từ chối"""
        self.ensure_one()
        self.write({
            'state': 'rejected',
            'rejection_reason': reason
        })
        self._send_rejection_email()
        return True

    def action_reset_to_draft(self):
        """Đưa về nháp"""
        self.ensure_one()
        self.write({'state': 'draft'})
        return True

    def _create_resource(self):
        """Tạo tài nguyên thực tế"""
        self.ensure_one()

        if self.request_type == 'book':
            book_vals = {
                'name': self.title,
                'author_names': self.author,
                'publisher': self.publisher,
                'isbn': self.isbn,
                'publication_year': self.publication_year,
                'summary': self.description,
                'notes': 'Được tạo từ yêu cầu: %s' % self.name,
            }
            book = self.env['library.book'].create(book_vals)

            self.write({
                'created_book_id': book.id,
                'state': 'done'
            })

        elif self.request_type == 'digital':
            digital_vals = {
                'name': self.title,
                'author': self.author,
                'media_type': self.format_type or 'video',
                'storage_type': 'url',
                'file_url': self.resource_url,
                'description': self.description,
                'notes': 'Được tạo từ yêu cầu: %s' % self.name,
            }
            digital = self.env['library.media'].create(digital_vals)

            self.write({
                'created_digital_resource_id': digital.id,
                'state': 'done'
            })

    def _notify_managers(self):
        """Thông báo cho quản lý"""
        # TODO: Implement email notification
        pass

    def _send_approval_email(self):
        """Gửi email phê duyệt"""
        # TODO: Implement email
        pass

    def _send_rejection_email(self):
        """Gửi email từ chối"""
        # TODO: Implement email
        pass

    def action_view_created_resource(self):
        """Xem tài nguyên đã tạo"""
        self.ensure_one()

        if self.created_book_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'library.book',
                'res_id': self.created_book_id.id,
                'view_mode': 'form',
            }
        elif self.created_digital_resource_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'library.media',
                'res_id': self.created_digital_resource_id.id,
                'view_mode': 'form',
            }
