# -*- coding: utf-8 -*-
{
    'name': 'Manual Bank Reconciliation',
    'version': '16.0.1.0',
    'author': 'Futurenet Technologies India Pvt Ltd',
    'company': 'Futurenet Technologies India Pvt Ltd',
    'website': 'http://www.futurenet.in',
    'category': 'Accounting',
    'summary': 'Replacing default method by traditional',
    'description': """ Replacing default bank statement reconciliation method by traditional way """,
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_line_view.xml',
        'views/account_journal_dashboard_view.xml',
        'wizard/bank_statement_wiz_view.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'auto_install': False,
}
