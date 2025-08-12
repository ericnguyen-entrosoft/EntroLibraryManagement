# See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta as rd

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError as UserError


class LibraryRack(models.Model):
    """Defining Library Rack."""

    _name = "library.rack"
    _description = "Library Rack"

    name = fields.Char("Tên giá sách", required=True, help="Tên giá sách")
    code = fields.Char("Mã", help="Nhập mã tại đây")
    active = fields.Boolean("Kích hoạt", default="True", help="Kích hoạt/vô hiệu hóa bản ghi")


class LibraryAuthor(models.Model):
    """Defining Library Author."""

    _name = "library.author"
    _description = "Author"

    name = fields.Char("Tên tác giả", required=True, help="Nhập tên tác giả thư viện")
    birth_date = fields.Date("Ngày sinh", help="Nhập ngày sinh")
    death_date = fields.Date("Ngày mất", help="Nhập ngày mất")
    biography = fields.Text("Tiểu sử", help="Nhập tiểu sử")
    note = fields.Text("Ghi chú", help="Nhập ghi chú")
    editor_ids = fields.Many2many(
        "res.partner",
        "author_editor_rel",
        "author_id",
        "parent_id",
        "Biên tập viên",
        help="Chọn biên tập viên",
    )

    _sql_constraints = [
        (
            "name_uniq",
            "unique (name)",
            "Tên của tác giả phải là duy nhất!",
        )
    ]


