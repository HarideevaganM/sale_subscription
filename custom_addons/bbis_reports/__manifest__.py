# -*- coding: utf-8 -*-
{
    'name': "BBIS Reports/Requirements",

    'summary': """
        This is a module for BBIS Reports and Requirements
        for Sales, Accounting, Customer Support""",

    'description': """
        BBIS Reports and Requirements includes different custom reports and functionalities for
        for Sales, Accounting, Customer Support, etc.
    """,

    'author': "Black Box Integrated Systems LLC",
    'website': "https://fms-tech.com",

    'category': 'Reports',
    'version': '0.1',
    'sequence': -11,

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'fms_repair', 'fms_sale', 'mail', 'contacts', 'account', 'fms_customer_support',
                'report_xlsx', 'purchase'],

    # always loaded
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/accounting_reports_group.xml',
        'security/security.xml',
        # reports
        # 'reports/assets.xml',
        'reports/header.xml',
        'reports/footer.xml',
        'reports/tax_invoice.xml',
        'reports/tax_invoice_inclusive.xml',
        'reports/installation_certificate.xml',
        'reports/installation_certificate_multi.xml',
        'reports/sale_quotation_order.xml',
        'reports/sale_quotation_order_inclusive.xml',
        'reports/service_quotation_order.xml',
        'reports/job_card.xml',
        'reports/job_card_rma.xml',
        'reports/purchase_order.xml',
        'reports/acct_financial_performance_scheds.xml',
        'reports/acct_financial_performance.xml',
        'reports/acct_financial_performance_comp.xml',
        'reports/acct_sales_report.xml',
        'reports/acct_receipts_report.xml',
        'reports/acct_receivables.xml',
        'reports/acct_age_receivables.xml',
        'reports/acct_statement_of_account.xml',
        'reports/acct_device_installation.xml',
        'reports/sales_report.xml',
        'reports/ledger_account_xlsx.xml',
        'reports/acct_age_payables.xml',
        'reports/tax_credit_note.xml',
        'reports/tax_credit_note_inclusive.xml',
        'reports/delivery_order.xml',
        # data
        'data/sale_order_email_templates.xml',
        'data/service_order_email_template.xml',
        'data/update_due_customer_scheduler.xml',
        'data/closed_support_ticket_mail.xml',
        # views
        'views/mail_compose_message_inherit.xml',
        'views/inclusive_order_line.xml',
        'views/sale_order_line_inherit.xml',
        'views/sale_order_inherit.xml',
        'views/inclusive_invoice_line.xml',
        'views/account_invoice_inherit.xml',
        'views/job_card_inherit.xml',
        'views/customer_support_inherit.xml',
        'views/account_move_line_inherit.xml',
        'views/account_payment_inherit.xml',
        'views/device_movement.xml',
        'views/account_move_report.xml',
        'views/res_partner_inherit.xml',
        'views/res_partner_bank_inherit.xml',
        'views/vehicle_master_inherit.xml',
        'views/stock_move_views_inherit.xml',
        'views/stock_production_lot_inherit.xml',
        'views/sale_subscription_inherit.xml',
        'views/purchase_order_inherit.xml',
        'views/account_move_inherit.xml',
        'views/installation_certificate_inherit.xml',
        'views/fms_customer_support_inherit.xml',
        'views/crm_lead_inherit.xml',
        'views/stock_picking_inherit.xml',
        'views/accounting_reports_menu.xml',
        # wizards
        'wizards/job_card_print_inst_certificates.xml',
        'wizards/account_move_line_wizard.xml',
        'wizards/bbis_sales_subscription_wizard.xml',
        'wizards/sale_order_report_wizard.xml',
        'wizards/bbis_sales_subscription_renewal_wizard.xml',
        'wizards/bbis_support_ticket_wizard.xml',
        'wizards/update_po_so_invoice_status.xml',
        'wizards/subscription_install_certificate.xml',
        'wizards/so_line_multi_update.xml',
        'wizards/invoice_line_multi_update.xml',
        'wizards/job_card_wizard_inherit.xml',
    ],
    'assets': {
        'web.report_assets': [
            '/bbis_reports/static/src/css/tax_invoice.css',
            '/bbis_reports/static/src/css/installation_certificate.css',
            '/bbis_reports/static/src/less/quotation_order.less',
            '/bbis_reports/static/src/less/job_card.less',
            '/bbis_reports/static/src/less/purchase_order.less',
            '/bbis_reports/static/src/less/accounting-reports.less',
            '/bbis_reports/static/src/less/delivery-report.less',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
