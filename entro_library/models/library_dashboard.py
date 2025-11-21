# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class LibraryDashboard(models.Model):
    _name = 'library.dashboard'
    _description = 'Library Dashboard'
    _auto = False

    @api.model
    def get_dashboard_data(self, filters=None):
        """
        Get aggregated data for library dashboard
        """
        if filters is None:
            filters = {}

        # Calculate date range
        date_from = filters.get('date_from')
        date_to = filters.get('date_to')

        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')

        # Get statistics
        statistics = self._get_statistics(date_from, date_to)

        # Get popular books
        popular_books = self._get_popular_books(limit=5)

        # Get category distribution
        category_distribution = self._get_category_distribution()

        # Get recent borrowings
        recent_borrowings = self._get_recent_borrowings(limit=10)

        # Get overdue borrowings
        overdue_borrowings = self._get_overdue_borrowings()

        # Get borrowing trends (last 7 days)
        borrowing_trends = self._get_borrowing_trends(days=7)

        # Get top borrowers
        top_borrowers = self._get_top_borrowers(limit=5)

        # Get new books this month
        new_books_this_month = self._get_new_books_this_month(limit=10)

        return {
            'statistics': statistics,
            'popular_books': popular_books,
            'category_distribution': category_distribution,
            'recent_borrowings': recent_borrowings,
            'overdue_borrowings': overdue_borrowings,
            'borrowing_trends': borrowing_trends,
            'top_borrowers': top_borrowers,
            'new_books_this_month': new_books_this_month,
        }

    def _get_statistics(self, date_from, date_to):
        """Calculate general statistics"""
        # Use sudo() for read-only statistics to avoid access issues
        Book = self.env['library.book'].sudo()
        BorrowingLine = self.env['library.borrowing.line'].sudo()
        Borrowing = self.env['library.borrowing'].sudo()
        Partner = self.env['res.partner'].sudo()

        # Total books
        total_book_titles = Book.search_count([])

        # Count borrowed books from borrowing lines
        borrowed_books = BorrowingLine.search_count([
            ('state', 'in', ('borrowed', 'overdue'))
        ])

        # Active borrowers
        active_borrowers = Partner.search_count([
            ('is_borrower', '=', True),
            ('is_membership_active', '=', True)
        ])

        # Count overdue books from lines
        overdue_books = BorrowingLine.search_count([
            ('state', '=', 'overdue')
        ])

        # Total fines (sum from borrowings)
        overdue_borrowings = Borrowing.search([
            ('state', 'in', ('borrowed', 'overdue'))
        ])
        total_fines = sum(overdue_borrowings.mapped('fine_amount'))

        # Count books borrowed in period from lines
        borrowing_lines_in_period = BorrowingLine.search([
            ('borrowing_id.borrow_date', '>=', date_from),
            ('borrowing_id.borrow_date', '<=', date_to)
        ])
        books_borrowed_in_period = len(borrowing_lines_in_period)

        # Count books returned in period from lines
        returned_lines_in_period = BorrowingLine.search([
            ('return_date', '>=', date_from),
            ('return_date', '<=', date_to),
            ('state', '=', 'returned')
        ])
        books_returned_in_period = len(returned_lines_in_period)

        return {
            'total_books': total_book_titles,
            'total_copies': total_book_titles,
            'borrowed_books': borrowed_books,
            'available_books': total_book_titles - borrowed_books,
            'active_borrowers': active_borrowers,
            'overdue_books': overdue_books,
            'total_fines': total_fines,
            'borrowings_in_period': books_borrowed_in_period,
            'returned_in_period': books_returned_in_period,
        }

    def _get_popular_books(self, limit=5):
        """Get most borrowed books"""
        books = self.env['library.book'].sudo().search([('total_times_borrowed', '>', 0)], order='total_times_borrowed desc', limit=limit)

        return [{
            'id': book.id,
            'name': book.name,
            'code': book.code,
            'author': ', '.join(book.author_ids.mapped('name')[:2]) if book.author_ids else 'N/A',
            'times_borrowed': book.total_times_borrowed,
            'quant_count': book.quant_count,
            'available_count': book.available_quant_count,
        } for book in books]

    def _get_category_distribution(self):
        """Get book distribution by category"""
        query = """
            SELECT
                c.name as category,
                COUNT(DISTINCT b.id) as count
            FROM library_book b
            JOIN library_book_category_rel rel ON b.id = rel.book_id
            JOIN library_category c ON c.id = rel.category_id
            WHERE b.active = true
            GROUP BY c.name
            ORDER BY count DESC
        """
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        return results

    def _get_recent_borrowings(self, limit=10):
        """Get recent borrowing transactions"""
        borrowings = self.env['library.borrowing'].search(
            [('state', 'not in', ('draft', 'cancelled'))],
            order='borrow_date desc, id desc',
            limit=limit
        )

        result = []
        for b in borrowings:
            # Show borrowing with book count
            book_count = len(b.borrowing_line_ids)
            book_titles = ', '.join(b.borrowing_line_ids.mapped('book_name')[:3])
            if book_count > 3:
                book_titles += f' (+{book_count - 3} more)'

            result.append({
                'id': b.id,
                'name': b.name,
                'book_count': book_count,
                'book_titles': book_titles,
                'borrower': b.borrower_id.name,
                'borrow_date': b.borrow_date.strftime('%Y-%m-%d') if b.borrow_date else '',
                'return_date': b.due_date.strftime('%Y-%m-%d') if b.due_date else '',
                'state': b.state,
                'late_days': b.late_days,
                'fine_amount': b.fine_amount,
            })
        return result

    def _get_overdue_borrowings(self):
        """Get overdue borrowings"""
        borrowings = self.env['library.borrowing'].search([
            ('state', '=', 'overdue')
        ], order='borrow_date asc')

        result = []
        for b in borrowings:
            # Get overdue books in this borrowing
            overdue_lines = b.borrowing_line_ids.filtered(lambda l: l.state == 'overdue')
            book_count = len(overdue_lines)
            book_titles = ', '.join(overdue_lines.mapped('book_name')[:3])
            if book_count > 3:
                book_titles += f' (+{book_count - 3} more)'

            result.append({
                'id': b.id,
                'name': b.name,
                'book_count': book_count,
                'book_titles': book_titles,
                'borrower': b.borrower_id.name,
                'borrower_phone': b.borrower_phone,
                'borrower_email': b.borrower_email,
                'borrow_date': b.borrow_date.strftime('%Y-%m-%d') if b.borrow_date else '',
                'late_days': b.late_days,
                'fine_amount': b.fine_amount,
            })
        return result

    def _get_borrowing_trends(self, days=7):
        """Get borrowing trends for last N days - count books, not borrowings"""
        BorrowingLine = self.env['library.borrowing.line'].sudo()
        trends = []

        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).date()

            # Count books borrowed on this date (from lines)
            borrowed_lines = BorrowingLine.search([
                ('borrowing_id.borrow_date', '=', date)
            ])
            borrowed = len(borrowed_lines)

            # Count books returned on this date (from lines)
            returned_lines = BorrowingLine.search([
                ('return_date', '=', date),
                ('state', '=', 'returned')
            ])
            returned = len(returned_lines)

            trends.append({
                'date': date.strftime('%Y-%m-%d'),
                'date_label': date.strftime('%d/%m'),
                'borrowed': borrowed,
                'returned': returned,
            })

        return trends

    def _get_top_borrowers(self, limit=5):
        """Get top borrowers - count books borrowed, not borrowing records"""
        query = """
            SELECT
                p.id,
                p.name,
                p.borrower_code,
                COUNT(DISTINCT b.id) as total_borrowings,
                COUNT(bl.id) as total_books_borrowed,
                SUM(CASE WHEN bl.state IN ('borrowed', 'overdue') THEN 1 ELSE 0 END) as current_books,
                SUM(CASE WHEN bl.state = 'overdue' THEN 1 ELSE 0 END) as overdue_books
            FROM res_partner p
            JOIN library_borrowing b ON b.borrower_id = p.id
            JOIN library_borrowing_line bl ON bl.borrowing_id = b.id
            WHERE p.is_borrower = true
            GROUP BY p.id, p.name, p.borrower_code
            ORDER BY total_books_borrowed DESC
            LIMIT %s
        """
        self.env.cr.execute(query, (limit,))
        results = self.env.cr.dictfetchall()

        return results

    def _get_new_books_this_month(self, limit=10):
        """Get books created in the current month"""
        from datetime import date

        # Get first day of current month
        today = date.today()
        first_day = date(today.year, today.month, 1)

        # Search for books created this month
        books = self.env['library.book'].sudo().search([
            ('create_date', '>=', first_day),
            ('active', '=', True)
        ], order='create_date desc', limit=limit)

        return [{
            'id': book.id,
            'name': book.name,
            'code': book.code,
            'author': ', '.join(book.author_ids.mapped('name')) if book.author_ids else 'N/A',
            'category': book.category_id.name if book.category_id else 'N/A',
            'registration_date': book.registration_date.strftime('%Y-%m-%d') if book.registration_date else '',
            'create_date': book.create_date.strftime('%Y-%m-%d') if book.create_date else '',
            'quant_count': book.quant_count,
            'available_count': book.available_quant_count,
        } for book in books]
