# -*- coding: utf-8 -*-
{
    'name': "FMS Access Groups",
    'summary': """This module extend the user groups with package.""",
    'description': """This module helps single click to allow access on all the set of modules.""",
    'author': "Futurenet Technologies India Pvt. Ltd.",
    'website': "http://www.futurenet.in",
    'category': 'Uncategorized',
    'version': '16.0.1',
        'depends': ['base', 'website_support', 'sales_team', 'fms_sale', 'sale_expense', 'hr', 'crm','hr_holidays', 'fms_customer_support',
                'purchase', 'purchase_requisition', 'odoo_job_costing_management', 'repair','hr_attendance', 'hr_contract', 'stock', 'subscription_close'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/access_rules.xml',
        'views/views.xml',
        'views/menu_items.xml',
    ],
}
