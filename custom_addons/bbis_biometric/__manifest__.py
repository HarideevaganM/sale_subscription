# -*- coding: utf-8 -*-
{
    'name': "BBIS Biometric Device Integration",

    'summary': """BBIS Biometric Device Integration""",

    'description': """
        BBIS Biometric Device Integration
    """,

    'author': "FMS Tech.",
    'website': "https://fms-tech.com",
    'category': 'HR',
    'version': '0.1',
    'sequence': -10,

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr_attendance', 'bbis_hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/bbis_biometric.xml',
        'views/bbis_message_wizard.xml',
        'wizards/biometric_attendance_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
