# -*- coding: utf-8 -*-
{
    'name': "BBIS Attendance Upload",

    'summary': """Upload BBIS Attendance using excel sheet""",

    'description': """
        This module will integrate BBIS attendance from biometric device to Odoo attendance.
    """,

    'author': "FMS Tech.",
    'website': "https://fms-tech.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'HR',
    'version': '0.1',
    'sequence': -10,

    # any module necessary for this one to work correctly
    'depends': ['hr_attendance', 'hr_holidays', 'hr_leave_report', 'base', 'mail', 'bbis_hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/bbis_attendance_temp.xml',
        'views/assets.xml',
        'views/hr_attendance_inherit.xml',
        'views/employee_attendance.xml',
        'wizard/custom_attendance_import.xml',
        'reports/assets.xml',
        'wizard/attendance_report_wizard.xml',

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