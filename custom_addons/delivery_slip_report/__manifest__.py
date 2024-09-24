# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'INVENTRY - DC REPORT ',
    'version' : '15.1',
    'sequence': 30,
    'description': """
    """,
    'depends' : ['crm', 'sale', 'stock'],
    'data': [
        'reports/delivery_order_report_inherit.xml',
        'reports/picking_operations_report_inherit.xml',

    ],
}
