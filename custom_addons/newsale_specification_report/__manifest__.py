# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS - Job New Sale Report',
    'version': '16',
    'category': 'Reporting',
    'summary': """Job Card Specification Report for New Sale""",
    'description': """""",
    'depends': ['odoo_job_costing_management','fms_sale','project'],
    'data': [

            'views/job_card_report.xml',
    ],
    'demo': [

    ],
    'installable': True,
    'application': False,
    'auto-install': False,
}