class LibraryCard(models.Model):
    """Defining Library Card."""

    _name = "library.card"
    _description = "Library Card information"
    _rec_name = "code"

    # @api.depends("student_id")
    # def _compute_name(self):
    #     """Compute name."""
    #     for rec in self:
    #         if rec.student_id:
    #             user = rec.student_id.name
    #         user = rec.teacher_id.name
    #         rec.card_name = user

    @api.depends("student_id")
    def _compute_name(self):
        for rec in self:
            student_name = False
            teacher_name = False
            if rec.teacher_id:
                teacher_name = rec.teacher_id.name
            if rec.student_id:
                student_name = rec.student_id.name
            rec.card_name = teacher_name or student_name

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
    student_id = fields.Many2one(
        "student.student", "Tên học sinh", help="Chọn học sinh liên quan"
    )
    standard_id = fields.Many2one("school.standard", "Lớp", help="Chọn lớp")
    card_name = fields.Char("Tên thẻ", compute="_compute_name", help="Tên thẻ")
    user = fields.Selection(
        [("student", "Học sinh"), ("teacher", "Giáo viên")],
        "Người dùng",
        help="Chọn người dùng",
    )
    state = fields.Selection(
        [("draft", "Nháp"), ("running", "Xác nhận"), ("expire", "Hết hạn")],
        "Trạng thái",
        default="draft",
        help="Trạng thái thẻ thư viện",
    )
    roll_no = fields.Integer("Số báo danh", help="Nhập số báo danh")
    teacher_id = fields.Many2one("school.teacher", "Tên giáo viên")
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
    active = fields.Boolean("Kích hoạt", default=True, help="Kích hoạt/vô hiệu hóa bản ghi")

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

    @api.onchange("student_id")
    def on_change_student(self):
        """
        This method automatically fill up student roll number.
        and standard field on student_id field
        @student : Apply method on this Field name
        @return : Dictionary having identifier of the record as key
        and the value of student roll number and standard...
        """
        if self.student_id:
            self.standard_id = self.student_id.standard_id.id
            self.roll_no = self.student_id.roll_no

    def _update_student_info(self, vals):
        student_rec = self.env["student.student"].browse(vals.get("student_id"))
        vals.update(
            {
                "standard_id": student_rec.standard_id.id,
                "roll_no": student_rec.roll_no,
            }
        )

    @api.model
    def create(self, vals):
        """Inherited this method to assign student values at record creation"""
        if vals.get("student_id"):
            self._update_student_info(vals)
        return super().create(vals)

    def write(self, vals):
        """Inherited this method to update student values at record updation"""
        if vals.get("student_id"):
            self._update_student_info(vals)
        return super().write(vals)

    @api.constrains("student_id", "teacher_id")
    def check_member_card(self):
        """Constraint to assign library card more than once"""
        if self.user == "student":
            if self.search(
                [
                    ("student_id", "=", self.student_id.id),
                    ("id", "not in", self.ids),
                    ("state", "!=", "expire"),
                ]
            ):
                raise UserError(
                    _(
                        "Bạn không thể cấp thẻ thư viện cho cùng một học sinh "
                        "nhiều hơn một lần!"
                    )
                )
        if self.user == "teacher":
            if self.search(
                [
                    ("teacher_id", "=", self.teacher_id.id),
                    ("id", "not in", self.ids),
                    ("state", "!=", "expire"),
                ]
            ):
                raise UserError(
                    _(
                        "Bạn không thể cấp thẻ thư viện cho cùng một giáo viên "
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

    def librarycard_expire(self):
        """Schedular to change in librarycard state when end date is over"""
        current_date = fields.Datetime.today()
        library_card_obj = self.env["library.card"]
        for rec in library_card_obj.search([("end_date", "<", current_date)]):
            rec.state = "expire"


class LibraryBookIssue(models.Model):
    """Book variant of product."""

    _name = "library.book.issue"
    _description = "Library information"
    _rec_name = "standard_id"

    @api.depends("date_issue", "day_to_return_book")
    def _compute_return_date(self):
        """This method calculate a book return date.
        @return : Dictionary having identifier of the record as key
        and the book return date as value"""
        for rec in self:
            diff = rd(days=rec.day_to_return_book or 0.0)
            if rec.date_issue and diff:
                rec.date_return = rec.date_issue + diff

    @api.depends("actual_return_date")
    def _compute_penalty(self):
        """This method calculate a penalty on book .
        @return : Dictionary having identifier of the record as key
                  and penalty as value"""
        for line in self:
            if line.date_return:
                start_day = line.date_return
                end_day = line.actual_return_date
                line.penalty = 0.0
                if start_day and end_day and start_day < end_day:
                    diff = rd(end_day.date(), start_day.date())
                    day = float(diff.days) or 0.0
                    if line.day_to_return_book:
                        line.penalty = day * line.name.fine_late_return or 0.0

    @api.depends("state")
    def _compute_lost_penalty(self):
        """This method calculate a penalty on book lost .
        @return : Dictionary having identifier of the record as key
                  and book lost penalty as value"""
        for rec in self:
            if rec.state and rec.state == "lost":
                rec.lost_penalty = rec.name.fine_lost or 0.0

    @api.depends("name")
    def _compute_check_ebook(self):
        """Compute for ebook boolean"""
        for rec in self:
            rec.ebook_check = False
            if rec.name.is_ebook:
                rec.ebook_check = True

    name = fields.Many2one(
        "product.product", "Tên sách", required=True, help="Nhập tên sách"
    )
    issue_code = fields.Char(
        "Số phiếu mượn",
        required=True,
        default=lambda self: _("Mới"),
        help="Nhập số phiếu mượn",
    )
    book_request_id = fields.Many2one("library.book.request", "Mã yêu cầu")
    student_id = fields.Many2one(
        "student.student", "Tên học sinh", help="Nhập học sinh"
    )
    teacher_id = fields.Many2one(
        "school.teacher", "Tên giáo viên", help="Chọn giáo viên"
    )
    card_name = fields.Char("Tên thẻ", help="Tên thẻ")
    standard_id = fields.Many2one("school.standard", "Lớp", help="Chọn lớp")
    roll_no = fields.Integer("Số báo danh", help="Nhập số báo danh")
    invoice_id = fields.Many2one(
        "account.move", "Hóa đơn người dùng", help="Chọn hóa đơn"
    )
    date_issue = fields.Datetime(
        "Ngày mượn",
        required=True,
        help="Ngày mượn sách",
        default=fields.Datetime.now,
    )
    date_return = fields.Datetime(
        compute="_compute_return_date",
        string="Ngày trả",
        store=True,
        help="Ngày phải trả sách",
    )
    actual_return_date = fields.Datetime(
        "Ngày trả thực tế",
        help="Ngày trả sách thực tế",
    )
    penalty = fields.Float(
        "Phạt trả trễ",
        compute="_compute_penalty",
        store=True,
        help="Phạt trả sách trễ",
    )
    lost_penalty = fields.Float(
        compute="_compute_lost_penalty",
        string="Phạt mất sách",
        store=True,
        help="Phạt khi mất sách",
    )
    day_to_return_book = fields.Integer(
        "Số ngày trả sách", help="Nhập số ngày trả sách"
    )
    card_id = fields.Many2one("library.card", "Số thẻ", required=True)
    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("issue", "Đã mượn"),
            ("reissue", "Gia hạn"),
            ("cancel", "Đã hủy"),
            ("return", "Đã trả"),
            ("lost", "Mất sách"),
            ("fine", "Bị phạt"),
            ("paid", "Hoàn thành"),
            ("subscribe", "Đăng ký"),
            ("pending", "Đang chờ"),
        ],
        "Trạng thái",
        default="draft",
        help="Trạng thái sách thư viện",
    )
    user = fields.Char("Người dùng", help="Nhập người dùng")
    compute_inv = fields.Integer(
        "Số hóa đơn",
        compute="_compute_invoices",
        help="Số lượng hóa đơn",
    )
    color = fields.Integer("Chỉ số màu", help="Chỉ số màu")
    payment_mode = fields.Selection(
        [("pay_physically", "Thanh toán tiền mặt"), ("by_bank", "Thanh toán qua ngân hàng")],
        "Phương thức thanh toán",
        help="Chọn phương thức thanh toán",
    )
    subscription_amt = fields.Float(
        "Số tiền đăng ký", help="Nhập số tiền đăng ký"
    )
    bank_teller_no = fields.Char(string="Số phiếu ngân hàng", help="Nhập số phiếu ngân hàng")
    bank_teller_amt = fields.Float(
        "Số tiền phiếu ngân hàng", help="Nhập số tiền phiếu ngân hàng"
    )
    ebook_download = fields.Binary("Tải sách", help="Tải sách")
    ebook_check = fields.Boolean(
        "Kiểm tra sách điện tử",
        compute="_compute_check_ebook",
        help="Kích hoạt cho sách điện tử",
    )
    lot_id = fields.Many2one(
        "stock.lot",
        "Số serial",
        help="Số serial cụ thể của sách được mượn"
    )

    @api.onchange("name")
    def onchange_book_name(self):
        """Filter available lots when book is selected"""
        if self.name and not self.name.is_ebook:
            # Get lots that have available stock
            available_lots = []
            lots = self.env['stock.lot'].search([('product_id', '=', self.name.id)])
            for lot in lots:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', self.name.id),
                    ('lot_id', '=', lot.id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0)
                ])
                if quants:
                    available_lots.append(lot.id)
            
            return {
                'domain': {
                    'lot_id': [('id', 'in', available_lots)]
                }
            }
        else:
            return {
                'domain': {
                    'lot_id': [('id', '=', False)]
                }
            }

    @api.onchange("date_issue", "day_to_return_book")
    def onchange_day_to_return_book(self):
        """This method calculate a book return date.
        @return : Dictionary having identifier of the record as key
                  and the book return date as value"""
        diff = rd(days=self.day_to_return_book or 0.0)
        if self.date_issue and diff:
            self.date_return = self.date_issue + diff

    @api.constrains("card_id", "state")
    def _check_issue_book_limit(self):
        """This method used how many book can issue as per user type.
        @return : True or False.
        """
        for rec in self:
            if rec.card_id:
                card_ids = rec.search_count(
                    [
                        ("card_id", "=", rec.card_id.id),
                        ("state", "in", ["issue", "reissue"]),
                    ]
                )
                card_no = card_ids
                if rec.state == "issue" or rec.state == "reissue":
                    card_no = card_ids - 1
                if rec.card_id.book_limit > card_no:
                    return True
                # Check the issue limit on card if it is over it give warning
                raise UserError(_("""Giới hạn mượn sách trên thẻ này đã vượt quá!"""))

    @api.onchange("card_id")
    def onchange_card_issue(self):
        """This method automatically fill up values on card.
        @return : Dictionary having identifier of the record as key
                  and the user info as value
        """
        if self.card_id:
            self.user = str(self.card_id.user.title()) or ""
            self.card_name = self.card_id.card_name or ""
            if self.card_id.user.title() == "Student":
                self.student_id = self.card_id.student_id.id or False
                self.standard_id = self.card_id.standard_id.id or False
                self.roll_no = int(self.card_id.roll_no) or False
            else:
                self.teacher_id = self.card_id.teacher_id.id

    @api.constrains("card_id", "name")
    def check_book_issue(self):
        """Constraint to check issue book on same card"""
        if self.search(
            [
                ("name", "=", self.name.id),
                ("id", "not in", self.ids),
                ("card_id", "=", self.card_id.id),
                ("state", "not in", ["draft", "cancel", "return", "paid"]),
            ]
        ):
            raise UserError(
                _(
                    "Bạn không thể mượn cùng một cuốn sách trên cùng một thẻ "
                    "nhiều hơn một lần tại cùng thời điểm!"
                )
            )

    def _update_student_vals(self, vals):
        """This is the common method to update student
        record at creation and edition of the exam record"""
        # fetch the record of user type student
        card_rec = self.env["library.card"].browse(vals.get("card_id"))
        vals.update(
            {
                "student_id": card_rec.student_id.id,
                "card_id": card_rec.id,
                "user": str(card_rec.user.title()),
                "standard_id": card_rec.standard_id.id,
                "roll_no": int(card_rec.roll_no),
                "card_name": card_rec.card_name,
            }
        )

    def _update_teacher_vals(self, vals):
        """This is the common method to update teacher
        record at creation and edition of the exam record"""
        # fetch the record of user type teacher
        card_rec = self.env["library.card"].browse(vals.get("card_id"))
        vals.update(
            {
                "teacher_id": card_rec.teacher_id.id,
                "card_name": card_rec.card_name,
                "user": str(card_rec.user.title()),
            }
        )

    @api.model
    def create(self, vals):
        """Override create method"""
        if vals.get("card_id") and vals.get("user") != "Teacher":
            self._update_student_vals(vals)
        if vals.get("card_id") and vals.get("user") == "Teacher":
            self._update_teacher_vals(vals)
        return super().create(vals)

    def write(self, vals):
        """Override write method"""
        if vals.get("card_id") and vals.get("user") != "Teacher":
            self._update_student_vals(vals)
        if vals.get("card_id") and vals.get("user") == "Teacher":
            self._update_teacher_vals(vals)
        return super().write(vals)

    def draft_book(self):
        """This method for books in draft state."""
        self.state = "draft"

    def issue_book(self):
        """This method used for issue a books."""
        curr_dt = fields.Date.today()
        seq_obj = self.env["ir.sequence"]
        for rec in self:
            if rec.card_id.end_date < curr_dt and rec.card_id.end_date > curr_dt:
                raise UserError(_("Thành viên của thẻ thư viện đã hết hạn!"))
            code_issue = seq_obj.next_by_code("library.book.issue") or _("Mới")
            if (
                rec.name
                and rec.name.availability == "notavailable"
                and not rec.name.is_ebook
            ):
                raise UserError(
                    _(
                        "Cuốn sách bạn chọn không có sẵn. Vui lòng"
                        " thử lại sau!"
                    )
                )
            if rec.student_id:
                issue_str = ""
                for book in rec.search(
                    [("card_id", "=", rec.card_id.id), ("state", "=", "fine")]
                ):
                    issue_str += str(book.issue_code) + ", "
                # check if fine on book is paid until then user
                # cannot issue new book
                if issue_str:
                    raise UserError(
                        _(
                            "Bạn không thể yêu cầu mượn sách cho đến khi chưa thanh toán tiền phạt"
                            " cho các phiếu mượn sách %s!"
                        )
                        % issue_str
                    )
            if rec.card_id:
                card_rec = rec.search_count(
                    [
                        ("card_id", "=", rec.card_id.id),
                        ("state", "in", ["issue", "reissue"]),
                    ]
                )
                if rec.card_id.book_limit > card_rec:
                    return_day = rec.name.day_to_return_book
                    
                    # For non-ebook, create stock move to track issuance
                    if not rec.name.is_ebook and rec.lot_id:
                        # Create stock move from internal to customers (issued)
                        internal_location = self.env['stock.location'].search([
                            ('usage', '=', 'internal'),
                            ('company_id', '=', self.env.company.id)
                        ], limit=1)
                        customer_location = self.env.ref('stock.stock_location_customers')
                        
                        move_vals = {
                            'name': f'Mượn sách: {rec.name.name} - {rec.issue_code}',
                            'product_id': rec.name.id,
                            'product_uom_qty': 1,
                            'product_uom': rec.name.uom_id.id,
                            'location_id': internal_location.id,
                            'location_dest_id': customer_location.id,
                            'date': fields.Datetime.now(),
                            'state': 'draft',
                            'reference': rec.issue_code,
                        }
                        move = self.env['stock.move'].create(move_vals)
                        
                        # Add lot information to move
                        move_line_vals = {
                            'move_id': move.id,
                            'product_id': rec.name.id,
                            'lot_id': rec.lot_id.id,
                            'quantity': 1,
                            'location_id': internal_location.id,
                            'location_dest_id': customer_location.id,
                            'product_uom_id': rec.name.uom_id.id,
                        }
                        self.env['stock.move.line'].create(move_line_vals)
                        
                        # Process move
                        move._action_confirm()
                        move._action_assign()
                        move._action_done()
                    
                    rec.write(
                        {
                            "state": "issue",
                            "day_to_return_book": return_day,
                            "issue_code": code_issue,
                        }
                    )
            return True

    def reissue_book(self):
        """This method used for reissue a books."""
        self.write({"actual_return_date": fields.datetime.now()})
        self._compute_penalty()
        if self.penalty > 0:
            raise UserError(_("""Ngày trả đã hết hạn, Vui lòng trả sách của bạn!"""))
        self.write(
            {
                "state": "reissue",
                "date_issue": fields.Datetime.today(),
                "actual_return_date": False,
            }
        )

    def return_book(self):
        """This method used for return a books."""
        self.actual_return_date = fields.datetime.now()
        self.state = "return"
        
        # Create return stock move when book is returned
        if self.lot_id and not self.name.is_ebook:
            # Create stock move from customers back to internal
            internal_location = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            customer_location = self.env.ref('stock.stock_location_customers')
            
            move_vals = {
                'name': f'Trả sách: {self.name.name} - {self.issue_code}',
                'product_id': self.name.id,
                'product_uom_qty': 1,
                'product_uom': self.name.uom_id.id,
                'location_id': customer_location.id,
                'location_dest_id': internal_location.id,
                'date': fields.Datetime.now(),
                'state': 'draft',
                'reference': self.issue_code,
            }
            move = self.env['stock.move'].create(move_vals)
            
            # Add lot information to move
            move_line_vals = {
                'move_id': move.id,
                'product_id': self.name.id,
                'lot_id': self.lot_id.id,
                'quantity': 1,
                'location_id': customer_location.id,
                'location_dest_id': internal_location.id,
                'product_uom_id': self.name.uom_id.id,
            }
            self.env['stock.move.line'].create(move_line_vals)
            
            # Process move
            move._action_confirm()
            move._action_assign()
            move._action_done()

    def lost_book(self):
        """Method to create scrap records for lost books"""
        stock_scrap_obj = self.env["stock.scrap"]
        for rec in self:
            rec.actual_return_date = fields.datetime.now()
            scrap_fields = list(stock_scrap_obj._fields)
            scrap_vals = stock_scrap_obj.default_get(scrap_fields)
            origin_str = "Book lost : "
            if rec.issue_code:
                origin_str += rec.issue_code
            if rec.student_id:
                origin_str += "( Student: " + rec.student_id.name + ")" or ""
            elif rec.teacher_id:
                origin_str += "( Faculty: " + rec.teacher_id.name + ")" or ""
            scrap_vals.update(
                {
                    "product_id": rec.name.id,
                    "product_uom_id": rec.name.uom_id.id,
                    "lot_id": rec.lot_id.id if rec.lot_id else False,
                    "origin": origin_str,
                }
            )
            scrap_id = stock_scrap_obj.with_context(book_lost=True).create(scrap_vals)
            scrap_id.action_validate()
            rec.state = "lost"
            rec.lost_penalty = self.name.fine_lost
        return True

    def cancel_book(self):
        """This method used for cancel book issue."""
        self.book_request_id.write({"state": "cancel"})
        self.state = "cancel"

    def user_fine(self):
        """
        This method used when penalty on book either late return or book lost
        and generate invoice of fine.
        """
        invoice_obj = self.env["account.move"]
        #       check whether address has been defined or not for student and teacher
        for record in self:
            if record.user == "Student":
                usr = record.student_id.partner_id.id
                if not record.student_id.partner_id.contact_address:
                    raise UserError(_("Lỗi! Học sinh phải có địa chỉ nhà!"))
            else:
                usr = record.teacher_id.employee_id.user_id.partner_id.id
                if not record.teacher_id.employee_id.address_home_id:
                    raise UserError(_("Lỗi! Giáo viên phải có địa chỉ nhà!"))
            # prepare and create value of account.move
            vals_invoice = {
                "move_type": "out_invoice",
                "partner_id": usr,
                "book_issue_id": record.id,
                "book_issue_reference": record.issue_code or "",
            }
            new_invoice_rec = invoice_obj.create(vals_invoice)
            # prepare move line value as lost books penalty
            acc_id = new_invoice_rec.journal_id.default_account_id.id
            invoice_line_ids = []
            if record.lost_penalty:
                invoice_line_ids.append(
                    (
                        0,
                        0,
                        {
                            "name": "Phạt mất sách",
                            "price_unit": record.lost_penalty,
                            "move_id": new_invoice_rec.id,
                            "account_id": acc_id,
                        },
                    )
                )
            # prepare move line value as late books return penalty
            if record.penalty:
                invoice_line_ids.append(
                    (
                        0,
                        0,
                        {
                            "name": "Phạt trả trễ",
                            "price_unit": record.penalty,
                            "move_id": new_invoice_rec.id,
                            "account_id": acc_id,
                        },
                    )
                )
            # update move lines for created move and
            # redirect it to particular invoice
            new_invoice_rec.write({"invoice_line_ids": invoice_line_ids})
        self.state = "fine"
        # view_id = self.env.ref("account.view_move_form")
        # context = dict(self._context)
        # context.update(
        #     {
        #         "default_move_type": "out_invoice",
        #         "default_book_issue_id": record.id,
        #         "default_customer": record.id,
        #     }
        # )
        # return {
        #     "name": _("New Invoice"),
        #     "view_mode": "form",
        #     "view_id": view_id.ids,
        #     "res_model": "account.move",
        #     "type": "ir.actions.act_window",
        #     # "nodestroy": True,
        #     # "res_id": new_invoice_rec.id,
        #     "domain": [("book_issue_id", "=", record.id)],
        #     "target": "current",
        #     "context": context,
        # }

    def subscription_pay(self):
        """Method to pay for subscription"""
        invoice_obj = self.env["account.move"]
        for record in self:
            if record.user == "Student":
                usr = record.student_id.partner_id.id
                if not record.student_id.partner_id.contact_address:
                    raise UserError(_("Error ! The Student must have a Home address."))
            else:
                usr = record.teacher_id.employee_id.user_id.partner_id.id
                if not record.teacher_id.employee_id.address_home_id:
                    raise UserError(_("Error ! Teacher must have a Home address!."))
            new_invoice_rec = invoice_obj.create(
                {
                    "move_type": "out_invoice",
                    "partner_id": usr,
                    "book_issue_id": record.id,
                    "book_issue_reference": record.issue_code or "",
                }
            )
            acc_id = new_invoice_rec.journal_id.default_account_id.id
            invoice_line_ids = []
            if record.subscription_amt:
                subcription_amount = record.subscription_amt
                invoice_line_ids.append(
                    (
                        0,
                        0,
                        {
                            "name": "Book Subscription Amount",
                            "price_unit": subcription_amount,
                            "invoice_id": new_invoice_rec.id,
                            "account_id": acc_id,
                        },
                    )
                )
            new_invoice_rec.write({"invoice_line_ids": invoice_line_ids})
        self.state = "pending"
        view_id = self.env.ref("account.view_move_form")
        return {
            "name": _("New Invoice"),
            "view_mode": "form",
            "view_id": view_id.ids,
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "nodestroy": True,
            "res_id": new_invoice_rec.id,
            "target": "current",
            "context": {"default_type": "out_invoice"},
        }

    def view_invoice(self):
        """this method is use for the view invoice of penalty"""
        invoice_obj = self.env["account.move"]
        for rec in self:
            invoices_rec = invoice_obj.search([("book_issue_id", "=", rec.id)])
            action = self.env.ref("account.action_move_out_invoice_type").read()[0]
            if len(invoices_rec) > 1:
                action["domain"] = [("id", "in", invoices_rec.ids)]
            elif len(invoices_rec) == 1:
                action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
                action["res_id"] = invoices_rec.ids[0]
            else:
                action = {"type": "ir.actions.act_window_close"}
        return action

    def _compute_invoices(self):
        """Method to compute invoices"""
        inv_obj = self.env["account.move"]
        for rec in self:
            count_invoice = inv_obj.search_count([("book_issue_id", "=", rec.id)])
            rec.compute_inv = count_invoice


