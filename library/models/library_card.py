# See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta as rd

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError as UserError, ValidationError


class LibraryCard(models.Model):
    """Defining Library Card."""

    _name = "library.card"
    _description = "Library Card information"
    _rec_name = "code"

    def _compute_name(self):
        for rec in self:
            rec.card_name = rec.partner_id.name if rec.partner_id else False

    @api.depends("start_date", "duration")
    def _compute_end_date(self):
        for rec in self:
            if rec.start_date:
                rec.end_date = rec.start_date + rd(months=rec.duration)

    code = fields.Char(
        "Số thẻ",
        required=True,
        default=lambda self: _("Mới"),
        help="Nhập số thẻ",
    )
    book_limit = fields.Integer(
        "Giới hạn số sách trên thẻ",
        required=True,
        help="Nhập giới hạn số sách",
    )
    card_name = fields.Char("Tên thẻ", compute="_compute_name", help="Tên thẻ")
    user = fields.Selection(
        [("student", "Học sinh"), ("teacher", "Giáo viên")],
        "Người dùng",
        help="Chọn người dùng",
    )
    user_type = fields.Selection(
        [("chu_tang_ni", "Chư Tăng Ni"), ("cu_si", "Cư sĩ")],
        "Loại người dùng",
        required=True,
        help="Chọn loại người dùng",
    )
    state = fields.Selection(
        [("draft", "Nháp"), ("running", "Xác nhận"), ("expire", "Hết hạn")],
        "Trạng thái",
        default="draft",
        help="Trạng thái thẻ thư viện",
    )
    start_date = fields.Date(
        "Ngày bắt đầu",
        default=fields.Date.context_today,
        help="Nhập ngày bắt đầu",
    )
    duration = fields.Integer("Thời hạn", help="Thời hạn tính bằng tháng")
    end_date = fields.Date("Ngày kết thúc", compute="_compute_end_date", store=True, help="Ngày kết thúc")
    partner_id = fields.Many2one(
        "res.partner",
        "Liên hệ",
        help="Thông tin liên hệ của người sở hữu thẻ"
    )
    user_id = fields.Many2one(
        "res.users",
        "Tài khoản người dùng",
        help="Tài khoản đăng nhập của người sở hữu thẻ"
    )
    has_user_account = fields.Boolean(
        "Có tài khoản",
        compute="_compute_has_user_account",
        help="Đã có tài khoản đăng nhập"
    )
    card_barcode = fields.Char(
        "Mã vạch thẻ",
        compute="_compute_card_barcode",
        store=True,
        help="Mã vạch được tạo từ mã thẻ thư viện"
    )
    active = fields.Boolean("Kích hoạt", default=True, help="Kích hoạt/vô hiệu hóa bản ghi")

    @api.depends('user_id')
    def _compute_has_user_account(self):
        """Check if library card has user account"""
        for card in self:
            card.has_user_account = bool(card.user_id)

    @api.depends('code')
    def _compute_card_barcode(self):
        """Generate barcode for library card"""
        for card in self:
            if card.code and card.code != 'Mới':
                # Generate barcode using card code with library prefix
                card.card_barcode = f"LIB{card.code}"
            else:
                card.card_barcode = ""

    @api.constrains("duration")
    def check_duration(self):
        """Constraint to assign library card more than once"""
        if self.duration and self.duration < 0:
            raise UserError(_("Thời hạn (tháng) không được là giá trị âm!"))

    @api.constrains("start_date")
    def check_start_date(self):
        new_dt = fields.Date.today()
        if self.start_date and self.start_date < new_dt:
            raise UserError(
                _("Ngày bắt đầu phải lớn hơn ngày hiện tại!")
            )

    @api.constrains("user_id")
    def check_member_card(self):
        """Constraint to assign library card more than once"""
        if self.user_id:
            if self.search(
                [
                    ("user_id", "=", self.user_id.id),
                    ("id", "not in", self.ids),
                    ("state", "!=", "expire"),
                ]
            ):
                raise UserError(
                    _(
                        "Bạn không thể cấp thẻ thư viện cho cùng một người dùng "
                        "nhiều hơn một lần!"
                    )
                )

    def running_state(self):
        """Change state to running"""
        self.code = self.env["ir.sequence"].next_by_code("library.card") or _("Mới")
        self.state = "running"

    def draft_state(self):
        """Change state to draft"""
        self.state = "draft"

    def unlink(self):
        """Inherited method to check state at record deletion"""
        for rec in self:
            if rec.state == "running":
                raise UserError(_("""Bạn không thể xóa thẻ thư viện đã xác nhận!"""))
        return super().unlink()

    def action_create_user_account(self):
        """Create user account from library card information"""
        self.ensure_one()
        
        if self.user_id:
            raise ValidationError(_("Thẻ này đã có tài khoản người dùng!"))
        
        # Get user info from partner or card name
        name = self.card_name or f'User {self.code}'
        email = ''

        # Use partner email if available
        if self.partner_id and self.partner_id.email:
            email = self.partner_id.email
        
        # Generate login from name or use card code
        login = email if email else f'user_{self.code.lower().replace(" ", "_")}'
        
        # Create user account
        user_vals = {
            'name': name,
            'login': login,
            'email': email if email else False,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],  # Basic user group
            'active': True,
        }
        
        try:
            user = self.env['res.users'].create(user_vals)
            self.user_id = user
            
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tài khoản người dùng',
                'res_model': 'res.users',
                'res_id': user.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except Exception as e:
            raise ValidationError(_("Không thể tạo tài khoản người dùng: %s") % str(e))

    def action_print_library_card(self):
        """Print library card"""
        self.ensure_one()
        return self.env.ref('library.action_report_library_card').report_action(self)

    def librarycard_expire(self):
        """Schedular to change in librarycard state when end date is over"""
        current_date = fields.Datetime.today()
        library_card_obj = self.env["library.card"]
        for rec in library_card_obj.search([("end_date", "<", current_date)]):
            rec.state = "expire"