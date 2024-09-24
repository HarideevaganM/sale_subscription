# -*- coding: utf-8 -*-
{
    'name': "FMS HR Reports",
    'summary': """This module includes reports for Human Resource Management""",
    'description': """This module includes reports for Human Resource Management""",
    'author': "Futurenet Technologies",
    'website': "http://www.futurenet.in",
    'category': 'Human Resource',
    'version': '16.0.1',
    'depends': ['base', 'hr_payroll_community','bank_advice_report'],
    'data': [
        'security/ir.model.access.csv',
        'views/payslip_summary_report.xml',
    ],
}
