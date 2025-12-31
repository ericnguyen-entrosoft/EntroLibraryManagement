# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class LibrarySignupRequest(models.Model):
    _name = 'library.signup.request'
    _description = 'Library Signup Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Mã đăng ký', required=True, copy=False, readonly=True, default='New')

    # Personal Information
    full_name = fields.Char(string='Họ và tên', required=True, tracking=True)
    dharma_name = fields.Char(string='Pháp Danh', tracking=True)
    email = fields.Char(string='Email', required=True, tracking=True)
    phone = fields.Char(string='Số điện thoại', required=True, tracking=True)
    date_of_birth = fields.Date(string='Ngày sinh', tracking=True)
    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('other', 'Khác')
    ], string='Giới tính', tracking=True)

    # Address
    street = fields.Char(string='Địa chỉ')
    street2 = fields.Char(string='Địa chỉ 2')
    city = fields.Char(string='Thành phố')
    state_id = fields.Many2one('res.country.state', string='Tỉnh/Thành')
    zip = fields.Char(string='Mã bưu điện')
    country_id = fields.Many2one('res.country', string='Quốc gia', default=lambda self: self.env.ref('base.vn'))

    # Identification
    id_card_number = fields.Char(string='CMND/CCCD', tracking=True)
    student_id = fields.Char(string='Mã sinh viên/học sinh', tracking=True)

    # Borrower Type
    borrower_type_id = fields.Many2one(
        'library.borrower.type',
        string='Loại độc giả',
        required=True,
        tracking=True,
        help='Chọn loại độc giả phù hợp'
    )

    # Additional Info
    organization = fields.Char(string='Đơn vị/Trường học')
    vipassana_attended = fields.Boolean(
        string='Đã tham gia khóa thiền Vipassana tại TVPS',
        default=False,
        tracking=True,
        help='Đánh dấu nếu người đăng ký đã tham gia khóa thiền Vipassana tại TVPS'
    )
    notes = fields.Text(string='Ghi chú')

    # Status
    state = fields.Selection([
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái', default='pending', required=True, tracking=True)

    rejection_reason = fields.Text(string='Lý do từ chối', tracking=True)

    # Related records
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True, tracking=True)
    user_id = fields.Many2one('res.users', string='User Account', readonly=True, tracking=True)

    # Approval info
    approved_by = fields.Many2one('res.users', string='Người duyệt', readonly=True, tracking=True)
    approved_date = fields.Datetime(string='Ngày duyệt', readonly=True, tracking=True)
    rejected_by = fields.Many2one('res.users', string='Người từ chối', readonly=True, tracking=True)
    rejected_date = fields.Datetime(string='Ngày từ chối', readonly=True, tracking=True)

    _sql_constraints = [
        ('email_unique', 'unique(email)', 'Email này đã được đăng ký!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('library.signup.request') or 'New'
        return super(LibrarySignupRequest, self).create(vals)

    def action_approve(self):
        """Approve signup request and create user account"""
        self.ensure_one()

        if self.state != 'pending':
            raise UserError(_('Chỉ có thể duyệt các yêu cầu đang chờ duyệt.'))

        # Check if email already exists
        existing_user = self.env['res.users'].sudo().search([('login', '=', self.email)], limit=1)
        if existing_user:
            raise UserError(_('Email %s đã được sử dụng bởi tài khoản khác.') % self.email)

        # Create partner
        partner_vals = {
            'name': self.full_name,
            'dharma_name': self.dharma_name,
            'email': self.email,
            'phone': self.phone,
            'street': self.street,
            'street2': self.street2,
            'city': self.city,
            'state_id': self.state_id.id,
            'zip': self.zip,
            'country_id': self.country_id.id,
            'is_borrower': True,
            'borrower_type_id': self.borrower_type_id.id,
            'id_card_number': self.id_card_number,
            'student_id': self.student_id,
            'date_of_birth': self.date_of_birth,
            'vipassana_attended': self.vipassana_attended,
            'comment': self.notes,
        }

        partner = self.env['res.partner'].sudo().create(partner_vals)

        # Create user with portal access
        user_vals = {
            'name': self.full_name,
            'login': self.email,
            'email': self.email,
            'partner_id': partner.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        }

        user = self.env['res.users'].sudo().create(user_vals)

        # Generate signup token for password setup
        user.partner_id.sudo().signup_prepare()

        # Update request
        self.write({
            'state': 'approved',
            'partner_id': partner.id,
            'user_id': user.id,
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

        # Send approval email with password reset link
        self._send_approval_email()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã duyệt!'),
                'message': _('Tài khoản đã được tạo và email đã được gửi đến %s') % self.email,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reject(self):
        """Reject signup request"""
        self.ensure_one()

        if self.state != 'pending':
            raise UserError(_('Chỉ có thể từ chối các yêu cầu đang chờ duyệt.'))

        if not self.rejection_reason:
            raise UserError(_('Vui lòng nhập lý do từ chối.'))

        self.write({
            'state': 'rejected',
            'rejected_by': self.env.user.id,
            'rejected_date': fields.Datetime.now(),
        })

        # Send rejection email
        self._send_rejection_email()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã từ chối'),
                'message': _('Yêu cầu đăng ký đã bị từ chối.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_reset_to_pending(self):
        """Reset to pending state"""
        self.ensure_one()
        self.write({
            'state': 'pending',
            'rejection_reason': False,
            'rejected_by': False,
            'rejected_date': False,
        })

    def _send_approval_email(self):
        """Send email notification when approved"""
        template = self.env.ref('entro_library_signup.mail_template_signup_approved', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_rejection_email(self):
        """Send email notification when rejected"""
        template = self.env.ref('entro_library_signup.mail_template_signup_rejected', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_view_partner(self):
        """View created partner"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Chưa có partner được tạo.'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
