# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS Purchase Order Report',
    'version': '16.1',
    'category': 'Report',
    'summary': """Customized Purchase Order Report""",
    'description': """
	This module contains Purchase Order Report
    """,
    'depends': ['purchase','purchase_requisition', 'account','base'],
    'data': [
			'views/purchase_order_report.xml',
    ],
    'demo': [
       
    ],
    'installable': True,
    'application': False,
    'auto-install':False,
}
