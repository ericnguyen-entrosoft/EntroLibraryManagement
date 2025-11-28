# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError


class LibraryPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add library counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'borrowing_count' in counters:
            values['borrowing_count'] = request.env['library.borrowing'].search_count([
                ('borrower_id', '=', partner.id),
                ('state', 'in', ['draft', 'borrowed']),
            ])

        if 'reservation_count' in counters:
            values['reservation_count'] = request.env['library.reservation'].search_count([
                ('borrower_id', '=', partner.id),
                ('state', 'in', ['active', 'available']),
            ])

        return values

    # ========== MY BORROWINGS ==========

    @http.route(['/my/borrowings', '/my/borrowings/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_my_borrowings(self, page=1, date_begin=None, date_end=None,
                             sortby=None, filterby=None, **kw):
        """Danh sách phiếu mượn của tôi"""

        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        LibraryBorrowing = request.env['library.borrowing']

        # Domain
        domain = [('borrower_id', '=', partner.id)]

        # Filters
        searchbar_filters = {
            'all': {'label': _('Tất cả'), 'domain': []},
            'draft': {'label': _('Nháp'), 'domain': [('state', '=', 'draft')]},
            'borrowed': {'label': _('Đang mượn'), 'domain': [('state', '=', 'borrowed')]},
            'returned': {'label': _('Đã trả'), 'domain': [('state', '=', 'returned')]},
            'overdue': {'label': _('Quá hạn'), 'domain': [('is_overdue', '=', True)]},
        }

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Ngày mượn'), 'order': 'borrow_date desc'},
            'name': {'label': _('Mã phiếu'), 'order': 'name'},
            'due_date': {'label': _('Ngày hẹn trả'), 'order': 'due_date'},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count
        borrowing_count = LibraryBorrowing.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/borrowings",
            url_args={'date_begin': date_begin, 'date_end': date_end,
                     'sortby': sortby, 'filterby': filterby},
            total=borrowing_count,
            page=page,
            step=self._items_per_page
        )

        # Get borrowings
        borrowings = LibraryBorrowing.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        values.update({
            'date': date_begin,
            'borrowings': borrowings,
            'page_name': 'borrowing',
            'pager': pager,
            'default_url': '/my/borrowings',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })

        return request.render("entro_library_website.portal_my_borrowings", values)

    @http.route(['/my/borrowing/<int:borrowing_id>'],
                type='http', auth="user", website=True)
    def portal_my_borrowing(self, borrowing_id=None, access_token=None, **kw):
        """Chi tiết phiếu mượn"""

        try:
            borrowing_sudo = self._document_check_access(
                'library.borrowing', borrowing_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'borrowing': borrowing_sudo,
            'page_name': 'borrowing',
            'report_type': 'pdf',
        }

        return request.render("entro_library_website.portal_my_borrowing_detail", values)

    # ========== MY RESERVATIONS ==========

    @http.route(['/my/reservations', '/my/reservations/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_my_reservations(self, page=1, sortby=None, filterby=None, **kw):
        """Danh sách đặt trước của tôi"""

        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Reservation = request.env['library.reservation']

        domain = [('borrower_id', '=', partner.id)]

        # Filters
        searchbar_filters = {
            'all': {'label': _('Tất cả'), 'domain': []},
            'active': {'label': _('Đang chờ'), 'domain': [('state', '=', 'active')]},
            'available': {'label': _('Đã có sẵn'), 'domain': [('state', '=', 'available')]},
            'borrowed': {'label': _('Đã mượn'), 'domain': [('state', '=', 'borrowed')]},
            'cancelled': {'label': _('Đã hủy'), 'domain': [('state', '=', 'cancelled')]},
        }

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Ngày đặt'), 'order': 'reservation_date desc'},
            'priority': {'label': _('Ưu tiên'), 'order': 'priority_order'},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count
        reservation_count = Reservation.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/reservations",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=reservation_count,
            page=page,
            step=self._items_per_page
        )

        # Get reservations
        reservations = Reservation.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        values.update({
            'reservations': reservations,
            'page_name': 'reservation',
            'pager': pager,
            'default_url': '/my/reservations',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })

        return request.render("entro_library_website.portal_my_reservations", values)

    @http.route(['/my/reservation/<int:reservation_id>/cancel'],
                type='http', auth="user", website=True, methods=['POST'], csrf=True)
    def portal_cancel_reservation(self, reservation_id, **kw):
        """Hủy đặt trước"""

        try:
            reservation = request.env['library.reservation'].browse(reservation_id)

            # Check access
            if reservation.borrower_id.id != request.env.user.partner_id.id:
                raise AccessError(_('Bạn không có quyền hủy đặt trước này'))

            if reservation.state not in ['active', 'available']:
                raise AccessError(_('Không thể hủy đặt trước ở trạng thái này'))

            reservation.action_cancel()

            return request.redirect('/my/reservations?message=cancelled')

        except Exception as e:
            return request.redirect('/my/reservations?error=%s' % str(e))

    # ========== MY BORROWING CART (DRAFT BORROWING) ==========

    @http.route(['/my/borrowing-cart'], type='http', auth="user", website=True)
    def portal_my_borrowing_cart(self, **kw):
        """Giỏ mượn sách (phiếu mượn nháp)"""

        partner = request.env.user.partner_id

        # Get or create draft borrowing
        borrowing = request.env['library.borrowing'].search([
            ('borrower_id', '=', partner.id),
            ('state', '=', 'draft'),
        ], limit=1)

        values = {
            'borrowing': borrowing,
            'page_name': 'borrowing_cart',
        }

        return request.render("entro_library_website.portal_my_borrowing_cart", values)

    @http.route(['/my/borrowing-cart/remove/<int:line_id>'],
                type='http', auth="user", website=True, methods=['POST'], csrf=True)
    def portal_remove_from_cart(self, line_id, **kw):
        """Xóa sách khỏi giỏ"""

        try:
            line = request.env['library.borrowing.line'].browse(line_id)

            # Check access
            if line.borrowing_id.borrower_id.id != request.env.user.partner_id.id:
                raise AccessError(_('Không có quyền'))

            if line.borrowing_id.state != 'draft':
                raise AccessError(_('Chỉ có thể xóa từ phiếu nháp'))

            line.unlink()

            return request.redirect('/my/borrowing-cart')

        except Exception as e:
            return request.redirect('/my/borrowing-cart?error=%s' % str(e))

    @http.route(['/my/borrowing-cart/checkout'],
                type='http', auth="user", website=True, methods=['POST'], csrf=True)
    def portal_checkout_borrowing(self, **kw):
        """Xác nhận mượn"""

        partner = request.env.user.partner_id

        borrowing = request.env['library.borrowing'].search([
            ('borrower_id', '=', partner.id),
            ('state', '=', 'draft'),
        ], limit=1)

        if not borrowing:
            return request.redirect('/my/borrowings?error=no_cart')

        if not borrowing.borrowing_line_ids:
            return request.redirect('/my/borrowing-cart?error=empty_cart')

        try:
            # Confirm borrowing (this will validate and change state)
            borrowing.action_confirm()

            return request.redirect('/my/borrowing/%s?message=confirmed' % borrowing.id)

        except Exception as e:
            return request.redirect('/my/borrowing-cart?error=%s' % str(e))

    # ========== BORROWING HISTORY & STATS ==========

    @http.route(['/my/borrowing-history'], type='http', auth="user", website=True)
    def portal_borrowing_history(self, **kw):
        """Lịch sử mượn sách với thống kê"""

        partner = request.env.user.partner_id

        # Statistics
        all_borrowings = request.env['library.borrowing'].search([
            ('borrower_id', '=', partner.id),
        ])

        total_borrowings = len(all_borrowings)
        total_books_borrowed = sum(b.total_quantity for b in all_borrowings)
        current_borrowed = len(all_borrowings.filtered(lambda b: b.state == 'borrowed'))
        overdue_count = len(all_borrowings.filtered(lambda b: b.is_overdue))

        # Recently returned books
        recently_returned = request.env['library.borrowing'].search([
            ('borrower_id', '=', partner.id),
            ('state', '=', 'returned'),
        ], order='return_date desc', limit=10)

        # Most borrowed categories
        category_stats = {}
        for borrowing in all_borrowings:
            for line in borrowing.borrowing_line_ids:
                cat = line.book_id.category_id.name or 'Khác'
                category_stats[cat] = category_stats.get(cat, 0) + 1

        top_categories = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:5]

        values = {
            'page_name': 'borrowing_history',
            'total_borrowings': total_borrowings,
            'total_books_borrowed': total_books_borrowed,
            'current_borrowed': current_borrowed,
            'overdue_count': overdue_count,
            'recently_returned': recently_returned,
            'top_categories': top_categories,
        }

        return request.render("entro_library_website.portal_borrowing_history", values)
