# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductPublicCategory(models.Model):
    _name = "product.public.category"
    _inherit = ["website.seo.metadata", "website.multi.mixin"]
    _description = "Website Book Category"
    _order = "sequence ASC, name ASC"

    name = fields.Char(required=True, translate=True)
    parent_id = fields.Many2one('product.public.category', 'Parent Category', index=True)
    child_id = fields.One2many('product.public.category', 'parent_id', 'Children Categories')
    parents_and_self = fields.Many2many('product.public.category', compute='_compute_parents_and_self')
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of book categories.")
    website_description = fields.Html('Category Description', sanitize_attributes=False, translate=True)
    product_tmpl_ids = fields.Many2many('product.template', relation='product_public_category_product_template_rel')

    @api.depends('parent_id')
    def _compute_parents_and_self(self):
        for category in self:
            if category.parent_id:
                category.parents_and_self = category.parent_path.split('/')[:-1]
            else:
                category.parents_and_self = category

    @api.constrains('parent_id')
    def check_parent_id(self):
        if not self._check_recursion():
            raise ValueError('Error ! You cannot create recursive categories.')

    def name_get(self):
        res = []
        for category in self:
            names = [category.name]
            parent_category = category.parent_id
            while parent_category:
                names.append(parent_category.name)
                parent_category = parent_category.parent_id
            res.append((category.id, ' / '.join(reversed(names))))
        return res


class ProductTemplate(models.Model):
    _inherit = "product.template"

    public_categ_ids = fields.Many2many(
        'product.public.category',
        relation='product_public_category_product_template_rel',
        string='Website Book Categories'
    )
    website_ribbon_id = fields.Many2one('product.ribbon', 'Ribbon')
    website_sequence = fields.Integer('Website Sequence', default=10000)
    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_published = fields.Boolean('Published on Website', default=False, copy=False)
    is_published = fields.Boolean('Is Published', related='website_published', readonly=False)

    def _default_website_meta(self):
        res = super()._default_website_meta()
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.description_sale
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = self.env['website'].get_cdn_url(f'/web/image/product.template/{self.id}/image_1920')
        return res

    def _compute_website_url(self):
        super()._compute_website_url()
        for product in self:
            product.website_url = f"/library/book/{product.id}"