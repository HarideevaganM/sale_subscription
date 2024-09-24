# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FMS - Sale',
    'version': '16.1.1',
    'category': 'Sales',
    'summary': """Customized Sale,Purchase,Inventory,Project,Subscription modules""",
    'description': """This module contains all the common features of Sales Management and Purchase Management.""",
    'depends': ['stock', 'sales_team','sale_crm', 'purchase', 'purchase_requisition', 'account', 'portal', 'crm', 'hr', 'sale_quotation_number',
                'odoo_job_costing_management', 'sale_subscription', 'job_order_card_instruction', 'project','website_support','material_purchase_requisitions', 'product', 'mail'],
    'data': [
            'security/ir_cron.xml',
            'security/engineer_group.xml',
            'security/ir.model.access.csv',
            'data/ir_sequence_data.xml',
            'data/data.xml',
            'wizard/job_card_wizard.xml',
            'views/installation_certificate.xml',
            'views/sale_order_inherit.xml',
            'views/contract.xml',
            'views/project.xml',
            'views/device_history.xml',
            'views/stock_inherit.xml',
            'views/subscription_inherit.xml',
            'views/division_invoice.xml',
            'views/purchase_inherit.xml',
            'views/job_instruction_inherit.xml',
            'views/product_inherit.xml',
            'views/material_requisition_inherit.xml',
            'views/vehicle_master.xml',
            'views/product_pricelist.xml',
            #~ 'views/menu_restriction.xml',
            'views/account_inherit.xml',
            'views/partner_inherit.xml',
            'views/crm_lead_inherit.xml',
            #~ 'report/installation_certificate_report.xml',
            'report/report_lease_invoice.xml',
            # 'report/report_sale_invoice.xml',
            # 'report/report_sale_invoice_inclusive.xml',

    ],
    'demo': [

    ],
    'installable': True,
    'application': False,
    'auto-install': False,
}
