# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Additional fields for library members
    id_card_number = fields.Char(string='CMND/CCCD')
    student_id = fields.Char(string='Mã sinh viên/học sinh')
    date_of_birth = fields.Date(string='Ngày sinh')
