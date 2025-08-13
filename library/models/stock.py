# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError



class StockMove(models.Model):
    _inherit = "stock.move"

    origin_ref = fields.Char(string="Origin")

    # Note: Serial assignment is now handled directly in the receipt creation process
    # This provides better control and follows standard Odoo receipt workflow


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _order = "create_date desc"

    date_done = fields.Datetime("Picking date")
    library_card_id = fields.Many2one(
        "library.card",
        "Thẻ thư viện",
        help="Thẻ thư viện được sử dụng cho việc mượn sách"
    )
    borrower_name = fields.Char(
        "Tên người mượn",
        help="Tên người mượn sách"
    )
    borrower_info = fields.Text(
        "Thông tin người mượn",
        help="Thông tin liên hệ người mượn"
    )
    due_date = fields.Date(
        "Hạn trả sách",
        help="Ngày hạn trả sách"
    )
    is_book_borrowing = fields.Boolean(
        "Phiếu mượn sách",
        default=False,
        help="Đánh dấu đây là phiếu mượn sách"
    )
    is_borrowing_transfer = fields.Boolean(
        "Phiếu chuyển mượn",
        default=False,
        help="Đánh dấu đây là phiếu chuyển mượn sách"
    )

class StockLot(models.Model):
    _inherit = "stock.lot"

    library_barcode = fields.Char(
        "Mã vạch thư viện",
        compute="_compute_library_barcode",
        store=True,
        help="Mã vạch được tạo theo định dạng: Mã kho + Số serial + Mã vị trí"
    )

    @api.depends('name')
    def _compute_library_barcode(self):
        """Generate library barcode with format: warehouse_code + serial + location_code"""
        for lot in self:
            if lot.name and lot.product_id:
                # Get current location of the lot
                quant = self.env['stock.quant'].search([
                    ('lot_id', '=', lot.id),
                    ('quantity', '>', 0),
                    ('location_id.usage', 'in', ['internal', 'transit'])
                ], limit=1)
                
                if quant and quant.location_id:
                    # Get warehouse and location codes
                    warehouse = quant.location_id.warehouse_id
                    location = quant.location_id
                    
                    # Use warehouse and location codes, fallback to default if not set
                    warehouse_code = warehouse.code if warehouse and warehouse.code else 'WH'
                    location_code = location.barcode if location.barcode else location.name[:4].upper()
                    
                    # Generate barcode: warehouse_code + serial + location_code
                    lot.library_barcode = f"{warehouse_code}{lot.name}{location_code}"
                else:
                    # If no location found, use default codes
                    lot.library_barcode = f"WH{lot.name}LOC"
            else:
                lot.library_barcode = ""

    def action_print_barcode_label(self):
        """Print barcode label for the lot"""
        self.ensure_one()
        return self.env.ref('library.action_report_lot_barcode_label').report_action(self)
