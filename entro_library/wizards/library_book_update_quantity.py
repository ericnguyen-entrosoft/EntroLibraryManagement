from datetime import date

from odoo import models, fields, api, exceptions


class LibraryBookUpdateQuantity(models.TransientModel):
    _name = 'library.book.update.quantity'
    _description = 'Cập nhật số lượng bản sao sách'

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
        string='Vị trí lưu trữ mặc định',
        domain=[('location_type', '=', 'storage')]
    )
    line_ids = fields.One2many(
        'library.book.update.quantity.line',
        'wizard_id',
        string='Danh sách bản sao'
    )
    use_multiple_locations = fields.Boolean(
        string='Phân bổ nhiều vị trí',
        default=False,
        help='Phân bổ số lượng cho nhiều vị trí khác nhau'
    )
    allocation_ids = fields.One2many(
        'library.book.update.quantity.allocation',
        'wizard_id',
        string='Phân bổ vị trí'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(LibraryBookUpdateQuantity, self).default_get(fields_list)
        if self.env.context.get('active_id'):
            res['book_id'] = self.env.context['active_id']
        return res

    @api.onchange('quantity', 'book_id', 'use_multiple_locations', 'allocation_ids', 'allocation_ids.quantity', 'allocation_ids.location_id')
    def _onchange_quantity(self):
        """Generate suggested registration numbers based on quantity"""
        if self.book_id:
            # Get storage locations that are NOT skip_register_number
            storage_locations = self.env['library.location'].search([
                ('location_type', '=', 'storage'),
                ('skip_register_number', '=', False)
            ])

            # Get the last registration number for this book in storage locations only
            last_quant = self.env['library.book.quant'].search([
                ('book_id', '=', self.book_id.id),
                ('location_id', 'in', storage_locations.ids)
            ], order='registration_number desc', limit=1)

            # Generate suggested registration numbers
            lines = [(5, 0, 0)]
            base_number = self._get_next_base_number(last_quant)

            if self.use_multiple_locations and self.allocation_ids:
                # Allocate based on direct quantity input per location
                index = 0
                for allocation in self.allocation_ids:
                    qty_for_location = allocation.quantity
                    if qty_for_location <= 0:
                        continue

                    # Check if location requires registration number
                    skip_reg_number = allocation.location_id.skip_register_number if allocation.location_id else False

                    if skip_reg_number:
                        # Create single line with quantity for this location
                        lines.append((0, 0, {
                            'registration_number': '',
                            'code_registration_number': '',
                            'location_id': allocation.location_id.id,
                            'quantity': qty_for_location,
                        }))
                    else:
                        # Create individual lines for each quant
                        for i in range(qty_for_location):
                            suggested_number, code_suggested_number = self._generate_registration_number(
                                base_number, self.book_id.category_id.code, index
                            )
                            lines.append((0, 0, {
                                'registration_number': suggested_number,
                                'code_registration_number': code_suggested_number,
                                'location_id': allocation.location_id.id,
                                'quantity': 1,
                            }))
                            index += 1
            else:
                # Default behavior: use default location
                if not self.quantity:
                    self.line_ids = lines
                    return

                skip_reg_number = self.location_id.skip_register_number if self.location_id else False

                if skip_reg_number:
                    # Create single line with total quantity
                    lines.append((0, 0, {
                        'registration_number': '',
                        'code_registration_number': '',
                        'location_id': self.location_id.id if self.location_id else False,
                        'quantity': self.quantity,
                    }))
                else:
                    # Create individual lines for each quant
                    for i in range(self.quantity):
                        suggested_number, code_suggested_number = self._generate_registration_number(
                            base_number, self.book_id.category_id.code, i
                        )
                        lines.append((0, 0, {
                            'registration_number': suggested_number,
                            'code_registration_number': code_suggested_number,
                            'location_id': self.location_id.id if self.location_id else False,
                            'quantity': 1,
                        }))

            self.line_ids = lines

    def _get_next_base_number(self, last_quant):
        """Get the next base registration number based on max existing number
        Format: YY.NNNNNN where YY is 2-digit year and NNNNNN is the next quant number
        """
        # Get 2-digit year from registration_date
        if self.book_id.registration_date:
            year = self.book_id.registration_date.year % 100  # Get last 2 digits
        else:
            year = date.today().year % 100

        # Extract numeric part directly in SQL and get maximum
        self.env.cr.execute("""
            SELECT CAST(SPLIT_PART(registration_number, '.', 2) AS INTEGER) as num
            FROM library_book_quant
            WHERE registration_number IS NOT NULL
            AND registration_number ~ '^[0-9]+\.[0-9]+$'
            ORDER BY num DESC
            LIMIT 1
        """)

        result = self.env.cr.fetchone()
        next_quant_number = (result[0] + 1) if result and result[0] else 1

        return year, next_quant_number

    def _generate_registration_number(self, base_info, code_category, index):
        """Generate registration number for a specific index
        Format: YY.NNNNNN where YY is 2-digit year and NNNNNN is padded with zeros
        Example: 25.001001 for year 2025, quant 1001
        """
        year, start_num = base_info
        current_num = start_num + index
        # Pad with zeros to 6 digits
        return f"{year:02d}.{current_num:06d}", f"{code_category}.{current_num:06d}"

    def action_create_quants(self):
        """Create the book quants"""
        self.ensure_one()

        if not self.line_ids:
            raise exceptions.UserError('Vui lòng tạo ít nhất một bản sao.')

        # Check for duplicate registration numbers in wizard (skip empty ones)
        reg_numbers = [line.registration_number for line in self.line_ids if line.registration_number]
        if reg_numbers and len(reg_numbers) != len(set(reg_numbers)):
            raise exceptions.UserError('Số ĐKCB không được trùng lặp trong danh sách.')

        # Check if registration numbers already exist in database
        if reg_numbers:
            existing_quants = self.env['library.book.quant'].search([
                ('registration_number', 'in', reg_numbers)
            ])
            if existing_quants:
                raise exceptions.UserError(
                    f'Số ĐKCB đã tồn tại: {", ".join(existing_quants.mapped("registration_number"))}'
                )

        # Check if this book already has a "no_borrow" quant
        no_borrow_type = self.env.ref('entro_library.quant_type_no_borrow', raise_if_not_found=False)
        can_borrow_type = self.env.ref('entro_library.quant_type_can_borrow', raise_if_not_found=False)

        has_no_borrow_quant = self.env['library.book.quant'].search_count([
            ('book_id', '=', self.book_id.id),
            ('quant_type_id', '=', no_borrow_type.id if no_borrow_type else False)
        ]) > 0

        # Create quants
        created_quants = self.env['library.book.quant']
        is_first_quant = not has_no_borrow_quant  # Flag to track if we need to create first no_borrow quant

        for line in self.line_ids:
            # Check if registration number is required (only if location doesn't skip it)
            location_skip_reg = line.location_id.skip_register_number if line.location_id else False

            if not line.registration_number and not location_skip_reg:
                raise exceptions.UserError('Vui lòng nhập Số ĐKCB cho tất cả các bản sao (trừ vị trí không yêu cầu).')

            # Logic: First quant for the book should be no_borrow, all subsequent quants are can_borrow
            # If no_borrow quant already exists, all new quants are can_borrow
            if is_first_quant:
                quant_type_id = no_borrow_type
                is_first_quant = False  # Only first quant is no_borrow
            else:
                quant_type_id = can_borrow_type

            quant = self.env['library.book.quant'].create({
                'book_id': self.book_id.id,
                'registration_number': line.registration_number if line.registration_number else False,
                'code_registration_number': line.code_registration_number if line.code_registration_number else False,
                'location_id': line.location_id.id if line.location_id else False,
                'state': 'available',
                'quant_type_id': quant_type_id.id if quant_type_id else False,
                'quantity': line.quantity,
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


class LibraryBookUpdateQuantityLine(models.TransientModel):
    _name = 'library.book.update.quantity.line'
    _description = 'Dòng cập nhật số lượng bản sao sách'
    _order = 'id'

    wizard_id = fields.Many2one(
        'library.book.update.quantity',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    registration_number = fields.Char(
        string='Số ĐKCB',
        required=False
    )
    code_registration_number = fields.Char(
        string='Mã ĐKCB theo danh mục',
        readonly=False
    )
    location_id = fields.Many2one(
        'library.location',
        string='Vị trí lưu trữ',
        domain=[('location_type', '=', 'storage')]
    )
    quantity = fields.Integer(
        string='Số lượng',
        default=1,
        required=True
    )


class LibraryBookUpdateQuantityAllocation(models.TransientModel):
    _name = 'library.book.update.quantity.allocation'
    _description = 'Phân bổ vị trí cho bản sao sách'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'library.book.update.quantity',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Thứ tự', default=10)
    location_id = fields.Many2one(
        'library.location',
        string='Vị trí lưu trữ',
        required=True,
        domain=[('location_type', '=', 'storage')]
    )
    quantity = fields.Integer(
        string='Số lượng',
        required=True,
        default=0,
        help='Số lượng bản sao cho vị trí này'
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity < 0:
                raise exceptions.UserError('Số lượng không được âm!')
