
{
    'name': 'Consolidated Invoice',
    'summary': """Consolidated Invoice""",
    'description': """Consolidated Invoice""",
    'depends': ['base', 'account', 'fms_sale'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'wizard/consolidated_invoice.xml',
        'views/invoice.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

