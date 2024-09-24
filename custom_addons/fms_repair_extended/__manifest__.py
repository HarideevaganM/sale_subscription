# -*- coding: utf-8 -*-

{
    'name': 'Repair Extended',
    'description': """ Repair Extended """,
    'summary': 'Repair Extended',
    'depends': ['fms_repair', 'website_support', 'account', 'fms_sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/repair_extended_view.xml',
    ],
    'installable': True,
    'application': True,
}
