# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError


class LibrarySignup(AuthSignupHome):

    @http.route('/web/library/signup', type='http', auth='public', website=True, sitemap=False)
    def library_signup(self, *args, **kw):
        """Extended signup page for library"""

        # Get borrower types
        borrower_types = request.env['library.borrower.type'].sudo().search([])

        # Get countries and states for dropdown
        countries = request.env['res.country'].sudo().search([])
        vietnam = request.env.ref('base.vn', raise_if_not_found=False)

        values = {
            'borrower_types': borrower_types,
            'countries': countries,
            'default_country': vietnam,
        }

        # If there's error from POST, add it
        if kw.get('error'):
            values['error'] = kw['error']
        if kw.get('success'):
            values['success'] = kw['success']

        return request.render('entro_library_signup.library_signup_form', values)

    @http.route('/web/library/signup/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def library_signup_submit(self, **post):
        """Handle library signup form submission"""

        try:
            # Validate required fields
            required_fields = ['full_name', 'email', 'phone', 'borrower_type_id', 'vipassana_attended']
            for field in required_fields:
                if not post.get(field):
                    raise UserError(_('Vui lòng điền đầy đủ thông tin bắt buộc.'))

            # Check if email already exists in signup requests
            existing_request = request.env['library.signup.request'].sudo().search([
                ('email', '=', post.get('email'))
            ], limit=1)

            if existing_request:
                raise UserError(_('Email này đã được đăng ký. Vui lòng kiểm tra email hoặc liên hệ quản lý thư viện.'))

            # Check if email already exists as user
            existing_user = request.env['res.users'].sudo().search([
                ('login', '=', post.get('email'))
            ], limit=1)

            if existing_user:
                raise UserError(_('Email này đã được sử dụng. Vui lòng sử dụng email khác.'))

            # Create signup request
            vals = {
                'full_name': post.get('full_name'),
                'dharma_name': post.get('dharma_name') or False,
                'email': post.get('email'),
                'phone': post.get('phone'),
                'date_of_birth': post.get('date_of_birth') or False,
                'gender': post.get('gender') or False,
                'street': post.get('street') or False,
                'street2': post.get('street2') or False,
                'city': post.get('city') or False,
                'state_id': int(post.get('state_id')) if post.get('state_id') else False,
                'zip': post.get('zip') or False,
                'country_id': int(post.get('country_id')) if post.get('country_id') else False,
                'id_card_number': post.get('id_card_number') or False,
                'student_id': post.get('student_id') or False,
                'borrower_type_id': int(post.get('borrower_type_id')),
                'organization': post.get('organization') or False,
                'vipassana_attended': True if post.get('vipassana_attended') == 'yes' else False,
                'notes': post.get('notes') or False,
                'state': 'pending',
            }

            signup_request = request.env['library.signup.request'].sudo().create(vals)

            # Send notification email to librarian
            self._notify_librarian(signup_request)

            return request.redirect('/web/library/signup/success')

        except UserError as e:
            # Redirect back to form with error
            return request.redirect('/web/library/signup?error=' + str(e))
        except Exception as e:
            return request.redirect('/web/library/signup?error=Đã xảy ra lỗi. Vui lòng thử lại.')

    @http.route('/web/library/signup/success', type='http', auth='public', website=True, sitemap=False)
    def library_signup_success(self, **kw):
        """Success page after signup"""
        return request.render('entro_library_signup.library_signup_success')

    def _notify_librarian(self, signup_request):
        """Notify library manager about new signup request"""
        # Get library managers
        library_manager_group = request.env.ref('entro_library.group_library_manager', raise_if_not_found=False)

        if library_manager_group:
            managers = request.env['res.users'].sudo().search([
                ('groups_id', 'in', [library_manager_group.id])
            ])

            # Create activity for each manager
            for manager in managers:
                signup_request.sudo().activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=manager.id,
                    summary=_('Yêu cầu đăng ký mới: %s') % signup_request.full_name,
                    note=_('Có yêu cầu đăng ký thành viên mới cần được duyệt.'),
                )
