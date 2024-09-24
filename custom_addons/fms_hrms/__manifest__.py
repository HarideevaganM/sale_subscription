# -*- coding: utf-8 -*-
{
    'name': 'FMS TECH -- Hr Employee',
    'version': '15.0.1.0.0',
    'summary': """Customized HRMS module for FMS-Tech which includes 
                    1. Employee Master 
                    2. Employee Documents 
                    3. Insurance details With Expiry Notifications and
                    4. Leave management""",
    'category': 'HR Employee',
    'depends': ['base','hr_contract', 'hr','hr_attendance','hr_holidays','hr_payroll_community','mail', 'hr_gamification','hr_expense','account'],
    # 'IT_asset_module',
    'data': [
        'security/ir.model.access.csv',
        'security/hr_insurance_security.xml',
        #~ 'security/hr_notification_cron.xml',
        'views/hr_payslip_view.xml',
        'views/hr_employee_view.xml',
        'views/employee_insurance_view.xml',
        'views/insurance_salary_stucture.xml',
        'views/hr_employee_view.xml',
        'views/salary_advance.xml',
        'views/salary_structure.xml',
        'reports/payslip_report_templates.xml',
        'reports/employee_offer_letter.xml',
        #~ 'reports/payslip_summary_report.xml',
        
    ],
    'installable': True,
}