class LibraryBookRequest(models.Model):
    """Request for Book."""

    _name = "library.book.request"
    _rec_name = "req_id"
    _description = "Book Request Information"

    @api.depends("type")
    def _compute_bname(self):
        """Method to compute book name"""
        for rec in self:
            if rec.type:
                if rec.type == "existing":
                    book = rec.name.name
                book = rec.new_book
                rec.book_name = book

    req_id = fields.Char(
        "Mã yêu cầu", readonly=True, default="Mới", help="Nhập mã yêu cầu"
    )
    card_id = fields.Many2one(
        "library.card", "Card No", required=True, help="Select library card"
    )
    type = fields.Selection(
        [("existing", "HardCopy"), ("ebook", "E Book")],
        "Book Type",
        help="Select type of book",
    )
    name = fields.Many2one("product.product", "Book Name", help="Select book")
    new_book = fields.Char(string="New Book Name", help="Enter new book name")
    book_name = fields.Char(
        "Name", compute="_compute_bname", store=True, help="Enter book name"
    )
    state = fields.Selection(
        [("draft", "Draft"), ("confirm", "Confirm"), ("cancel", "Cancelled")],
        default="draft",
        help="State of library book request",
    )
    book_return_days = fields.Integer(
        related="name.day_to_return_book",
        string="Return Days",
        help="Book return days",
    )
    ebook_name = fields.Many2one("product.product", "E book Name", help="E-book name")
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the category without removing it.",
    )
    book_issue_id = fields.Many2one("library.book.issue", "Book Issue")

    @api.constrains("card_id", "name")
    def check_book_request(self):
        """Constraint to check request book on same card"""
        if self.search(
            [
                ("card_id", "=", self.card_id.id),
                ("name", "=", self.name.id),
                ("id", "not in", self.ids),
                ("type", "=", "existing"),
                ("state", "!=", "cancel"),
            ]
        ):
            raise UserError(
                _(
                    "You can't request same book on same card more than once at "
                    "same time!"
                )
            )

    @api.constrains("card_id")
    def check_start_date(self):
        date = fields.Date.today()
        if self.card_id.start_date > date:
            raise UserError(_("You can't request book!"))

    @api.model
    def create(self, vals):
        """Inherited method to generate sequence at record creation"""
        seq_obj = self.env["ir.sequence"]
        vals.update({"req_id": (seq_obj.next_by_code("library.book.request") or "New")})
        return super().create(vals)

    def draft_book_request(self):
        """Method to change state as draft"""
        self.state = "draft"

    def confirm_book_request(self):
        """Method to confirm book request"""
        book_issue_obj = self.env["library.book.issue"]
        curr_dt = fields.Date.today()
        vals = {}

        issue_id = False
        if (self.card_id.start_date and curr_dt <= self.card_id.start_date) and (
            self.card_id.end_date and curr_dt >= self.card_id.end_date
        ):
            raise UserError(_("Thành viên của thẻ thư viện đã hết hạn!"))
        if self.type == "existing":
            vals.update(
                {
                    "card_id": self.card_id.id,
                    "book_request_id": self.id,
                    "name": self.name.id,
                }
            )
        elif self.type == "ebook" and self.ebook_name:
            vals.update(
                {
                    "name": self.ebook_name.id,
                    "card_id": self.card_id.id,
                    "subscription_amt": self.ebook_name.subscrption_amt,
                }
            )
        issue_id = book_issue_obj.create(vals)
        if self.type == "ebook":
            issue_vals = {}
            if not self.ebook_name.is_subscription:
                issue_vals.update(
                    {
                        "state": "paid",
                        "ebook_download": self.ebook_name.attach_ebook,
                    }
                )
            else:
                issue_vals.update(
                    {
                        "state": "subscribe",
                        "ebook_download": self.ebook_name.attach_ebook,
                    }
                )
            issue_id.write(issue_vals)
        else:
            issue_id.write({"state": "draft"})
        self.state = "confirm"
        self.book_issue_id = issue_id.id
        # changes state to confirm
        if issue_id:
            issue_id.onchange_card_issue()
        return {
            "name": ("Book Issue"),
            "view_mode": "form",
            "res_id": issue_id.id,
            "res_model": "library.book.issue",
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def unlink(self):
        """Inherited method to check state at record deletion"""
        for rec in self:
            if rec.state == "confirm":
                raise UserError(
                    _(
                        "You cannot delete a confirmed record of library book"
                        " request!"
                    )
                )
        return super().unlink()

    def cancle_book_request(self):
        """Method to change state as cancel"""
        self.state = "cancel"


class StudentLibrary(models.Model):
    _inherit = "student.student"

    def set_alumni(self):
        """Override method to make library card of student active false
        when student is alumni"""
        lib_card_obj = self.env["library.card"]
        for rec in self:
            student_card_rec = lib_card_obj.search([("student_id", "=", rec.id)])
            if student_card_rec:
                student_card_rec.active = False
        return super().set_alumni()
