# -*- coding: utf-8 -*-

{
    'name': "Purchase Report BBIS",
    'summary': "Purchase Report BBIS",
    'category': 'purchase',
    'version': '16.0.1.3',
    'depends': ['purchase', 'odoo_job_costing_management'],
    'data': [
            'report/report_extend.xml',
            'report/report_action.xml',
            'report/purchase_report_extended.xml',
            'views/purchase_order_view.xml',
             ],
    'installable': True,
    'application': True
}