# -*- coding: utf-8 -*-
{
    'name': "Open HRMS Vacation Management",
    'version': '16.0.1.0.0',
    'summary': """Manage Employee Vacation""",
    'description': """HR Vacation management""",
    'depends': ['hr_leave_request_aliasing', 'project', 'hr_payroll', 'account'],
    'data': [
        'security/hr_vacation_security.xml',
        'security/ir.model.access.csv',
        'data/hr_payslip_data.xml',
        'views/hr_reminder.xml',
        'data/hr_vacation_data.xml',
        'wizard/reassign_task.xml',
        'views/hr_employee_ticket.xml',
        'views/hr_vacation.xml',
        'views/hr_payslip.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
