# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LibraryAuthor(models.Model):
    """Defining Library Author."""

    _name = "library.author"
    _description = "Author"

    name = fields.Char("Tên tác giả", required=True, help="Nhập tên tác giả thư viện")
    birth_date = fields.Date("Ngày sinh", help="Nhập ngày sinh")
    death_date = fields.Date("Ngày mất", help="Nhập ngày mất")
    biography = fields.Text("Tiểu sử", help="Nhập tiểu sử")
    note = fields.Text("Ghi chú", help="Nhập ghi chú")
    editor_ids = fields.Many2many(
        "res.partner",
        "author_editor_rel",
        "author_id",
        "parent_id",
        "Biên tập viên",
        help="Chọn biên tập viên",
    )

    _sql_constraints = [
        (
            "name_uniq",
            "unique (name)",
            "Tên của tác giả phải là duy nhất!",
        )
    ]