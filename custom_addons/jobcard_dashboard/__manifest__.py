# -*- coding: utf-8 -*-

#  See LICENSE file for full copyright and licensing details.

{
    'name': 'Job Card Dashboard',
    'version': '2.1',
    'category' : 'Sales',
    'license': 'Other proprietary',
    'summary': """Job Card Dashboard""",
    'depends': [
            'fms_sale',
            # 'odoo_job_costing_management',
            # 'job_order_card_instruction',
    ],
    'description': """

    """,
    'author': 'futurenet technologies.',
    'website': 'http://www.futurenet.in',
    'images': ['/static/description/welcome.png'],
    'data':[

        'security/ir.model.access.csv',
        'views/job_card_dashboard.xml',

    ],
    'installable' : True,
    'application' : True,
    'auto-install': False,

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
