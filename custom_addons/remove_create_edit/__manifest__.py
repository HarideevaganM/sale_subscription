# -*- coding: utf-8 -*-
{
    'name': "Remove Create & Edit",
    'description': """
       Create and edit option removed in partner field
    """,
    'category': 'Enchancement',
    'version': '16.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'account', 'purchase', 'stock', 'product'],

    # always loaded
    'data': [
        'views/views.xml',
    ],
}
