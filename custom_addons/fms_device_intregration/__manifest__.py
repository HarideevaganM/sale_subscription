# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Pull API Intregration',
    'version': '16.0.0',
    'summary': 'Pull API Intregration',
    'description': 'Pull API Intregration',
    'depends': ['stock', 'fms_sale'],
    'data': [
        "data/import_export_cron.xml",
        "views/res_compnay_views.xml",
        "wizard/message_wizard.xml"
    ],
    'installable': True,
    'application': True,
}