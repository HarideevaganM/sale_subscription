{
    'name': 'Journal Voucher Report',
    'version': '16.0.1',
    'category': 'Accounting',
    'summary':
    'Accounting customization',
    'author': 'Futurenet Technologies',
    'icon': "/journal_reports/static/img/icon.png",
    'depends': ['account'],
    
    'data': [
        'report/cheque_payment_report.xml',
        'report/journal_voucher_report.xml',
  
        ],
        
    'installable': True,
    'auto_install': False,
    'application': True,
}
