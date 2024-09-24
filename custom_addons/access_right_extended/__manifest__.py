# -*- coding: utf-8 -*-
{
    'name' : 'Access right extended',
    'version' : '16.0',
    'summary': 'Access right extended',
    'sequence': 1,
    'description': """Access right extended""",
    'depends' : ['hr_contract','hr_expense','account','sale_subscription','sale','sale_management', 'crm', 'stock', 'purchase', 'hr_expense', 'website_support', 'fms_hrms', 'hr', 'odoo_job_costing_management'],
    'data': [
        'security/view_hide_stock_invoice.xml.xml',
        'views/sale_order_view.xml.xml'
    ],
    'installable': True,
    'application': True,
}
