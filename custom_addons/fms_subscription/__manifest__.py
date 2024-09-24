# -*- coding: utf-8 -*-

{
    'name': 'FMS Subscription ',
    'version': '16.1.0',
    'sequence': 125,
    'category': 'Human Resources',
    'description': """
        """,
    'depends': ['mail','repair','website_support','fms_sale','sale_subscription', 'account'],

    'data': [
        #~ 'views/maintenance.xml',

        'data/data.xml',
        'security/subscription_cron.xml',
        'views/subscription_menu_inherit.xml',
    ],
    # 'images':[
    #     'static/description/icon1.png',
    # ],
    #~ 'demo': ['data/maintenance_demo.xml'],
    'installable': True,
    'application': True,

}
