# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PURCHASE-INHERIT',
    'version': '1.2',
    'category': 'PURCHASE',
    'sequence': 5,
    'author': 'Futurenet',
    'summary': 'PURCHASE - INHERIT',
    'depends': ['base','sale','purchase','account','stock'],

    'data': [
        'security/ir.model.access.csv',
        # 'security/group_view.xml',
        'views/purchase_inherit_view.xml',

    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
