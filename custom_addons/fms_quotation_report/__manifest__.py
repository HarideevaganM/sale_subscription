# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS zz Report',
    'version': '16.1.1',
    'category': 'Report',
    'summary': """Customized Quotation Report""",
    'description': """
	This module contains Quotation Report
    """,
    'depends': ['base','sale','sales_team'],
    'data': [
			'views/quotation_report.xml',
			'views/quotation_report_inclusive.xml',
    ],
    'demo': [
       
    ],
    'installable': True,
    'application': False,
    'auto-install':False,
}
