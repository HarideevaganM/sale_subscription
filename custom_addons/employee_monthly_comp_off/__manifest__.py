# -*- coding: utf-8 -*-
{
    'name': 'Employees Monthly Comp Off Leaves',
    'version': '1.0',
    'sequence': 145,
    "author": "Knacktechs Solutions",
    'summary': 'Employees Monthly Comp Off Leaves',
    'license': 'LGPL-3',
    'category': 'Human Resources',
    'website':'www.knacktechs.com',
    'images': [
        'static/description/compoff.jpg'
    ],
    'description': """
""",
    'depends': ['base','hr','hr_holidays','hr_contract','hr_attendance','hr_payroll','resource'],
    'data': [
        'data/bt_hr_overtime_data.xml',
        'security/ir.model.access.csv',
        'views/hr_view.xml',
        'views/bt_hr_overtime_view.xml',
        'views/resource_view.xml',

                ],
    'installable': True,
    'application': True,
}
