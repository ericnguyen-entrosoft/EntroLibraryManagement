# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CharacterMapping(models.Model):
    _name = 'character.mapping'
    _description = 'Ánh xạ ký tự'
    _order = 'van, ma_so'

    van = fields.Char(string='Vần', required=True, index=True)
    ma_so = fields.Char(string='Mã số', required=True, index=True)
    language_id = fields.Many2one('res.lang', string='Ngôn ngữ', required=True)

    note = fields.Text(string='Ghi chú')
    active = fields.Boolean(string='Hoạt động', default=True)

    _sql_constraints = [
        ('van_ma_so_lang_unique',
         'unique(van, ma_so, language_id)',
         'Vần, Mã số và Ngôn ngữ phải duy nhất!')
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.ma_so}] {record.van}"
            if record.language_id:
                name += f" ({record.language_id.name})"
            result.append((record.id, name))
        return result
