# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime, timedelta

from werkzeug.exceptions import Forbidden, NotFound

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Command
from odoo.http import request, route
from odoo.tools import str2bool

from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.addons.website.controllers import main
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class WebsiteLibrary(http.Controller):
    
    def _get_search_order(self, post):
        """Get search order for books"""
        order = post.get('order') or 'name'
        return 'is_published desc, %s, id desc' % order

    def _get_library_domain(self, search, category, author=None, availability=None):
        """Build domain for library book search"""
        domains = [
            ('sale_ok', '=', True),  # Books should be borrowable
            ('categ_id.book_categ', '=', True),  # Only book categories
        ]
        
        if search:
            for srch in search.split(" "):
                subdomains = [
                    ('name', 'ilike', srch),
                    ('isbn', 'ilike', srch),
                    ('catalog_num', 'ilike', srch),
                    ('author.name', 'ilike', srch),
                ]
                domains.append(expression.OR(subdomains))

        if category:
            domains.append([('categ_id', '=', int(category))])
            
        if author:
            domains.append([('author', '=', int(author))])
            
        if availability == 'available':
            domains.append([('availability', '=', 'available')])

        return expression.AND(domains)

    @http.route(['/library', '/library/books'], type='http', auth="public", website=True)
    def library_books(self, page=0, category=None, search='', ppg=False, **post):
        """Main library books listing page"""
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg or 20

        ppr = request.env['website'].get_current_website().shop_ppr or 4

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        domain = self._get_library_domain(search, category)

        url = "/library"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list

        Product = request.env['product.template'].with_context(bin_size=True)

        Category = request.env['product.category']
        if category:
            category = Category.browse(int(category)).exists()

        website_domain = request.website.website_domain()
        search_product = Product.search(
            domain + website_domain,
            order=self._get_search_order(post)
        )

        pager = request.website.pager(url=url, total=len(search_product), page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset:offset + ppg]

        ProductCategory = request.env['product.category']
        if category:
            category = ProductCategory.browse(int(category)).exists()

        # Get all book categories for filter
        book_categories = ProductCategory.search([('book_categ', '=', True)])
        
        # Get all authors for filter
        authors = request.env['library.author'].search([])

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': False,  # No pricing for library
            'products': products,
            'search_count': len(search_product),
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'categories': book_categories,
            'authors': authors,
            'main_object': category,
        }
        return request.render("website_library.library_books", values)

    @http.route(['/library/book/<model("product.template"):product>'], type='http', auth="public", website=True)
    def library_book_detail(self, product, category='', search='', **kwargs):
        """Book detail page"""
        if not product.can_access_from_current_website():
            raise NotFound()

        # Get available lots/serials for this book
        available_lots = product.product_variant_ids.mapped('lot_ids').filtered(
            lambda lot: any(quant.quantity > 0 for quant in lot.quant_ids.filtered(
                lambda q: q.location_id.usage == 'internal'
            ))
        )

        values = {
            'search': search,
            'category': category,
            'product': product,
            'main_object': product,
            'available_lots': available_lots,
            'available_count': len(available_lots),
        }
        return request.render("website_library.book_detail", values)

    @http.route(['/library/cart'], type='http', auth="public", website=True)
    def library_cart(self, access_token=None, revive='', **post):
        """Library borrowing cart page"""
        order = request.website.sale_get_order()

        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()

        values = {
            'website_sale_order': order,
            'revive': revive,
        }
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)
            if abandoned_order:
                values['abandoned_order'] = abandoned_order

        return request.render("website_library.library_cart", values)

    @http.route(['/library/cart/add'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def library_cart_add(self, product_id, lot_id=None, add_qty=1, set_qty=0, **kwargs):
        """Add book to borrowing cart"""
        try:
            sale_order = request.website.sale_get_order(force_create=True)
            if sale_order.state != 'draft':
                request.session['sale_order_id'] = None
                sale_order = request.website.sale_get_order(force_create=True)

            product = request.env['product.product'].browse(int(product_id))
            
            if not product.exists() or not product.categ_id.book_categ:
                return request.redirect("/library?error=invalid_product")
            
            # Check if book is available
            if product.availability != 'available':
                return request.redirect(f"/library/book/{product.product_tmpl_id.id}?error=not_available")
            
            # For library borrowing, always add qty 1 (can't borrow multiple copies of same book)
            add_qty = 1
            
            # Check if book already in cart
            existing_line = sale_order.order_line.filtered(lambda l: l.product_id.id == product.id)
            if existing_line:
                return request.redirect("/library/cart?error=already_in_cart")
            
            # Create order line for book borrowing
            order_line_values = {
                'product_id': product.id,
                'product_uom_qty': add_qty,
                'order_id': sale_order.id,
                'name': f'Mượn sách: {product.name}',
                'price_unit': 0.0,  # No cost for borrowing
            }
            
            if lot_id:
                lot = request.env['stock.lot'].browse(int(lot_id))
                if lot.exists() and lot.product_id.id == product.id:
                    order_line_values['lot_id'] = lot.id
                
            # Mark order as library borrowing
            sale_order.write({
                'is_library_borrowing': True,
            })
                
            order_line = request.env['sale.order.line'].sudo().create(order_line_values)

            return request.redirect("/library/cart?added=1")
            
        except Exception as e:
            return request.redirect("/library?error=add_failed")

    @http.route(['/library/cart/remove'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def library_cart_remove(self, line_id, **kwargs):
        """Remove book from borrowing cart"""
        order = request.website.sale_get_order()
        if order:
            line = request.env['sale.order.line'].browse(int(line_id))
            if line and line.order_id == order:
                line.unlink()
        return request.redirect("/library/cart")

    @http.route(['/library/borrow'], type='http', auth="public", website=True)
    def library_borrow_checkout(self, **post):
        """Checkout page for book borrowing"""
        order = request.website.sale_get_order()

        if not order or not order.order_line:
            return request.redirect('/library')

        # Check if user is logged in and has library card
        if not request.env.user._is_public():
            # Look for library card
            library_card = request.env['library.card'].search([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', '=', 'running')
            ], limit=1)
        else:
            library_card = False

        values = {
            'order': order,
            'library_card': library_card,
            'user': request.env.user,
        }
        return request.render("website_library.borrow_checkout", values)

    @http.route(['/library/borrow/confirm'], type='http', auth="user", methods=['POST'], website=True, csrf=False)
    def library_borrow_confirm(self, **post):
        """Confirm book borrowing - creates sale order and delivery"""
        order = request.website.sale_get_order()
        
        if not order or not order.order_line:
            return request.redirect('/library')

        # Get library card
        library_card = request.env['library.card'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('state', '=', 'running')
        ], limit=1)

        if not library_card:
            raise UserError(_("Bạn cần có thẻ thư viện hợp lệ để mượn sách."))

        # Set order details
        order.write({
            'partner_id': request.env.user.partner_id.id,
            'library_card_id': library_card.id,
            'origin': 'Website Library Borrowing',
        })

        # Confirm the order (this creates the borrowing request)
        order.action_confirm()

        # Auto-create and confirm delivery for borrowing
        for picking in order.picking_ids:
            if picking.state == 'confirmed':
                picking.action_assign()
                # Auto-validate the delivery to complete borrowing
                picking.button_validate()

        return request.redirect(f'/my/orders/{order.id}?access_token={order.access_token}')

    @http.route(['/library/return/<int:order_id>'], type='http', auth="user", website=True)
    def library_return_page(self, order_id, **post):
        """Book return page"""
        order = request.env['sale.order'].browse(order_id)
        
        if not order.exists() or order.partner_id != request.env.user.partner_id:
            raise Forbidden()

        # Get return pickings for this order
        return_pickings = request.env['stock.picking'].search([
            ('origin', 'like', f'Return of {order.name}'),
            ('partner_id', '=', request.env.user.partner_id.id)
        ])

        values = {
            'order': order,
            'return_pickings': return_pickings,
        }
        return request.render("website_library.book_return", values)

    @http.route(['/library/return/create'], type='http', auth="user", methods=['POST'], website=True, csrf=False)
    def library_return_create(self, order_id, **post):
        """Create return picking for borrowed books"""
        order = request.env['sale.order'].browse(int(order_id))
        
        if not order.exists() or order.partner_id != request.env.user.partner_id:
            raise Forbidden()

        # Create return wizard and process
        return_wizard = request.env['library.return.book.wizard'].create({
            'sale_order_id': order.id,
        })
        
        result = return_wizard.create_return_picking()
        
        if result and result.get('res_id'):
            picking_id = result['res_id']
            return request.redirect(f'/library/return/picking/{picking_id}')
        
        return request.redirect(f'/library/return/{order_id}')

    @http.route(['/library/return/picking/<int:picking_id>'], type='http', auth="user", website=True)
    def library_return_picking_detail(self, picking_id, **post):
        """Return picking detail page"""
        picking = request.env['stock.picking'].browse(picking_id)
        
        if not picking.exists() or picking.partner_id != request.env.user.partner_id:
            raise Forbidden()

        values = {
            'picking': picking,
        }
        return request.render("website_library.return_picking_detail", values)


# Table compute class for product layout (copied from website_sale)
class TableCompute(object):

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey, ppr):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= ppr:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(ppr):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=20, ppr=4):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        x = 0
        for p in products:
            x = min(max(getattr(p, 'website_size_x', 1), 1), ppr)
            y = min(max(getattr(p, 'website_size_y', 1), 1), ppr)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % ppr, pos // ppr, x, y, ppr):
                pos += 1
            if index >= ppg and ((pos + 1.0) // ppr) > maxy:
                break

            if x == 1 and y == 1:   # simple heuristic for CPU optimization
                minpos = pos // ppr

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // ppr) + y2][(pos % ppr) + x2] = False
            self.table[pos // ppr][pos % ppr] = {
                'product': p, 'x': x, 'y': y,
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos // ppr))
            index += 1

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows

    @http.route(['/library/search/autocomplete'], type='json', auth="public", website=True)
    def library_search_autocomplete(self, query, **kwargs):
        """Autocomplete search suggestions"""
        suggestions = []
        
        if len(query) >= 2:
            # Search books
            books = request.env['product.template'].search([
                ('sale_ok', '=', True),
                ('categ_id.book_categ', '=', True),
                ('website_published', '=', True),
                ('name', 'ilike', query)
            ], limit=5)
            
            for book in books:
                suggestions.append({
                    'label': book.name,
                    'value': book.name,
                    'url': f'/library/book/{book.id}'
                })
            
            # Search authors
            authors = request.env['library.author'].search([
                ('name', 'ilike', query)
            ], limit=3)
            
            for author in authors:
                suggestions.append({
                    'label': f'Author: {author.name}',
                    'value': author.name,
                    'url': f'/library?author={author.id}'
                })
        
        return {'suggestions': suggestions}

    @http.route(['/library/snippet/books'], type='json', auth="public", website=True)
    def library_snippet_books(self, category=None, availability=None, order='name', limit=12, **kwargs):
        """Get books for website snippets"""
        domain = [
            ('sale_ok', '=', True),
            ('categ_id.book_categ', '=', True),
            ('website_published', '=', True)
        ]
        
        if category:
            domain.append(('categ_id', '=', int(category)))
        
        if availability:
            domain.append(('availability', '=', availability))
        
        books = request.env['product.template'].search(domain, order=order, limit=int(limit))
        
        result = []
        for book in books:
            result.append({
                'id': book.id,
                'name': book.name,
                'author': book.author.name if book.author else '',
                'image_url': f'/web/image/product.template/{book.id}/image_512' if book.image_1920 else '',
                'availability': book.availability,
                'url': f'/library/book/{book.id}'
            })
        
        return {'books': result}

    @http.route(['/library/snippet/stats'], type='json', auth="public", website=True)
    def library_snippet_stats(self, **kwargs):
        """Get library statistics for snippets"""
        total_books = request.env['product.template'].search_count([
            ('sale_ok', '=', True),
            ('categ_id.book_categ', '=', True)
        ])
        
        available_books = request.env['product.template'].search_count([
            ('sale_ok', '=', True),
            ('categ_id.book_categ', '=', True),
            ('availability', '=', 'available')
        ])
        
        borrowed_books = request.env['sale.order'].search_count([
            ('is_library_borrowing', '=', True),
            ('state', '=', 'sale')
        ])
        
        total_users = request.env['library.card'].search_count([
            ('state', '=', 'running')
        ])
        
        return {
            'total_books': total_books,
            'available_books': available_books,
            'borrowed_books': borrowed_books,
            'total_users': total_users
        }

    @http.route(['/library/dashboard/data'], type='json', auth="user", website=True)
    def library_dashboard_data(self, **kwargs):
        """Get dashboard data for backend"""
        if not request.env.user.has_group('library.group_librarian'):
            return {'error': 'Access denied'}
        
        # Get statistics
        stats = self.library_snippet_stats()
        
        # Get borrowing trends (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        borrowing_data = request.env['sale.order'].read_group([
            ('is_library_borrowing', '=', True),
            ('date_order', '>=', thirty_days_ago),
            ('state', '=', 'sale')
        ], ['date_order'], ['date_order:day'])
        
        borrowing_trends = {
            'labels': [data['date_order:day'] for data in borrowing_data],
            'values': [data['date_order_count'] for data in borrowing_data]
        }
        
        # Get popular books
        popular_books_data = request.env['sale.order.line'].read_group([
            ('order_id.is_library_borrowing', '=', True),
            ('order_id.state', '=', 'sale')
        ], ['product_id'], ['product_id'], limit=10, orderby='product_id_count desc')
        
        popular_books = {
            'labels': [request.env['product.product'].browse(data['product_id'][0]).name for data in popular_books_data],
            'values': [data['product_id_count'] for data in popular_books_data]
        }
        
        return {
            'stats': stats,
            'borrowing_trends': borrowing_trends,
            'popular_books': popular_books,
            'recent_activities': []  # Can be implemented later
        }