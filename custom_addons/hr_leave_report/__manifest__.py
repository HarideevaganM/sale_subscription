# -*- coding: utf-8 -*-

{
    'name': 'HR Leave Extended',
    'description': """ HR Leave Extended """,
    'summary': 'HR Leave Extended',
    'depends': ['hr_holidays', 'hr_work_from_home'],
    'data': [
        'report/report_action.xml',
        'report/report_hr_leave_report.xml',
        'views/hr_holidays_view.xml',
    ],
    'installable': True,
    'application': True,
}
