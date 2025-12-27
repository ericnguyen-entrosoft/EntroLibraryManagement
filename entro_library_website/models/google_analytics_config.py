# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GoogleAnalyticsConfig(models.Model):
    _name = 'google.analytics.config'
    _description = 'Google Analytics Configuration'
    _order = 'id desc'

    name = fields.Char(string='Configuration Name', required=True, default='GA4 Configuration')
    active = fields.Boolean(string='Active', default=True)

    # GA4 Configuration
    property_id = fields.Char(
        string='GA4 Property ID',
        help='Your Google Analytics 4 Property ID (e.g., 123456789)'
    )
    credentials_json = fields.Text(
        string='Service Account Credentials (JSON)',
        help='Paste the entire content of your Google Cloud service account JSON key file here'
    )

    # Metrics Configuration
    metric_name = fields.Selection([
        ('totalUsers', 'Total Users'),
        ('activeUsers', 'Active Users'),
        ('sessions', 'Sessions'),
        ('screenPageViews', 'Page Views'),
    ], string='Metric to Track', default='activeUsers', required=True)

    date_range = fields.Selection([
        ('7daysAgo', 'Last 7 Days'),
        ('30daysAgo', 'Last 30 Days'),
        ('90daysAgo', 'Last 90 Days'),
        ('365daysAgo', 'Last Year'),
    ], string='Date Range', default='30daysAgo', required=True)

    # Current Value
    visitor_count = fields.Integer(
        string='Current Visitor Count',
        readonly=True,
        help='Last fetched visitor count from Google Analytics'
    )
    last_update = fields.Datetime(
        string='Last Updated',
        readonly=True
    )
    last_error = fields.Text(
        string='Last Error',
        readonly=True
    )

    # Auto-update Settings
    auto_update = fields.Boolean(
        string='Auto Update',
        default=True,
        help='Automatically fetch data from Google Analytics'
    )
    update_interval = fields.Integer(
        string='Update Interval (hours)',
        default=6,
        help='How often to fetch data from Google Analytics (in hours)'
    )

    @api.model
    def get_active_config(self):
        """Get the active Google Analytics configuration"""
        return self.search([('active', '=', True)], limit=1)

    def action_test_connection(self):
        """Test Google Analytics connection and fetch data"""
        self.ensure_one()
        try:
            count = self._fetch_visitor_count()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Connection successful! Visitor count: %s') % count,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Connection failed: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_fetch_data(self):
        """Manually fetch visitor count from Google Analytics"""
        self.ensure_one()
        try:
            count = self._fetch_visitor_count()
            self.write({
                'visitor_count': count,
                'last_update': fields.Datetime.now(),
                'last_error': False,
            })
            # Update system parameter
            self.env['ir.config_parameter'].sudo().set_param('library.visitor_count', count)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Visitor count updated: %s') % count,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_msg = str(e)
            self.write({
                'last_error': error_msg,
                'last_update': fields.Datetime.now(),
            })
            _logger.error('Failed to fetch Google Analytics data: %s', error_msg)
            raise UserError(_('Failed to fetch data: %s') % error_msg)

    def _fetch_visitor_count(self):
        """Fetch visitor count from Google Analytics using GA4 Data API"""
        self.ensure_one()

        if not self.property_id:
            raise UserError(_('Please configure GA4 Property ID'))

        if not self.credentials_json:
            raise UserError(_('Please configure Service Account Credentials'))

        try:
            # Import Google Analytics Data API
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Metric,
            )
            from google.oauth2 import service_account
            import json

            # Parse credentials JSON
            credentials_dict = json.loads(self.credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/analytics.readonly']
            )

            # Initialize client
            client = BetaAnalyticsDataClient(credentials=credentials)

            # Build request
            request = RunReportRequest(
                property=f'properties/{self.property_id}',
                date_ranges=[DateRange(
                    start_date=self.date_range,
                    end_date='today'
                )],
                metrics=[Metric(name=self.metric_name)],
            )

            # Execute request
            response = client.run_report(request)

            # Extract value
            if response.rows:
                value = int(float(response.rows[0].metric_values[0].value))
                return value
            else:
                return 0

        except ImportError:
            raise UserError(_(
                'Google Analytics Data API library not installed. '
                'Please install it using: pip3 install google-analytics-data'
            ))
        except json.JSONDecodeError:
            raise UserError(_('Invalid JSON format in Service Account Credentials'))
        except Exception as e:
            raise UserError(_('Error fetching data from Google Analytics: %s') % str(e))

    @api.model
    def cron_update_visitor_count(self):
        """Scheduled action to update visitor count from Google Analytics"""
        configs = self.search([('active', '=', True), ('auto_update', '=', True)])
        for config in configs:
            try:
                count = config._fetch_visitor_count()
                config.write({
                    'visitor_count': count,
                    'last_update': fields.Datetime.now(),
                    'last_error': False,
                })
                # Update system parameter
                self.env['ir.config_parameter'].sudo().set_param('library.visitor_count', count)
                _logger.info('Google Analytics visitor count updated: %s', count)
            except Exception as e:
                error_msg = str(e)
                config.write({
                    'last_error': error_msg,
                    'last_update': fields.Datetime.now(),
                })
                _logger.error('Failed to update Google Analytics data for config %s: %s',
                            config.name, error_msg)
