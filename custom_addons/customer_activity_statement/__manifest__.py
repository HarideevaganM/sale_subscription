# Copyright 2018 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Partner Activity Statement',
    'version': '16.0.2.1.2',
    'category': 'Accounting & Finance',
    'summary': 'OCA Financial Reports',
    'author': "Eficent, Odoo Community Association (OCA)",
    'website': 'https://github.com/OCA/account-financial-reporting',
    'license': 'AGPL-3',
    'depends': ['base',
        'account',
    ],
    'data': [
        'views/statement.xml',
        'wizard/customer_activity_statement_wizard.xml',
    ],
    'installable': True,
    'application': False,
'assets': {
        'web.report_assets_common': [
            '/customer_activity_statement/static/src/less/layout_statement.scss',
        ],
    },
}
