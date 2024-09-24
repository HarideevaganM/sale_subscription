# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Renewal',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 5,
    'summary': 'Renewal Contract',
    'description': "",
    'author':"Iswasu Technologies",
    'depends': [
        'base_setup',
        'sales_team',
        'mail',
        'sale',
        'calendar',
        'resource',
        'fetchmail',
        'utm',
        'web_planner',
        'web_tour',
        'contacts',
        'fms_sale',

    ],
    'data': [

        'views/renewal_cycle.xml',
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',





    ],


    'installable': True,
    'application': True,
    'auto_install': False,
   
}
