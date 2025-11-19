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

        return {
            'statistics': statistics,
            'popular_books': popular_books,
            'category_distribution': category_distribution,
            'recent_borrowings': recent_borrowings,
            'overdue_borrowings': overdue_borrowings,
            'borrowing_trends': borrowing_trends,
            'top_borrowers': top_borrowers,
        }

    def _get_statistics(self, date_from, date_to):
        """Calculate general statistics"""
        Book = self.env['library.book']
        Borrowing = self.env['library.borrowing']
        Partner = self.env['res.partner']

        # Total books
        total_books = sum(Book.search([]).mapped('times_borrowed')) or Book.search_count([])
        total_book_titles = Book.search_count([])

        # Available and borrowed books
        borrowed_books = Borrowing.search_count([
            ('state', 'in', ('borrowed', 'overdue'))
        ])

        # Active borrowers
        active_borrowers = Partner.search_count([
            ('is_borrower', '=', True),
            ('is_membership_active', '=', True)
        ])

        # Overdue books
        overdue_books = Borrowing.search_count([
            ('state', '=', 'overdue')
        ])

        # Total fines
        overdue_borrowings = Borrowing.search([
            ('state', '=', 'overdue')
        ])
        total_fines = sum(overdue_borrowings.mapped('fine_amount'))

        # Books borrowed in period
        borrowings_in_period = Borrowing.search_count([
            ('borrow_date', '>=', date_from),
            ('borrow_date', '<=', date_to)
        ])

        # Books returned in period
        returned_in_period = Borrowing.search_count([
            ('return_date', '>=', date_from),
            ('return_date', '<=', date_to),
            ('state', '=', 'returned')
        ])

        return {
            'total_books': total_book_titles,
            'total_copies': total_books,
            'borrowed_books': borrowed_books,
            'available_books': total_books - borrowed_books,
            'active_borrowers': active_borrowers,
            'overdue_books': overdue_books,
            'total_fines': total_fines,
            'borrowings_in_period': borrowings_in_period,
            'returned_in_period': returned_in_period,
        }

    def _get_popular_books(self, limit=5):
        """Get most borrowed books"""
        books = self.env['library.book'].search([], order='times_borrowed desc', limit=limit)

        return [{
            'id': book.id,
            'name': book.name,
            'code': book.code,
            'author': ', '.join(book.author_ids.mapped('name')[:2]) if book.author_ids else 'N/A',
            'times_borrowed': book.times_borrowed,
            'current_borrower': book.current_borrower_id.name if book.current_borrower_id else None,
            'state': book.state,
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

        # If no categories, group by other criteria
        if not results:
            # Group by state instead
            query = """
                SELECT
                    state as category,
                    COUNT(*) as count
                FROM library_book
                WHERE active = true
                GROUP BY state
            """
            self.env.cr.execute(query)
            results = self.env.cr.dictfetchall()

        return results

    def _get_recent_borrowings(self, limit=10):
        """Get recent borrowing transactions"""
        borrowings = self.env['library.borrowing'].search(
            [],
            order='borrow_date desc, id desc',
            limit=limit
        )

        return [{
            'id': b.id,
            'name': b.name,
            'book_title': b.book_name,
            'book_code': b.book_code,
            'borrower': b.borrower_id.name,
            'borrow_date': b.borrow_date.strftime('%Y-%m-%d') if b.borrow_date else '',
            'due_date': b.due_date.strftime('%Y-%m-%d') if b.due_date else '',
            'return_date': b.return_date.strftime('%Y-%m-%d') if b.return_date else '',
            'state': b.state,
            'late_days': b.late_days,
            'fine_amount': b.fine_amount,
        } for b in borrowings]

    def _get_overdue_borrowings(self):
        """Get overdue borrowings"""
        borrowings = self.env['library.borrowing'].search([
            ('state', '=', 'overdue')
        ], order='due_date asc')

        return [{
            'id': b.id,
            'name': b.name,
            'book_title': b.book_name,
            'borrower': b.borrower_id.name,
            'borrower_phone': b.borrower_phone,
            'borrower_email': b.borrower_email,
            'due_date': b.due_date.strftime('%Y-%m-%d') if b.due_date else '',
            'late_days': b.late_days,
            'fine_amount': b.fine_amount,
        } for b in borrowings]

    def _get_borrowing_trends(self, days=7):
        """Get borrowing trends for last N days"""
        trends = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).date()

            borrowed = self.env['library.borrowing'].search_count([
                ('borrow_date', '=', date)
            ])

            returned = self.env['library.borrowing'].search_count([
                ('return_date', '=', date),
                ('state', '=', 'returned')
            ])

            trends.append({
                'date': date.strftime('%Y-%m-%d'),
                'date_label': date.strftime('%d/%m'),
                'borrowed': borrowed,
                'returned': returned,
            })

        return trends

    def _get_top_borrowers(self, limit=5):
        """Get top borrowers"""
        query = """
            SELECT
                p.id,
                p.name,
                p.borrower_code,
                p.borrower_type,
                COUNT(b.id) as total_borrowings,
                SUM(CASE WHEN b.state IN ('borrowed', 'overdue') THEN 1 ELSE 0 END) as current_borrowings,
                SUM(CASE WHEN b.state = 'overdue' THEN 1 ELSE 0 END) as overdue_count
            FROM res_partner p
            JOIN library_borrowing b ON b.borrower_id = p.id
            WHERE p.is_borrower = true
            GROUP BY p.id, p.name, p.borrower_code, p.borrower_type
            ORDER BY total_borrowings DESC
            LIMIT %s
        """
        self.env.cr.execute(query, (limit,))
        results = self.env.cr.dictfetchall()

        return results
