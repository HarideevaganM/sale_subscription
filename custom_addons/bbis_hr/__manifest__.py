# -*- coding: utf-8 -*-
{
    'name': "BBIS HR Module Requirements",

    'summary': """BBIS HR Module Requirements""",

    'description': """
        BBIS HR Module Requirements
    """,

    'author': "FMS Tech.",
    'website': "https://fms-tech.com",
    'category': 'HR',
    'version': '0.1',
    'sequence': -10,

    # any module necessary for this one to work correctly
    'depends': ['hr_attendance', 'hr_holidays', 'hr_leave_report', 'base', 'mail', 'hr_work_from_home', 'account'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/accrual_process_scheduler.xml',
        'data/hr_securities.xml',
        'data/outside_work_mail_template.xml',
        'data/hr_holidays_mail_template.xml',
        'data/work_from_home_mail_template.xml',
        'reports/year_wise_leave_report.xml',
        'reports/employee_wise_leave_report.xml',
        'reports/employee_leave_report.xml',
        'views/hr_working_branch.xml',
        'views/bbis_leave_adjustments.xml',
        'views/allocation_request_inherit.xml',
        'views/hr_holidays_inherit.xml',
        'views/hr_holidays_status_inherit.xml',
        'views/hr_employee_inherit.xml',
        'views/my_approvals.xml',
        'views/hr_work_outside.xml',
        'views/hr_work_home_inherit.xml',
        'views/hr_expense_inherit.xml',
        'views/hr_work_home_inherit.xml',
        'views/hr_holidays_report.xml',
        'views/ir_attachment.xml',
        'views/employee_menus.xml',
        'wizard/accrual_process.xml',
        'wizard/leave_report_wizard.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'qweb': [
        'static/src/xml/list_view_buttons.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}