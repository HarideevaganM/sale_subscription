# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'FMS LEAD INHERIT',
    'version' : '15.1',
    'summary': 'Send Invoices and Track Payments',
    'sequence': 30,
    'description': """
Core mechanisms for the Lead modules. To display the menuitems, install the module account_invoicing.
    """,
    'category': 'CRM',    
   
   'depends': [
        'sale',
        'fms_sale',
        'crm',
    ],
    'data': [
       'views/lead_kanban_views.xml',
       
    ],
    
    
    'installable': True,
    'application': False,
    'auto_install': False,
    #~ 'post_init_hook': '_auto_install_l10n',
}
