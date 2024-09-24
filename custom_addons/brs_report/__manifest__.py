{
    'name': 'BRS Reports',
    'version': '1.0',
    'category': 'Accounting',
    'sequence': 2,
    'author': 'Futurenet',
    'icon': "/brs_report/static/img/icon.png",
    'description': """ BRS Statement """
        ,
    'depends': [ 'base','report_intrastat',
                 'account',
                    ],       
   
    'data': [
            'views/brs_statement_view.xml',
            'views/daywise_brs_sequence.xml',
            'security/ir.model.access.csv',

                        ],
  
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
    
}
