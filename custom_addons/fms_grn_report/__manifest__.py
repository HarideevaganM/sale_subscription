# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS - RECEIPT_REPORT',
    'version': '16.0',
    'category': 'Receipt report',
    'author': 'Futurenet Technologies',
    'description': """ """,

    'depends': ['purchase', 'purchase_requisition', 'account', 'sale'],
    'images': [],
    'data': [
        'views/receipt_report_inherit.xml',
        'views/payment_receipt_report_inherit.xml',
        'views/purchase_payment_inherit.xml',
    ],
    'qweb': [
    ],
    'demo': [

    ],
    'installable': True,
    'application': False,
    'auto-install': False,
}