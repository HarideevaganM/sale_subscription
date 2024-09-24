# -*- coding: utf-8 -*-
{
    'name': 'Advanced HR Recruitment',
    'summary': 'Creates validations In HR Recruitment Workflow'
               '(Eg: An application stage cannot be moved to its previous one)',
    'description': """ Once Application stage is set as Contract signed then Users cannot change its value
    """,
    'depends': [
        'base',
        'hr_recruitment'
    ],
    'data': ['views/hr_form_extend.xml'],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'installable': True,
    'auto_install': False,
}
