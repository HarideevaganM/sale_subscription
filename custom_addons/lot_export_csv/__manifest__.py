# -*- coding: utf-8 -*-
{
    'name': 'Download Job Serial File',
    'version': '16.0',
    "category": "Stock",
    'depends': ['fms_sale', 'report_csv'],
    'data': [
        'views/lot_serial_csv.xml',
        'wizard/lot_serial_wizard.xml',
    ],
    'installable': True,
    'application': True,
}
