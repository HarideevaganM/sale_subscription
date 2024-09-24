# -*- coding: utf-8 -*-

{
    'name': 'Maintenance Process Flow',
    'version': '16.1.0',
    'sequence': 125,
    'category': 'Human Resources',
    'description': """
        Track equipment and manage maintenance requests.""",
    'depends': ['mail','website_support','fms_sale', 'repair'],
    'summary': 'Equipments,Maintenance Tracking,Repairing',
    'data': [
        #~ 'views/maintenance.xml',
        'security/ir.model.access.csv',
        'views/repair_model.xml',
        'data/ir_sequence_data.xml',
    ],
    # 'images':[
    #     'static/description/icon1.png',
    # ],
    #~ 'demo': ['data/maintenance_demo.xml'],
    'installable': True,
    'application': True,
}
