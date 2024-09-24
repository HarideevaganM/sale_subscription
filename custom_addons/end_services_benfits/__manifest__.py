# -*- coding: utf-8 -*-
{
    'name': "End Services Benfits",

    'summary': """
        calculation of end of services benefits""",

    'description': """
              """,

    'author': "Dvit",
    'website': "https://www.dvit.me",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr_payroll', 'hr', 'hr_contract', ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'templates.xml','salary_rul.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}