# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS SALE ORDER Report',
    'version': '1.1',
    'category': 'Report',
    'summary': """Customized Sale Report""",
    'description': """
	This module contains Invoice Report
    """,
    'depends': ['sale','base'],
    'data': [
		'views/order_report.xml',
			
			
       
    ],
    'demo': [
       
    ],
    'installable': True,
    'application': False,
    'auto-install':False,
}
