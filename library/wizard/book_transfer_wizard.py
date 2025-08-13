# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class LibraryBookTransferWizard(models.TransientModel):
    """Wizard for internal transfer of books between locations"""
    
    _name = "library.book.transfer.wizard"
    _description = "Chuyển kho nội bộ sách"

    product_id = fields.Many2one(
        "product.product",
        "Sách", 
        required=True,
        help="Sách cần chuyển kho"
    )
    source_location_id = fields.Many2one(
        "stock.location",
        "Vị trí nguồn",
        required=True,
        domain="[('usage', '=', 'internal')]",
        help="Vị trí hiện tại của sách"
    )
    dest_location_id = fields.Many2one(
        "stock.location",
        "Vị trí đích",
        required=True,
        domain="[('usage', '=', 'internal')]",
        help="Vị trí muốn chuyển sách đến"
    )
    lot_ids = fields.Many2many(
        "stock.lot",
        "book_transfer_wizard_lot_rel",
        "wizard_id",
        "lot_id",
        "Số serial",
        help="Chọn các số serial cần chuyển kho"
    )
    transfer_date = fields.Datetime(
        "Ngày chuyển kho",
        required=True,
        default=fields.Datetime.now(),
        help="Ngày thực hiện chuyển kho"
    )
    available_lot_ids = fields.Many2many(
        "stock.lot",
        compute="_compute_available_lot_ids",
        help="Số serial có sẵn tại vị trí nguồn"
    )
    all_lots = fields.Boolean(
        "Chuyển tất cả",
        default=False,
        help="Chuyển tất cả số serial có tại vị trí nguồn"
    )

    @api.depends('product_id', 'source_location_id')
    def _compute_available_lot_ids(self):
        """Compute available lots at source location"""
        for record in self:
            if record.product_id and record.source_location_id:
                # Find lots available at the source location
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', record.product_id.id),
                    ('location_id', '=', record.source_location_id.id),
                    ('quantity', '>', 0),
                    ('lot_id', '!=', False)
                ])
                record.available_lot_ids = quants.mapped('lot_id')
            else:
                record.available_lot_ids = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Clear selections when product changes"""
        if self.product_id:
            self.lot_ids = False
            self.source_location_id = False
            self.dest_location_id = False

    @api.onchange('source_location_id')
    def _onchange_source_location_id(self):
        """Clear lot selection when source location changes"""
        if self.source_location_id:
            self.lot_ids = False
            self.all_lots = False

    @api.onchange('all_lots')
    def _onchange_all_lots(self):
        """Select all available lots when all_lots is checked"""
        if self.all_lots and self.available_lot_ids:
            self.lot_ids = self.available_lot_ids
        elif not self.all_lots:
            self.lot_ids = False

    @api.constrains('source_location_id', 'dest_location_id')
    def _check_locations(self):
        for record in self:
            if record.source_location_id == record.dest_location_id:
                raise ValidationError(_("Vị trí nguồn và vị trí đích không thể giống nhau!"))

    def action_transfer_books(self):
        """Execute internal transfer"""
        self.ensure_one()
        
        lots_to_transfer = self.lot_ids
        if self.all_lots:
            lots_to_transfer = self.available_lot_ids
            
        if not lots_to_transfer:
            raise ValidationError(_("Vui lòng chọn ít nhất một số serial để chuyển kho!"))
        
        # Create internal transfer
        result = self.product_id.create_book_internal_transfer(
            lots_to_transfer,
            self.source_location_id,
            self.dest_location_id,
            self.transfer_date
        )
        
        # Show success message
        transferred_count = len(result['transferred_lots'])
        message = _("Đã chuyển thành công %d cuốn sách từ %s đến %s") % (
            transferred_count,
            self.source_location_id.name,
            self.dest_location_id.name
        )
        
        # Return action to view the created transfer
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phiếu chuyển kho',
            'res_model': 'stock.picking',
            'res_id': result['picking'].id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'message': message
            }
        }