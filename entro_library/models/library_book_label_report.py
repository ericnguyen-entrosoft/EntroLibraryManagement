# -*- coding: utf-8 -*-
from odoo import models


class LibraryBookLabelReportCustom(models.AbstractModel):
    _name = 'report.entro_library.report_book_label_custom'
    _description = 'Library Book Label Report Custom'

    def _get_report_values(self, docids, data):
        """
        Process the data parameter and make it available to the template
        """
        quant_quantities = data.get('quant_quantities', {}) if data else {}

        # Ensure all quant IDs are integers
        quant_quantities_int = {}
        for quant_id, quantity in quant_quantities.items():
            quant_quantities_int[int(quant_id)] = quantity

        return {
            'doc_ids': docids,
            'doc_model': 'library.book.label.wizard',
            'docs': self.env['library.book.label.wizard'].browse(docids),
            'data': {'quant_quantities': quant_quantities_int},
            'quant_quantities': quant_quantities_int,
        }


class LibraryBookLabelReportDDC(models.AbstractModel):
    _name = 'report.entro_library.report_book_label_ddc'
    _description = 'Library Book Label Report DDC'

    def _get_report_values(self, docids, data):
        """
        Process the data parameter and make it available to the template
        """
        quant_quantities = data.get('quant_quantities', {}) if data else {}

        # Ensure all quant IDs are integers
        quant_quantities_int = {}
        for quant_id, quantity in quant_quantities.items():
            quant_quantities_int[int(quant_id)] = quantity

        return {
            'doc_ids': docids,
            'doc_model': 'library.book.label.wizard',
            'docs': self.env['library.book.label.wizard'].browse(docids),
            'data': {'quant_quantities': quant_quantities_int},
            'quant_quantities': quant_quantities_int,
        }
