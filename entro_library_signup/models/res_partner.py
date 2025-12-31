# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Additional fields for library members
    dharma_name = fields.Char(string='Pháp Danh')
    id_card_number = fields.Char(string='CMND/CCCD')
    student_id = fields.Char(string='Mã sinh viên/học sinh')
    date_of_birth = fields.Date(string='Ngày sinh')
    vipassana_attended = fields.Boolean(
        string='Đã tham gia khóa thiền Vipassana tại TVPS',
        default=False,
        help='Đánh dấu nếu thành viên đã tham gia khóa thiền Vipassana tại TVPS'
    )
