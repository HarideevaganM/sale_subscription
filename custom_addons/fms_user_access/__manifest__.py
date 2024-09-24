# -*- coding: utf-8 -*-
{
    'name': "FMS - User access customized mosule",
    'description': """
       Hide and control menu visibilities to users
    """,
    'category': 'Enchancement',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['crm','project','odoo_job_costing_management','hr','fms_hrms'],

    # always loaded
    'data': [
        'security/user_access.xml',
    ],
}
