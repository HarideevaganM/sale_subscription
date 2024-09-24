# -*- coding: utf-8 -*-
{
    'name': 'Employee Summary XLS',
    'version': '16.0',
    "category": "hr",
    'depends': ['hr', 'hr_holidays', 'report_xlsx'],
    'data': [
        'views/action_xls.xml',
        'wizard/emp_summary_wizard.xml',
    ],
    'installable': True,
    'application': True,
}
