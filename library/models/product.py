# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta


class ProductTemplate(models.Model):
    _inherit = "product.template"

    name = fields.Char("Tên sách", required=True, help="Tên sách")


class ProductCategory(models.Model):
    _inherit = "product.category"

    book_categ = fields.Boolean("Danh mục sách", default=False, help="Danh mục sách")


class ProductLang(models.Model):
    """Book language"""

    _name = "product.lang"
    _description = "Book's Language"

    code = fields.Char("Mã", required=True, help="Mã sách")
    name = fields.Char("Tên", required=True, translate=True, help="Tên sách")

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name)",
            "The name of the language must be unique !",
        )
    ]

    @api.constrains("code")
    def _check_code(self):
        for rec in self:
            if self.search([("id", "!=", rec.id), ("code", "=", rec.code)]):
                raise ValidationError(_("The code of the language must be unique !"))


class ProductProduct(models.Model):
    """Book variant of product"""

    _inherit = "product.product"

    @api.model
    def default_get(self, fields):
        """Overide method to get default category books"""
        res = super().default_get(fields)
        category = self.env["product.category"].search(
            [("name", "=", "Books")], limit=1
        )
        res.update({"categ_id": category.id})
        return res

    def _default_categ(self):
        """This method put default category of product"""

        if self._context is None:
            self._context = {}
        if self._context.get("category_id", False):
            return self._context["category_id"]
        res = False
        try:
            res = self.env.ref("library.product_category_1").id
        except ValueError:
            res = False
        return res

    def _get_partner_code_name(self, product, parent_id):
        """This method get the partner code name"""
        for supinfo in product.seller_ids:
            if supinfo.partner_id.id == parent_id:
                return {
                    "code": supinfo.product_code or product.default_code,
                    "name": supinfo.product_name or product.name,
                }
        res = {"code": product.default_code, "name": product.name}
        return res

    def _compute_product_code(self):
        """This method get the product code"""
        res = {}
        parent_id = self._context.get("parent_id", None)
        for product in self:
            res[product.id] = self._get_partner_code_name(product, parent_id)["code"]
        return res

    @api.model
    def create(self, vals):
        """This method is Create new student"""
        # add link from editor to supplier:
        if "editor" in vals:
            for supp in self.env["library.editor.supplier"].search(
                ("name", "=", vals.get("editor"))
            ):
                supplier = [
                    0,
                    0,
                    {
                        "pricelist_ids": [],
                        "name": supp.supplier_id.id,
                        "sequence": supp.sequence,
                        "qty": 0,
                        "delay": 1,
                        "product_code": False,
                        "product_name": False,
                    },
                ]
                if "seller_ids" not in vals:
                    vals["seller_ids"] = [supplier]
                else:
                    vals["seller_ids"].append(supplier)
        
        # Enable serial tracking for books
        if vals.get('categ_id'):
            category = self.env['product.category'].browse(vals['categ_id'])
            if category.book_categ and not vals.get('tracking'):
                vals['tracking'] = 'serial'
        
        return super().create(vals)

    @api.depends("qty_available")
    def _compute_books_available(self):
        # TODO
        for rec in self:
            rec.books_available = rec.qty_available
            rec.availability = "available"

    @api.depends("books_available", "day_to_return_book")
    def _compute_books_availablity(self):
        """Method to compute availability of book"""
        for rec in self:
            rec.availability = "notavailable"
            if rec.books_available >= 1:
                rec.availability = "available"

    @api.depends("lot_ids")
    def _compute_lot_count(self):
        """Compute lot/serial counts"""
        for rec in self:
            rec.total_lots = len(rec.lot_ids)
            # Check availability based on current stock of each lot
            available_count = 0
            for lot in rec.lot_ids:
                # Get current stock for this lot
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', rec.id),
                    ('lot_id', '=', lot.id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0)
                ])
                if quants:
                    available_count += 1
            rec.available_lots = available_count

    def _generate_serial_number(self, receiving_date=None):
        """Generate serial number based on year + sequence + first letter"""
        if not receiving_date:
            receiving_date = fields.Date.today()
        
        year = str(receiving_date.year)
        first_letter = self.name[0].upper() if self.name else 'X'
        
        # Get next sequence number for this year
        sequence_obj = self.env['ir.sequence']
        sequence_code = f'library.book.serial.{year}'
        
        # Create sequence if it doesn't exist
        if not sequence_obj.sudo().search([('code', '=', sequence_code)]):
            sequence_obj.sudo().create({
                'name': f'Book Serial {year}',
                'code': sequence_code,
                'prefix': year,
                'suffix': first_letter,
                'padding': 6,
                'number_increment': 1,
                'number_next': 1,
            })
        
        serial_number = sequence_obj.sudo().next_by_code(sequence_code)
        return serial_number

    def action_add_quantity(self):
        """Open wizard to add book quantity via receipt"""
        return {
            'name': 'Thêm sách mới',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.receipt.wizard',
            'view_mode': 'form',
            'context': {
                'default_product_id': self.id,
            },
            'target': 'new',
        }

    def create_book_receipt(self, quantity, receiving_date=None, location_dest=None):
        """Create a receipt for new books with automatic serial generation"""
        if not receiving_date:
            receiving_date = fields.Date.today()
        
        # Ensure product has tracking enabled
        if self.tracking != 'serial':
            self.tracking = 'serial'
        
        # Get warehouse and locations
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not warehouse:
            raise ValidationError(_("Không tìm thấy kho hàng!"))
        
        # Use provided location or default to warehouse stock location
        if not location_dest:
            location_dest = warehouse.lot_stock_id
        
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        
        # Create receipt (incoming picking)
        picking_vals = {
            'picking_type_id': warehouse.in_type_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': location_dest.id,
            'origin': f'Thêm sách: {self.name}',
            'scheduled_date': receiving_date,
        }
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Generate serials first
        lots_created = []
        for i in range(quantity):
            serial_number = self._generate_serial_number(receiving_date)
            lot_vals = {
                'name': serial_number,
                'product_id': self.id,
                'company_id': self.env.company.id,
            }
            lot = self.env['stock.lot'].create(lot_vals)
            lots_created.append(lot)
        
        # Create stock moves with serial assignment
        for lot in lots_created:
            move_vals = {
                'name': f'Nhập sách: {self.name}',
                'product_id': self.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_id.id,
                'picking_id': picking.id,
                'location_id': supplier_location.id,
                'location_dest_id': location_dest.id,
                'date': receiving_date,
            }
            move = self.env['stock.move'].create(move_vals)
            
            # Create move line with lot assignment
            move_line_vals = {
                'move_id': move.id,
                'product_id': self.id,
                'lot_id': lot.id,
                'quantity': 1,
                'location_id': supplier_location.id,
                'location_dest_id': warehouse.lot_stock_id.id,
                'product_uom_id': self.uom_id.id,
                'picking_id': picking.id,
            }
            self.env['stock.move.line'].create(move_line_vals)
        
        # Confirm and process receipt
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()
        
        return {
            'picking': picking,
            'lots_created': lots_created,
            'serial_numbers': [lot.name for lot in lots_created]
        }
    
    def action_borrow_book(self):
        """Open wizard to borrow book"""
        return {
            'name': 'Mượn sách',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.borrow.wizard',
            'view_mode': 'form',
            'context': {
                'default_product_id': self.id,
            },
            'target': 'new',
        }

    def create_book_borrowing(self, lot_id, borrower_name, borrower_info, due_date=None, library_card=None):
        """Create a borrowing picking to move book from stock to borrowing location"""
        if not due_date:
            due_date = fields.Date.today() + timedelta(days=14)  # Default 2 weeks
        
        # Get locations
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not warehouse:
            raise ValidationError(_("Không tìm thấy kho hàng!"))
        
        # Get borrowing location
        borrowing_location = self.env.ref('library.stock_location_library_borrowing', raise_if_not_found=False)
        if not borrowing_location:
            raise ValidationError(_("Không tìm thấy vị trí kho mượn sách!"))
        
        # Find current location of the book (lot)
        lot = self.env['stock.lot'].browse(lot_id)
        if not lot:
            raise ValidationError(_("Không tìm thấy số serial sách!"))
        
        # Get current stock location of this lot
        quant = self.env['stock.quant'].search([
            ('lot_id', '=', lot.id),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal')
        ], limit=1)
        
        if not quant:
            raise ValidationError(_("Sách này không có trong kho hoặc đã được mượn!"))
        
        # Create borrowing picking (internal transfer)
        picking_vals = {
            'picking_type_id': warehouse.int_type_id.id,
            'location_id': quant.location_id.id,
            'location_dest_id': borrowing_location.id,
            'origin': f'Mượn sách: {self.name} - {borrower_name}',
            'scheduled_date': fields.Datetime.now(),
            'note': f'Người mượn: {borrower_name}\nThông tin: {borrower_info}\nHạn trả: {due_date}',
            'library_card_id': library_card.id if library_card else False,
            'borrower_name': borrower_name,
            'borrower_info': borrower_info,
            'due_date': due_date,
            'is_book_borrowing': True,
            'is_borrowing_transfer': True,
            'user_id': self.env.user.id,  # Assign to current user
            'partner_id': library_card.partner_id.id if library_card and library_card.partner_id else False,
        }
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create stock move
        move_vals = {
            'name': f'Mượn sách: {self.name}',
            'product_id': self.id,
            'product_uom_qty': 1,
            'product_uom': self.uom_id.id,
            'picking_id': picking.id,
            'location_id': quant.location_id.id,
            'location_dest_id': borrowing_location.id,
            'date': fields.Datetime.now(),
        }
        move = self.env['stock.move'].create(move_vals)
        
        # Create move line with lot assignment
        move_line_vals = {
            'move_id': move.id,
            'product_id': self.id,
            'lot_id': lot.id,
            'quantity': 1,
            'product_uom_id': self.uom_id.id,
            'location_id': quant.location_id.id,
            'location_dest_id': borrowing_location.id,
            'picking_id': picking.id,
        }
        self.env['stock.move.line'].create(move_line_vals)
        
        # Confirm and process picking
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()
        
        return {
            'picking': picking,
            'lot': lot,
            'due_date': due_date
        }

    def action_view_borrowing_transfers(self):
        """View all borrowing transfers for this book"""
        borrowing_location = self.env.ref('library.stock_location_library_borrowing', raise_if_not_found=False)
        if not borrowing_location:
            return {'type': 'ir.actions.act_window_close'}
            
        pickings = self.env['stock.picking'].search([
            ('is_book_borrowing', '=', True),
            ('move_ids.product_id', '=', self.id)
        ])
        
        action = {
            'name': f'Phiếu mượn sách: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'context': {
                'default_is_book_borrowing': True,
            },
            'domain': [('id', 'in', pickings.ids)],
        }
        
        if len(pickings) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': pickings.id,
            })
            
        return action

    def _compute_borrowing_count(self):
        """Compute number of borrowing transfers"""
        for product in self:
            borrowing_count = self.env['stock.picking'].search_count([
                ('is_book_borrowing', '=', True),
                ('move_ids.product_id', '=', product.id)
            ])
            product.borrowing_count = borrowing_count

    borrowing_count = fields.Integer(
        "Số lượt mượn",
        compute="_compute_borrowing_count",
        help="Số lượng phiếu mượn sách"
    )

    def action_print_barcode_labels(self):
        """Open wizard to select lots and print barcode labels"""
        return {
            'name': 'In nhãn mã vạch',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.barcode.wizard',
            'view_mode': 'form',
            'context': {
                'default_product_id': self.id,
            },
            'target': 'new',
        }

    def action_internal_transfer(self):
        """Open wizard for internal transfer of books"""
        return {
            'name': 'Chuyển kho nội bộ',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.transfer.wizard',
            'view_mode': 'form',
            'context': {
                'default_product_id': self.id,
            },
            'target': 'new',
        }

    def create_book_internal_transfer(self, lot_ids, source_location, dest_location, transfer_date=None):
        """Create internal transfer for moving books between locations"""
        if not transfer_date:
            transfer_date = fields.Datetime.now()
        
        # Get warehouse
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not warehouse:
            raise ValidationError(_("Không tìm thấy kho hàng!"))
        
        # Create internal transfer picking
        picking_vals = {
            'picking_type_id': warehouse.int_type_id.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': f'Chuyển kho: {self.name}',
            'scheduled_date': transfer_date,
            'move_type': 'direct',
        }
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create stock moves for each selected lot
        moves_created = []
        for lot in lot_ids:
            # Verify lot is available at source location
            quant = self.env['stock.quant'].search([
                ('lot_id', '=', lot.id),
                ('location_id', '=', source_location.id),
                ('quantity', '>', 0)
            ], limit=1)
            
            if not quant:
                continue  # Skip if lot not available at source location
                
            move_vals = {
                'name': f'Chuyển kho: {self.name} - {lot.name}',
                'product_id': self.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_id.id,
                'picking_id': picking.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'date': transfer_date,
            }
            move = self.env['stock.move'].create(move_vals)
            
            # Create move line with lot assignment
            move_line_vals = {
                'move_id': move.id,
                'product_id': self.id,
                'lot_id': lot.id,
                'quantity': 1,
                'product_uom_id': self.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'picking_id': picking.id,
            }
            self.env['stock.move.line'].create(move_line_vals)
            moves_created.append(move)
        
        if not moves_created:
            picking.unlink()
            raise ValidationError(_("Không có sách nào có thể chuyển từ vị trí nguồn đã chọn!"))
        
        # Confirm and process picking
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()
        
        return {
            'picking': picking,
            'moves_created': moves_created,
            'transferred_lots': [move.move_line_ids.lot_id for move in moves_created]
        }


    isbn = fields.Char(
        "Mã ISBN",
        help="Hiển thị số chuẩn quốc tế của sách",
    )
    catalog_num = fields.Char(
        "Số danh mục", help="Hiển thị số nhận dạng của sách"
    )
    lang = fields.Many2one("product.lang", "Ngôn ngữ", help="Ngôn ngữ của sách")
    editor_ids = fields.One2many("book.editor", "book_id", "Biên tập viên", help="Biên tập viên sách")
    author = fields.Many2one("library.author", "Tác giả", help="Tác giả thư viện")
    code = fields.Char(
        compute="_compute_product_code",
        string="Từ viết tắt",
        store=True,
        help="Mã sách",
    )
    catalog_num = fields.Char(string="Số danh mục", help="Số tham chiếu của sách")
    creation_date = fields.Datetime(
        "Ngày tạo",
        readonly=True,
        help="Ngày tạo bản ghi",
        default=lambda self: fields.Datetime.today(),
    )
    date_retour = fields.Datetime("Ngày trả", help="Ngày trả sách")
    fine_lost = fields.Float("Phí phạt mất sách", help="Nhập phí phạt khi mất sách")
    fine_late_return = fields.Float("Trả muộn", help="Nhập phí phạt trả muộn")
    tome = fields.Char(
        string="TẬP", help="Lưu trữ thông tin công việc trong nhiều tập"
    )
    nbpage = fields.Integer("Số trang", help="Nhập số trang")
    books_available = fields.Float(
        "Sách có sẵn",
        compute="_compute_books_available",
        help="Số sách có sẵn",
    )
    availability = fields.Selection(
        [("available", "Có sẵn"), ("notavailable", "Không có sẵn")],
        "Tình trạng sách",
        default="available",
        compute="_compute_books_availablity",
        help="Tình trạng có sẵn của sách",
        store=True,
    )
    back = fields.Selection(
        [("hard", "Bìa cứng"), ("paper", "Bìa mềm")],
        "Loại đóng bìa",
        help="Hiển thị loại đóng bìa sách",
        default="paper",
    )
    pocket = fields.Char("Bỏ túi", help="Kích thước bỏ túi")
    num_pocket = fields.Char(
        "Số bộ sưu tập",
        help="Hiển thị số bộ sưu tập mà sách thuộc về",
    )
    num_edition = fields.Integer("Số lần tái bản", help="Số lần tái bản của sách")
    format = fields.Char("Định dạng", help="Hình thức vật lý tổng quát của sách")
    #    price_cat = fields.Many2one('library.price.category', "Price category")
    is_ebook = fields.Boolean(
        "Là sách điện tử", help="Kích hoạt/Tắt tùy theo sách là sách điện tử hay không"
    )
    is_subscription = fields.Boolean(
        "Dựa trên đăng ký", help="Kích hoạt/tắt theo đăng ký"
    )
    subscrption_amt = fields.Float("Số tiền đăng ký", help="Số tiền đăng ký")
    attach_ebook = fields.Binary("Đính kèm sách điện tử", help="Đính kèm sách tại đây")
    day_to_return_book = fields.Integer(
        "Số ngày trả sách", help="Nhập số ngày trả sách"
    )
    attchment_ids = fields.One2many(
        "book.attachment",
        "product_id",
        "Tệp đính kèm sách",
        help="Các tệp đính kèm sách",
    )
    lot_ids = fields.One2many(
        "stock.lot",
        "product_id", 
        "Số serial sách",
        help="Danh sách số serial của sách"
    )
    total_lots = fields.Integer(
        "Tổng số serial",
        compute="_compute_lot_count",
        help="Tổng số serial đã tạo"
    )
    available_lots = fields.Integer(
        "Serial có sẵn",
        compute="_compute_lot_count", 
        help="Số serial có sẵn để mượn"
    )

    _sql_constraints = [
        (
            "unique_barcode_code",
            "unique(barcode,code)",
            "Barcode and Code must be unique across all the products!",
        )
    ]

    @api.constrains("isbn")
    def check_duplicate_isbn(self):
        """
        This method will check duplicate isbn
        Raises:
            ValidationError:
                The isbn field must be unique!
        """
        for rec in self:
            self._cr.execute(
                """
                SELECT
                    id
                FROM
                    product_product
                WHERE
                    id != %s
                AND
                    lower(isbn) = %s
                """,
                (rec.id, str(rec.isbn.lower().strip()) if rec.isbn else ""),
            )
            if self._cr.fetchone():
                raise ValidationError(_("The isbn field must be unique!"))

    @api.onchange("is_ebook", "attach_ebook")
    def onchange_availablilty(self):
        """Onchange method to define book availability"""
        if self.is_ebook and self.attach_ebook:
            self.availability = "available"

    def action_purchase_order(self):
        """Method to redirect at book order"""
        purchase_line_obj = self.env["purchase.order.line"]
        purchase = purchase_line_obj.search([("product_id", "=", self.id)])
        action = self.env.ref("purchase.purchase_form_action")
        result = action.read()[0]
        if not purchase:
            raise ValidationError(_("There is no Books Purchase !"))
        order = []
        [order.append(order_rec.order_id.id) for order_rec in purchase]
        if len(order) != 1:
            result["domain"] = "[('id', 'in', " + str(order) + ")]"
        else:
            res = self.env.ref("purchase.purchase_order_form", False)
            result["views"] = [(res and res.id or False, "form")]
            result["res_id"] = purchase.order_id.id
        return result


