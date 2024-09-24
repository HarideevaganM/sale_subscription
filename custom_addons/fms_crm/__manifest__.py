# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'FMS LEAD',
    'version' : '1.1',
    'summary': 'Send Invoices and Track Payments',
    'sequence': 30,
    'description': """
Core mechanisms for the Lead modules. To display the menuitems, install the module account_invoicing.
    """,
    'category': 'CRM',
    
   
   'depends': [
        'base_setup',
        'sales_team',
        'mail',
        'calendar',
        'resource',
        'fetchmail',
        'utm',
        'web_planner',
        'web_tour',
        'contacts',
        'sale',
        'fms_sale',
    ],
    'data': [
       'views/lead_views.xml',
       'wizard/lead_wizard.xml',
       'data/ir.sequence.xml',
       
    ],
    
    
    'installable': True,
    'application': False,
    'auto_install': False,
    #~ 'post_init_hook': '_auto_install_l10n',
}
