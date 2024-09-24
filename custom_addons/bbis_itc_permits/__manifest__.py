# -*- coding: utf-8 -*-
{
    'name': "BBIS ITC Permits",

    'summary': """
        This is a module for BBIS to Create &
        Renew the ITC Permits for the vehicles.""",

    'description': """
        ITC permits includes the creation and renewal of Vehicles of ITC Permits and the related reports..
    """,

    'author': "Black Box Integrated Systems LLC",
    'website': "https://fms-tech.com",

    'category': 'ITC',
    'version': '0.1',
    'sequence': -11,

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'mail', 'contacts', 'report_xlsx', 'fms_sale', 'sale_subscription', 'bbis_reports'],

    # always loaded
    'data': [
        # Security
        'security/itc_mail_group.xml',
        'security/ir.model.access.csv',
        # reports
        'reports/assets.xml',
        'reports/job_completion_certificate.xml',
        'reports/sale_subscription_report_view_inherit.xml',
        'reports/itc_report.xml',
        # data
        'data/itc_expired_update.xml',
        'data/itc_expired_mail.xml',
        # 'data/sale_order_data.xml',
        # views
        'views/sale_order_inherit.xml',
        'views/itc_permit.xml',
        'views/product_product_inherit.xml',
        'views/job_card_inherit.xml',
        'views/account_invoice_inherit.xml',

        # wizards
        'wizards/itc_permit_upload_wizard.xml',
        'wizards/itc_permit_report_wizard.xml',
        'views/menu.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}