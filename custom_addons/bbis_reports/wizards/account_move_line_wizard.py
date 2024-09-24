# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PrintBbisAccountingReports(models.TransientModel):
    _name = 'account_ml.bbis_reports'
    _description = 'Wizard: Print Accounting Reports'

    account_reports = fields.Selection([('financial_performance', 'Financial Performance'),
                                        ('sales', 'Sales Report'),
                                        ('device_installations', 'Device Installations'),
                                        ('receipts', 'Monthly Receipts'),
                                        ('receivables', 'Receivable'),
                                        ('aged_receivable', 'Aged Receivable'),
                                        ('aged_payable', 'Aged Payable'),
                                        ('soa', 'Statement of Account'),
                                        ('ledger', 'Ledger Account - Partner'),
                                        ('ledger_account', 'Ledger Account - Accounts')], string='Account Reports',
                                       default="financial_performance")
    date_filter = fields.Selection([('this_year', 'This Year'),
                                    ('last_year', 'Last Year'),
                                    ('custom', 'Custom')], string='Date Filter', default="this_year", required=True)
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries')], string='Target Moves',
                                   default="posted")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    comparison = fields.Boolean(string='Enable Comparison', default=False)
    include_sales_qty = fields.Boolean(string='Display Quantity', default=False)
    include_tax = fields.Boolean(string='Display Tax', default=False)
    include_cr = fields.Boolean(string='Display Credit', default=False)
    include_db = fields.Boolean(string='Display Debit', default=False)
    client = fields.Many2one('res.partner', string='Client Name')
    soa_start_date = fields.Date("Start Date", default=fields.Date.today)
    aged_receivable_date = fields.Date("Start Date", default=fields.Date.today)
    bank = fields.Many2one('account.journal', string='Bank Account', domain=[('type', '=', 'bank')],
                                         default=7)
    account_type = fields.Selection([('receivable', 'Receivable'), ('payable', 'Payable')], string='Account Type',
                                    default="receivable")
    account = fields.Many2one('account.account', string='Account Name')
    # Field for find out the subsequent payment between this date.
    subsequent_pay_date = fields.Date("Subsequent Payment Until")
    page_break_notes = fields.Boolean("Page Break Notes")

    #@api.multi
    def print_reports(self):
        # If the user is from billing user need to block all the reports from Download reports except Statement of account.
        user = self.env.user
        billing_users = user.has_group('bbis_reports.group_accounts_report_users')
        if billing_users:
            if self.account_reports != 'soa':
                raise ValidationError('You are not allow to take this report.')

        data = {
            'model': 'account_ml.bbis_reports',
            'form': self.read()[0]
        }
        template = ''

        for r in self:
            if r.account_reports == 'financial_performance':
                template = 'bbis_reports.bbis_reports_financial_performance'
                if r.comparison:
                    template = 'bbis_reports.bbis_reports_financial_performance_comp'
            if r.account_reports == 'sales':
                template = 'bbis_reports.bbis_reports_sales'
            if r.account_reports == 'receipts':
                template = 'bbis_reports.bbis_reports_receipts'
            if r.account_reports == 'receivables':
                template = 'bbis_reports.bbis_reports_receivables'
            if r.account_reports == 'aged_receivable':
                template = 'bbis_reports.bbis_reports_age_receivables'
            if r.account_reports == 'device_installations':
                template = 'bbis_reports.bbis_reports_device_installations'
            if r.account_reports == 'soa':
                template = 'bbis_reports.bbis_reports_statement_of_account'
            if r.account_reports == 'aged_payable':
                template = 'bbis_reports.bbis_reports_age_payables'

        if template == '':
            raise ValidationError('Please select account reports to be printed.')

        return self.env.ref(template).report_action(self, data=data)

    #@api.multi
    def print_xlsx_report(self):
        # If the user is from billing user need to block all the reports from Download reports except Statement of account.
        user = self.env.user
        billing_users = user.has_group('bbis_reports.group_accounts_report_users')
        if billing_users:
            if self.account_reports not in ('soa', 'ledger'):
                raise ValidationError('You are not allow to take this report.')

        data = {
            'model': 'account_ml.bbis_reports',
            'form': self.read()[0]

        }
        template = ''
        for r in self:
            if r.account_reports == 'soa':
                template = 'bbis_reports.statement_of_account_report_xlsx'
            elif r.account_reports == 'ledger':
                template = 'bbis_reports.ledger_account_report_xlsx'
            elif r.account_reports == 'device_installations':
                template = 'bbis_reports.device_installation_report_xlsx'
            elif r.account_reports == 'aged_receivable':
                template = 'bbis_reports.aged_receivables_report_xlsx'
            # Ledger Account - Account Reports.
            elif r.account_reports == 'ledger_account':
                template = 'bbis_reports.ledger_account_coa_report_xlsx'

            if r.account_reports == 'soa' or r.account_reports == 'ledger':
                if not r.client:
                    raise ValidationError('Please select a Customer.')
            if r.account_reports == 'aged_receivable':
                if not r.subsequent_pay_date:
                    raise ValidationError('Please select the Subsequent Payment Date.')
        if template == '':
            raise ValidationError('Please select account reports to be printed.')

        return self.env.ref(template).report_action(self, data=data)

