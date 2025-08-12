# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class LibraryBookReceiptWizard(models.TransientModel):
    """Wizard to create receipt for new books"""
    
    _name = "library.book.receipt.wizard"
    _description = "Tạo phiếu nhập sách mới"

    product_id = fields.Many2one(
        "product.product",
        "Sách", 
        required=True,
        help="Sách cần thêm"
    )
    quantity = fields.Integer(
        "Số lượng",
        required=True,
        default=1,
        help="Số lượng sách cần nhập"
    )
    receiving_date = fields.Date(
        "Ngày nhập kho",
        required=True,
        default=fields.Date.today(),
        help="Ngày nhập sách vào thư viện"
    )
    location_id = fields.Many2one(
        "stock.location",
        "Vị trí nhập kho",
        required=True,
        domain="[('usage', '=', 'internal')]",
        help="Vị trí trong kho để nhập sách"
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_("Số lượng phải lớn hơn 0!"))

    def action_create_receipt(self):
        """Create receipt with automatic serial generation"""
        self.ensure_one()
        
        if not self.product_id:
            raise ValidationError(_("Vui lòng chọn sách!"))
        
        # Create receipt with serials
        result = self.product_id.create_book_receipt(
            self.quantity, 
            self.receiving_date,
            self.location_id
        )
        
        # Show success message with serial numbers
        serial_numbers = result['serial_numbers']
        message = _("Đã tạo thành công phiếu nhập với %d số serial:\n%s") % (
            len(serial_numbers), 
            '\n'.join(serial_numbers)
        )
        
        # Return action to view the created receipt
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phiếu nhập sách',
            'res_model': 'stock.picking',
            'res_id': result['picking'].id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'message': message
            }
        }