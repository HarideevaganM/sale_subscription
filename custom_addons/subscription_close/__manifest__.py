# -*- coding: utf-8 -*-
{
    'name': "Closure of Subscription",
    'summary': """Completion of the subscription""",
    'description': """This module extend the subscription process with closing steps.""",
    'author': "Futurenet Technologies India Pvt Ltd",
    'website': "http://www.futurenet.in",
    'category': 'Uncategorized',
    'version': '16.0.1',
    'depends': ['base', 'fms_subscription', 'website_support', 'fms_customer_support', 'sale_subscription'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/cron_views.xml',
        'data/datas.xml',
        'views/views.xml',
    ],
}