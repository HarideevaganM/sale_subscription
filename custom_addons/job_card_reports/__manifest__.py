# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS - Installation certificates',
    'version': '16.1.1',
    'category': 'Sales',
    'summary': """Customized Sale,Purchase,Inventory,Project,Subscription modules""",
    'description': """This module contains all the common features of Sales Management and Purchase Management.""",
    'depends': ['sales_team', 'purchase', 'purchase_requisition', 'account', 'portal', 'crm', 'hr', 'fms_sale',
                'odoo_job_costing_management', 'sale_subscription', 'job_order_card_instruction', 'project'],
    'data': [
          'views/opal_ivms_report.xml',
          'views/speed_limiter_certificate.xml',
          'views/speed_limiter_certificates.xml',
          'views/non_opal_ivms_certificate.xml',
    ],
    'demo': [

    ],
    'installable': True,
    'application': False,
    'auto-install': False,
}
