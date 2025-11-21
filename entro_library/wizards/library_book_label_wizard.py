# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class LibraryBookLabelWizard(models.TransientModel):
    _name = 'library.book.label.wizard'
    _description = 'In nhãn sách'

    print_format = fields.Selection([
        ('custom', 'Nhãn ĐKCB'),
        ('ddc', 'Nhãn DDC'),
    ], string='Format', default='custom', required=True)

    quant_line_ids = fields.One2many(
        'library.book.label.line',
        'wizard_id',
        string='Bản sao sách'
    )

    custom_quantity = fields.Integer(
        string='Custom Quantity',
        help='If set, this quantity will be used for all selected book quants'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(LibraryBookLabelWizard, self).default_get(fields_list)

        quant_ids = self.env.context.get('active_ids', [])
        if quant_ids:
            quants = self.env['library.book.quant'].browse(quant_ids)
            lines = []
            for quant in quants:
                lines.append((0, 0, {
                    'quant_id': quant.id,
                    'quantity': 1,
                }))
            res['quant_line_ids'] = lines

        return res

    def action_open_wizard(self):
        """Open the wizard form view"""
        return {
            'name': 'In nhãn sách',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.label.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def process(self):
        """Generate and print the labels"""
        self.ensure_one()

        # Get all quants with their quantities
        quant_quantities = {}
        for line in self.quant_line_ids:
            if line.quantity > 0:
                if self.custom_quantity:
                    quant_quantities[line.quant_id.id] = self.custom_quantity
                else:
                    quant_quantities[line.quant_id.id] = line.quantity

        if not quant_quantities:
            raise exceptions.UserError('Vui lòng chọn ít nhất một bản sao để in.')

        # Return report action
        xml_id = 'entro_library.action_report_book_label_' + self.print_format.replace('x', '_').replace('price', 'price')

        # Map print_format to report xml_id
        report_map = {
            'custom': 'entro_library.action_report_book_label_custom',
            'ddc': 'entro_library.action_report_book_label_ddc',
        }

        report_xml_id = report_map.get(self.print_format, 'entro_library.action_report_book_label_custom')

        return self.env.ref(report_xml_id).report_action(
            self,
            data={'quant_quantities': quant_quantities}
        )


class LibraryBookLabelLine(models.TransientModel):
    _name = 'library.book.label.line'
    _description = 'Dòng in nhãn sách'
    _order = 'quant_id'

    wizard_id = fields.Many2one(
        'library.book.label.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    quant_id = fields.Many2one(
        'library.book.quant',
        string='Bản sao sách',
        required=True
    )
    quantity = fields.Integer(
        string='Số lượng nhãn',
        default=1,
        required=True
    )

    # Related fields for display
    registration_number = fields.Char(
        related='quant_id.registration_number',
        string='Số ĐKCB',
        readonly=True
    )
    book_name = fields.Char(
        related='quant_id.book_id.name',
        string='Tên sách',
        readonly=True
    )
