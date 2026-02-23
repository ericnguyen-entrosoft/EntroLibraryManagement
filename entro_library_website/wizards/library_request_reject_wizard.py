# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class LibraryRequestRejectWizard(models.TransientModel):
    _name = 'library.request.reject.wizard'
    _description = 'Wizard từ chối yêu cầu bổ sung tài liệu'

    request_id = fields.Many2one(
        'library.resource.request',
        string='Yêu cầu',
        required=True,
        ondelete='cascade'
    )

    rejection_reason = fields.Text(
        string='Lý do từ chối',
        required=True,
        help='Giải thích rõ lý do từ chối để người yêu cầu hiểu'
    )

    def action_confirm_reject(self):
        """Xác nhận từ chối yêu cầu"""
        self.ensure_one()
        if not self.rejection_reason:
            raise UserError('Vui lòng nhập lý do từ chối!')

        self.request_id.do_reject(self.rejection_reason)

        return {'type': 'ir.actions.act_window_close'}
