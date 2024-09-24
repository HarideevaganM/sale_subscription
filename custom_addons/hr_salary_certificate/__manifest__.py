# -*- coding: utf-8 -*-

{
    'name': 'HR Salary Certificate',
    'description': """ Salary Certificate """,
    'summary': 'Salary Certificate',
    'depends': ['hr'],
    'data': [
        'report/report_extend.xml',
        'report/report_action.xml',
        'report/report_salary_certificate.xml',
        'views/hr_views.xml',
    ],
    'installable': True,
    'application': True,
}
