# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class LibraryBookCreateQuantWizard(models.TransientModel):
    _name = 'library.book.create.quant.wizard'
    _description = 'Tạo bản sao sách'

    book_id = fields.Many2one(
        'library.book',
        string='Sách',
        required=True,
        readonly=True
    )
    quantity = fields.Integer(
        string='Số lượng',
        default=1,
        required=True
    )
    location_id = fields.Many2one(
        'library.location',
        string='Vị trí lưu trữ mặc định'
    )
    line_ids = fields.One2many(
        'library.book.create.quant.wizard.line',
        'wizard_id',
        string='Danh sách bản sao'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(LibraryBookCreateQuantWizard, self).default_get(fields_list)
        if self.env.context.get('active_id'):
            res['book_id'] = self.env.context['active_id']
        return res

    @api.onchange('quantity', 'book_id')
    def _onchange_quantity(self):
        """Generate suggested registration numbers based on quantity"""
        if self.quantity and self.book_id:
            # Get the last registration number for this book
            last_quant = self.env['library.book.quant'].search([
                ('book_id', '=', self.book_id.id)
            ], order='registration_number desc', limit=1)

            # Generate suggested registration numbers
            lines = []
            base_number = self._get_next_base_number(last_quant)

            for i in range(self.quantity):
                suggested_number = self._generate_registration_number(base_number, i)
                lines.append((0, 0, {
                    'registration_number': suggested_number,
                    'location_id': self.location_id.id if self.location_id else False,
                }))

            self.line_ids = lines

    def _get_next_base_number(self, last_quant):
        """Get the next base registration number"""
        if last_quant and last_quant.registration_number:
            # Try to extract number from last registration number
            import re
            match = re.search(r'(\d+)$', last_quant.registration_number)
            if match:
                base = last_quant.registration_number[:match.start()]
                next_num = int(match.group(1)) + 1
                return base, next_num
            else:
                # If no number found, append .1
                return last_quant.registration_number + '.', 1
        else:
            # Use book code or generate default
            if self.book_id.code:
                return self.book_id.code + '.', 1
            else:
                return 'Q', 1

    def _generate_registration_number(self, base_info, index):
        """Generate registration number for a specific index"""
        if isinstance(base_info, tuple):
            base, start_num = base_info
            return f"{base}{start_num + index}"
        else:
            return f"{base_info}{index + 1}"

    def action_create_quants(self):
        """Create the book quants"""
        self.ensure_one()

        if not self.line_ids:
            raise exceptions.UserError('Vui lòng tạo ít nhất một bản sao.')

        # Check for duplicate registration numbers in wizard
        reg_numbers = [line.registration_number for line in self.line_ids if line.registration_number]
        if len(reg_numbers) != len(set(reg_numbers)):
            raise exceptions.UserError('Số ĐKCB không được trùng lặp trong danh sách.')

        # Check if registration numbers already exist in database
        existing_quants = self.env['library.book.quant'].search([
            ('registration_number', 'in', reg_numbers)
        ])
        if existing_quants:
            raise exceptions.UserError(
                f'Số ĐKCB đã tồn tại: {", ".join(existing_quants.mapped("registration_number"))}'
            )

        # Create quants
        created_quants = self.env['library.book.quant']
        for line in self.line_ids:
            if not line.registration_number:
                raise exceptions.UserError('Vui lòng nhập Số ĐKCB cho tất cả các bản sao.')

            quant = self.env['library.book.quant'].create({
                'book_id': self.book_id.id,
                'registration_number': line.registration_number,
                'location_id': line.location_id.id if line.location_id else False,
                'state': 'available',
                'note': line.note,
            })
            created_quants |= quant

        # Show created quants
        return {
            'name': 'Bản sao đã tạo',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.quant',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_quants.ids)],
            'context': {'create': False}
        }


class LibraryBookCreateQuantWizardLine(models.TransientModel):
    _name = 'library.book.create.quant.wizard.line'
    _description = 'Dòng tạo bản sao sách'
    _order = 'id'

    wizard_id = fields.Many2one(
        'library.book.create.quant.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Thứ tự', default=10)
    registration_number = fields.Char(
        string='Số ĐKCB',
        required=True
    )
    location_id = fields.Many2one(
        'library.location',
        string='Vị trí lưu trữ'
    )
    note = fields.Char(string='Ghi chú')