class BookAttachment(models.Model):
    """Defining Book Attachment."""

    _name = "book.attachment"
    _description = "Stores attachments of the book"

    name = fields.Char("Mô tả", required=True, help="Nhập mô tả")
    product_id = fields.Many2one("product.product", "Sản phẩm", help="Chọn sách")
    date = fields.Date(
        "Ngày đính kèm", required=True, default=fields.Datetime.today()
    )
    attachment = fields.Binary("Tệp đính kèm", help="Đính kèm tệp tại đây")


class LibraryAuthor(models.Model):
    _inherit = "library.author"

    book_ids = fields.Many2many(
        "product.product",
        "author_book_rel",
        "author_id",
        "product_id",
        "Sách",
        help="Các sách liên quan",
    )



class BookEditor(models.Model):
    """Book Editor Information"""

    _name = "book.editor"
    _description = "Information of Editor of the Book"

    image = fields.Binary("Hình ảnh", help="Hình ảnh sách")
    name = fields.Char("Tên", required=True, index=True, help="Tên sách")
    biography = fields.Text("Tiểu sử", help="Tiểu sử")
    note = fields.Text("Ghi chú", help="Ghi chú")
    phone = fields.Char("Số điện thoại", help="Số điện thoại")
    mobile = fields.Char("Số di động", help="Số điện thoại di động")
    fax = fields.Char("Fax", help="Số fax")
    title = fields.Many2one("res.partner.title", "Tiêu đề", help="Tiêu đề sách")
    website = fields.Char("Trang web", help="Nhập trang web tại đây")
    street = fields.Char("Đường", help="Nhập tên đường")
    street2 = fields.Char("Đường phụ", help="Nhập tên đường phụ")
    city = fields.Char("Thành phố", help="Nhập tên thành phố")
    state_id = fields.Many2one("res.country.state", "Tỉnh/Thành", help="Chọn tỉnh/thành")
    zip = fields.Char("Mã ZIP", help="Mã bưu điện")
    country_id = fields.Many2one("res.country", "Quốc gia", help="Chọn quốc gia")
    book_id = fields.Many2one("product.product", "Tham chiếu sách", help="Chọn tham chiếu sách")
