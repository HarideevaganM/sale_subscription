# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS - Bank_Advice_Report',
    'version': '16.1',
    'category': 'Sales',
    'summary': """Customized Payroll""",
    'description': """This module contains all the common features of Sales Management and Purchase Management.""",
    'depends': ['hr','base', 'hr_payroll_community'],
    'data': [
			  'security/ir.model.access.csv',
              'views/views.xml',
              'views/template.xml',
              'views/report_views.xml',
    ],
    'demo': [

    ],
    'installable': True,
    'application': False,
    'auto-install': False,
}
