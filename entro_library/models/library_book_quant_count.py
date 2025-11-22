# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class LibraryBookQuantCount(models.Model):
    _name = 'library.book.quant.count'
    _description = 'Kiểm kê bản sao sách'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'count_date desc, name desc'

    name = fields.Char(
        string='Số phiếu',
        required=True,
        copy=False,
        readonly=True,
        default='/',
        tracking=True
    )
    count_date = fields.Date(
        string='Ngày kiểm kê',
        default=fields.Date.today,
        required=True,
        tracking=True,
        states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )
    location_id = fields.Many2one(
        'library.location',
        string='Vị trí lưu trữ',
        help='Để trống để kiểm kê tất cả vị trí',
        states={'in_progress': [('readonly', True)], 'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )
    category_id = fields.Many2one(
        'library.category',
        string='Nhóm sách',
        help='Để trống để kiểm kê tất cả nhóm',
        states={'in_progress': [('readonly', True)], 'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )
    state_filter = fields.Selection([
        ('available', 'Có sẵn'),
        ('borrowed', 'Đang mượn'),
        ('reserved', 'Đã đặt trước'),
        ('maintenance', 'Bảo trì'),
        ('lost', 'Mất'),
        ('damaged', 'Hư hỏng')
    ],
        string='Trạng thái',
        help='Để trống để kiểm kê tất cả trạng thái',
        states={'in_progress': [('readonly', True)], 'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('in_progress', 'Đang kiểm kê'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy')
    ],
        string='Trạng thái',
        default='draft',
        required=True,
        tracking=True
    )
    line_ids = fields.One2many(
        'library.book.quant.count.line',
        'count_id',
        string='Chi tiết kiểm kê',
        states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )
    responsible_id = fields.Many2one(
        'res.users',
        string='Người phụ trách',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )
    note = fields.Text(
        string='Ghi chú',
        states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('library.book.quant.count') or '/'
        return super(LibraryBookQuantCount, self).create(vals)

    def action_start_count(self):
        """Generate count lines based on filters"""
        self.ensure_one()
        if self.state != 'draft':
            raise exceptions.UserError('Chỉ có thể bắt đầu kiểm kê từ trạng thái Nháp!')

        # Build domain for filtering quants
        domain = [('active', '=', True)]
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
        if self.category_id:
            domain.append(('category_id', '=', self.category_id.id))
        if self.state_filter:
            domain.append(('state', '=', self.state_filter))

        # Find quants matching the filters
        quants = self.env['library.book.quant'].search(domain)

        if not quants:
            raise exceptions.UserError('Không tìm thấy bản sao sách nào phù hợp với bộ lọc!')

        # Clear existing lines
        self.line_ids.unlink()

        # Create count lines
        lines = []
        for quant in quants:
            lines.append((0, 0, {
                'quant_id': quant.id,
                'theory_qty': quant.quantity,
                'counted_qty': 0,
            }))

        self.write({
            'line_ids': lines,
            'state': 'in_progress'
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tạo {len(quants)} dòng kiểm kê',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_validate_count(self):
        """Apply counted quantities to quants"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise exceptions.UserError('Chỉ có thể xác nhận kiểm kê từ trạng thái Đang kiểm kê!')

        # Apply counted quantities
        for line in self.line_ids:
            if line.difference != 0:
                line.quant_id.quantity = line.counted_qty

        self.state = 'done'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': 'Kiểm kê đã được xác nhận và số lượng đã được cập nhật',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Cancel the count"""
        self.ensure_one()
        if self.state == 'done':
            raise exceptions.UserError('Không thể hủy phiếu kiểm kê đã hoàn thành!')

        self.state = 'cancelled'

    def action_reset_to_draft(self):
        """Reset to draft and clear lines"""
        self.ensure_one()
        if self.state == 'done':
            raise exceptions.UserError('Không thể chuyển về Nháp phiếu kiểm kê đã hoàn thành!')

        self.line_ids.unlink()
        self.state = 'draft'
