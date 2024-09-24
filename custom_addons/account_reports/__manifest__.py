# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Accounting Reports',
    'summary': 'View and create reports',
    'category': 'Accounting',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_financial_report_data.xml',
        'views/account_report_view.xml',
        'views/report_financial.xml',
        'views/search_template_view.xml',
        'views/report_followup.xml',
        'views/partner_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/res_config_settings_views.xml'
    ],
    'assets': {
            'web.assets_backend': [
                'account_reports/static/src/less/account_financial_report.less',
                'account_reports/static/src/js/account_reports_followup.js',
                'account_reports/static/src/js/account_reports_tours.js'
                'account_reports/static/src/js/account_reports.js'
            ],
        },
    'qweb': [
        'static/src/xml/account_report_template.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
