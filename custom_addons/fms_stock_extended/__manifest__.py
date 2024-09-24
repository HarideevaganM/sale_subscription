# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS GRN Report',
    'version': '1.0',
    'category': 'FMS GRN Report',
    'summary': """Customized GRN Report""",
    'description': """Customized GRN Report""",
    'depends': ['stock'],
    'data': [
            'views/stock_picking.xml',
            'report/grn_report.xml',
            'report/report_action.xml',
    ],
    'installable': True,
    'application': True,
}
