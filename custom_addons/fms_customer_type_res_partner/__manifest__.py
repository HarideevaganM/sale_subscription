# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer Type',
    'version': '16.1',
    'category': 'Sales',
    'summary': 'customer_Type',
    'description': """ This module will list the customer type in company master """,
    'depends': [
        'sale', 'crm','base','sales_team', 'fms_sale_extended'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/customer_type.xml',
       ],
    'demo': [

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
