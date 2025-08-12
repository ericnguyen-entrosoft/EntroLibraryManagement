# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class LibraryBookBorrowWizard(models.TransientModel):
    """Wizard to borrow books"""
    
    _name = "library.book.borrow.wizard"
    _description = "Mượn sách từ thư viện"

    product_id = fields.Many2one(
        "product.product",
        "Sách", 
        required=True,
        help="Sách cần mượn"
    )
    lot_id = fields.Many2one(
        "stock.lot",
        "Số serial sách",
        required=True,
        help="Chọn số serial cụ thể của sách"
    )
    library_card_id = fields.Many2one(
        "library.card",
        "Thẻ thư viện",
        required=True,
        help="Thẻ thư viện của người mượn"
    )
    borrower_name = fields.Char(
        "Tên người mượn",
        required=True,
        help="Tên của người mượn sách"
    )
    borrower_info = fields.Text(
        "Thông tin người mượn",
        help="Thông tin liên hệ hoặc ghi chú về người mượn"
    )
    due_date = fields.Date(
        "Hạn trả sách",
        required=True,
        default=lambda self: fields.Date.today() + timedelta(days=14),
        help="Ngày hạn trả sách"
    )
    available_lot_ids = fields.Many2many(
        "stock.lot",
        compute="_compute_available_lot_ids",
        help="Serial numbers available for borrowing"
    )

    @api.depends('product_id')
    def _compute_available_lot_ids(self):
        """Compute available lots for borrowing"""
        for record in self:
            if record.product_id:
                # Get available lots for this product (not in borrowing location)
                borrowing_location = self.env.ref('library.stock_location_library_borrowing', raise_if_not_found=False)
                if borrowing_location:
                    available_lots = self.env['stock.quant'].search([
                        ('product_id', '=', record.product_id.id),
                        ('quantity', '>', 0),
                        ('location_id.usage', '=', 'internal'),
                        ('location_id', '!=', borrowing_location.id),
                        ('lot_id', '!=', False)
                    ]).mapped('lot_id')
                    record.available_lot_ids = available_lots
                else:
                    # If no borrowing location, show all available lots
                    available_lots = self.env['stock.quant'].search([
                        ('product_id', '=', record.product_id.id),
                        ('quantity', '>', 0),
                        ('location_id.usage', '=', 'internal'),
                        ('lot_id', '!=', False)
                    ]).mapped('lot_id')
                    record.available_lot_ids = available_lots
            else:
                record.available_lot_ids = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Clear lot_id when product changes"""
        if self.product_id:
            self.lot_id = False

    @api.onchange('library_card_id')
    def _onchange_library_card_id(self):
        """Auto-fill borrower info from library card"""
        if self.library_card_id:
            card = self.library_card_id
            self.borrower_name = card.card_name or ''
            # Get contact info from partner if linked
            if card.partner_id:
                contact_info = []
                if card.partner_id.phone:
                    contact_info.append(f"ĐT: {card.partner_id.phone}")
                if card.partner_id.email:
                    contact_info.append(f"Email: {card.partner_id.email}")
                self.borrower_info = '\n'.join(contact_info)

    @api.constrains('due_date')
    def _check_due_date(self):
        for record in self:
            if record.due_date <= fields.Date.today():
                raise ValidationError(_("Hạn trả sách phải sau ngày hôm nay!"))

    def action_borrow_book(self):
        """Process book borrowing"""
        self.ensure_one()
        
        if not self.product_id or not self.lot_id:
            raise ValidationError(_("Vui lòng chọn sách và số serial!"))
        
        if not self.borrower_name:
            raise ValidationError(_("Vui lòng nhập tên người mượn!"))
        
        # Create borrowing picking
        result = self.product_id.create_book_borrowing(
            self.lot_id.id,
            self.borrower_name,
            self.borrower_info or '',
            self.due_date,
            self.library_card_id
        )
        
        # Show success message
        message = _("Đã tạo thành công phiếu mượn sách!\nSố serial: %s\nNgười mượn: %s\nHạn trả: %s") % (
            self.lot_id.name,
            self.borrower_name,
            self.due_date
        )
        
        # Return action to view the created picking
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phiếu mượn sách',
            'res_model': 'stock.picking',
            'res_id': result['picking'].id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'message': message
            }
        }