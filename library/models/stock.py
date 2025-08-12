# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _



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
