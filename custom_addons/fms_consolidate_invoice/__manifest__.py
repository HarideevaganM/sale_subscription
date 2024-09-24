# -*- coding: utf-8 -*-
{
    'name': "FMS Consolidate Invoice",
    'summary': """This module extend the invoice with consolidation feature with multiple invoices.""",
    'author': "Futurenet Technologies India Pvt Ltd",
    'website': "http://www.futurenet.in",
    'category': 'Accounting',
    'version': '16.0.1',
    'depends': ['base', 'account', 'fms_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/views.xml',
        'reports/report_views.xml',
    ],
    'installable': False,
    'auto_install': False,
}