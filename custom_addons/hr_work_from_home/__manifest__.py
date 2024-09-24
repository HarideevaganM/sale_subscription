# -*- coding: utf-8 -*-

{
    'name': 'HR Work From Home',
    'description': """ HR work from home """,
    'summary': 'HR work from home',
    'depends': ['hr', 'hr_extended'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_extend.xml',
        'report/report_action.xml',
        'report/report_work_from_home.xml',
        'views/mail_template.xml',
        'views/hr_work_home.xml',
        'views/hr_ticket_view.xml'
    ],
    'installable': True,
    'application': True,
}
