# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS SO Cancel',
    'version': '16.1.1',
    'category': 'Sales',
    'description': """FMS-Saleorder Cancel""",
    'depends': ['sale', 'sales_team'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/so_cancel_wizard.xml',
        'views/sale_order_inherit.xml',
    ],
    'demo': [

    ],
    'installable': True,
    'application': False,
    'auto-install': False,
}
