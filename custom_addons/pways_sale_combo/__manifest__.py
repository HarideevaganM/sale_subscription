# -*- coding: utf-8 -*-
{
    'name': 'Sales Order Combo',
    'category': 'sale',
    'summary': 'This module allows user to use combo feature in sale order.',
    'description': """This module allows user to use combo feature in sale order""",
    'version': '16.0.',
    'depends': ['stock', 'sale_management'],
    "data": [
        'security/ir.model.access.csv',
        'wizard/combo_product_wizard.xml',
        'views/sale_order.xml',
    ],
    'installable': True,
    'auto_install': False,
}
