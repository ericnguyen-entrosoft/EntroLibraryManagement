from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_book = fields.Boolean('Is a Book', default=False)
    isbn = fields.Char('ISBN', size=13, help="International Standard Book Number")
    author = fields.Char('Author')
    publisher = fields.Char('Publisher')
    publication_date = fields.Date('Publication Date')
    genre = fields.Selection([
        ('fiction', 'Fiction'),
        ('non_fiction', 'Non-Fiction'),
        ('science', 'Science'),
        ('technology', 'Technology'),
        ('history', 'History'),
        ('biography', 'Biography'),
        ('children', 'Children'),
        ('education', 'Education'),
        ('reference', 'Reference'),
        ('other', 'Other')
    ], string='Genre')
    pages = fields.Integer('Number of Pages')
    language = fields.Selection([
        ('en', 'English'),
        ('vi', 'Vietnamese'),
        ('fr', 'French'),
        ('de', 'German'),
        ('es', 'Spanish'),
        ('zh', 'Chinese'),
        ('ja', 'Japanese'),
        ('ko', 'Korean'),
        ('other', 'Other')
    ], string='Language', default='en')
    
    book_condition = fields.Selection([
        ('new', 'New'),
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor')
    ], string='Book Condition', default='new')
    
    library_location = fields.Char('Library Location', help="Shelf/Section location in library")
    is_available = fields.Boolean('Available for Borrowing', default=True, compute='_compute_is_available', store=True)
    borrowed_count = fields.Integer('Times Borrowed', default=0)
    borrowed_by = fields.Many2one('res.partner', 'Currently Borrowed By')
    borrowed_date = fields.Date('Borrowed Date')
    return_date = fields.Date('Expected Return Date')
    
    @api.depends('borrowed_by')
    def _compute_is_available(self):
        for record in self:
            record.is_available = not bool(record.borrowed_by)
    
    @api.model
    def create(self, vals):
        if vals.get('is_book'):
            vals['type'] = 'product'
            vals['tracking'] = 'serial'
        return super().create(vals)