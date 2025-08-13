# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class LibraryBookBarcodeWizard(models.TransientModel):
    """Wizard to select lots and print barcode labels"""
    
    _name = "library.book.barcode.wizard"
    _description = "In nhãn mã vạch sách"

    product_id = fields.Many2one(
        "product.product",
        "Sách", 
        required=True,
        help="Sách cần in nhãn"
    )
    lot_ids = fields.Many2many(
        "stock.lot",
        "book_barcode_wizard_lot_rel",
        "wizard_id",
        "lot_id",
        "Số serial",
        help="Chọn các số serial cần in nhãn"
    )
    all_lots = fields.Boolean(
        "In tất cả",
        default=False,
        help="In nhãn cho tất cả số serial của sách này"
    )
    available_lot_ids = fields.Many2many(
        "stock.lot",
        compute="_compute_available_lot_ids",
        help="Tất cả số serial có sẵn"
    )

    @api.depends('product_id')
    def _compute_available_lot_ids(self):
        """Compute available lots for this product"""
        for record in self:
            if record.product_id:
                lots = self.env['stock.lot'].search([
                    ('product_id', '=', record.product_id.id)
                ])
                record.available_lot_ids = lots
            else:
                record.available_lot_ids = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Clear lot selection when product changes"""
        if self.product_id:
            self.lot_ids = False

    @api.onchange('all_lots')
    def _onchange_all_lots(self):
        """Select all lots when all_lots is checked"""
        if self.all_lots and self.available_lot_ids:
            self.lot_ids = self.available_lot_ids
        elif not self.all_lots:
            self.lot_ids = False

    def action_print_labels(self):
        """Print barcode labels for selected lots"""
        self.ensure_one()
        
        lots_to_print = self.lot_ids
        if self.all_lots:
            lots_to_print = self.available_lot_ids
            
        if not lots_to_print:
            raise ValidationError(_("Vui lòng chọn ít nhất một số serial để in!"))
        
        # Return report action for selected lots
        return self.env.ref('library.action_report_lot_barcode_label').report_action(lots_to_print)