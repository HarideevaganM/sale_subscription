# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM ENTERPRISE',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 5,
    'summary': 'Leads, Opportunities, Activities',
    'description': "",
    'website': 'https://www.odoo.com/page/crm',
    'depends': [
        'base_setup',
        'sales_team',
        'mail',
        'calendar',
        'resource',
        'fetchmail',
        'utm',
        'web_planner',
        'web_tour',
        'contacts',
        'crm',
    ],
    'data': [

        'views/leadwiz.xml',
    ],
    'demo': [
        'data/crm_demo.xml',
        'data/mail_activity_demo.xml',
        'data/crm_lead_demo.xml',
    ],
    'css': ['static/src/css/crm.css'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
