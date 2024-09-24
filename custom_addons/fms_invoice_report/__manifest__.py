# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'GFMS INVOICE Report',
    'version': '16.0',
    'category': 'Invoice Report',
    'summary': """Customized INVOICE Report""",
    'description': """This module contains Invoice Report""",
    'depends': ['purchase','purchase_requisition', 'account'],
    'data': ['views/invoice_report.xml'],
    'demo': [],
    'installable': True,
    'application': False,
}
