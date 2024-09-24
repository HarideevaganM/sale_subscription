import os

from odoo import api, models, _
from datetime import datetime
from odoo.exceptions import ValidationError
import odoo.tools as tools
import xlsxwriter
from io import BytesIO
from urllib.request import urlopen


class BbisAcctSalesReport(models.AbstractModel):
    _name = 'report.bbis_reports.statement_of_account'
    _description = 'BBIS Statement of Account Report'

    def _get_reconcile(self, line, mode):
        if mode == 'credit':
            rec = self.env['account.partial.reconcile'].search([('debit_move_id', '=', line['id'])])
            aml = rec.mapped('amount')
            amount = sum(aml)
        else:
            rec = self.env['account.partial.reconcile'].search([('credit_move_id', '=', line['id'])])
            aml = rec.mapped('amount')
            amount = sum(aml)

        return amount

    def _get_accounting_data(self, data):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        d = data['start_date']
        self.env.cr.execute(
            """
            select
            aml.id as id,
            pr.name as partner,
            aml.name as label,
            aml.date as date,
            aml.date_maturity as due_date,
            am.name as invoice,
            am.narration as description,
            am.ref as ref,
            aml.debit as debit,
            aml.credit as credit,
            aml.balance as balance,
            aml.debit_cash_basis as debit_cash,
            aml.amount_residual as amount_residual,
            (CASE
                WHEN aml.credit > 0 
                THEN (select SUM(amount) from account_partial_reconcile where credit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
                WHEN aml.debit > 0 
                THEN (select SUM(amount) from account_partial_reconcile where debit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
                END
            ) as transaction_credit,
            extract(day from '%s'::timestamp - ai.date_invoice::timestamp) as days_overdue,
            aj.name as journal
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_journal aj on aj.id = aml.journal_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_invoice ai on aml.invoice_id = ai.id
            LEFT JOIN res_partner pr on aml.partner_id = pr.id
            WHERE ac.internal_type = '%s'
            AND aml.date <= '%s'
            AND pr.id = %d AND am.state in %s
            ORDER BY aml.date ASC
            """ % (d, d, d, data['account_type'], d, data['partner'], move_state))

        accounting_data = self.env.cr.dictfetchall()

        return {'list': accounting_data}

    @api.model
    def _get_report_values(self, docids, data=None):

        form_data = data['form']
        company = self.env.user.company_id
        default_bank = self.env['account.journal'].browse(7)

        if not form_data['client']:
            raise ValidationError(_('Please select a client.'))
        if not form_data['soa_start_date']:
            raise ValidationError(_('Please select start date.'))

        client_id = form_data['client'][0]
        bank_id = form_data['bank'][0] if form_data['bank'] else False

        partner = self.env['res.partner'].search([('id', '=', client_id)], limit=1)
        bank = self.env['account.journal'].browse(bank_id)
        page_break_notes = form_data['page_break_notes']

        # To be used in test only
        # partner = self.env['res.partner'].search([('name', '=', 'Air Conditionin Inst Elect & Mech Engg Est - ACECO')], limit=1)
        # bank = self.env['account.journal'].browse(7)
        # client_id = partner.id
        #
        # form_data = {
        #     'soa_start_date': '2022-02-24',
        #     'date_filter': 'this_year',
        #     'target_move': 'posted',
        #     'client': partner,
        #     'account_type': 'receivable',
        #     'bank': bank
        # }

        start_date = datetime.strptime(form_data['soa_start_date'], '%Y-%m-%d')

        final_data = {
            'start_date': start_date,
            'date': form_data['date_filter'],
            'move_state': form_data['target_move'],
            'partner': client_id,
            'account_type': form_data['account_type'],
        }

        return {
            'doc_model': 'account.move.line',
            'move_state': form_data['target_move'],
            'date': form_data['date_filter'],
            'company': company,
            'partner': partner,
            'account_type': form_data['account_type'],
            'bank': bank,
            'default_bank': default_bank,
            'start_date': start_date,
            'data': self.get_accounting_data(final_data),
            'get_reconcile': self.get_reconcile,
            'page_break_notes': page_break_notes
        }


class BbisSOAExcel(models.AbstractModel):
    _name = 'report.bbis_reports.statement_of_account_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Statement Of Account'

    def generate_xlsx_report(self, workbook, data, partner):
        total_amount = 0
        sub_total_amount = 0
        form_data = data['form']
        company = self.env.user.company_id
        default_bank = self.env['account.journal'].browse(7)

        if not form_data['client']:
            raise ValidationError(_('Please select a client.'))
        if not form_data['soa_start_date']:
            raise ValidationError(_('Please select start date.'))

        client_id = form_data['client'][0]
        bank_id = form_data['bank'][0] if form_data['bank'] else default_bank.id

        partner = self.env['res.partner'].search([('id', '=', client_id)], limit=1)
        bank = self.env['account.journal'].browse(bank_id)

        move_state = "('posted')" if form_data['target_move'] == 'posted' else "('posted', 'draft')"
        date = form_data['soa_start_date']
        account_type = form_data['account_type']

        sheet = workbook.add_worksheet('Statement Of Account')
        row = 25
        header_row = 11

        self.env.cr.execute(
            """
            select
            aml.id as id,
            pr.name as partner,
            aml.name as label,
            aml.date as date,
            aml.date_maturity as due_date,
            am.name as invoice,
            am.narration as description,
            am.ref as ref,
            aml.debit as debit,
            aml.credit as credit,
            aml.balance as balance,
            aml.debit_cash_basis as debit_cash,
            aml.amount_residual as amount_residual,
            (CASE
                WHEN aml.credit > 0 
                THEN (select COALESCE(SUM(amount),0) from account_partial_reconcile where credit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
                ELSE (select COALESCE(SUM(amount),0) from account_partial_reconcile where debit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
                END
            ) as transaction_credit,
            extract(day from '%s'::timestamp - ai.date_invoice::timestamp) as days_overdue,
            aj.name as journal
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_journal aj on aj.id = aml.journal_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_invoice ai on aml.invoice_id = ai.id
            LEFT JOIN res_partner pr on aml.partner_id = pr.id
            WHERE ac.internal_type = '%s'
            AND aml.date <= '%s'
            AND pr.id = %d AND am.state in %s
            ORDER BY aml.date ASC
            """ % (date, date, date, account_type, date, client_id, move_state))

        accounting_data = self.env.cr.dictfetchall()

        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'font_size': 20})
        totals_style = workbook.add_format(
            {'bold': True, 'align': 'center', 'bg_color': '#2C286C', 'font_color': 'white', 'border': True, 'font_size': 10})
        normal = workbook.add_format({'align': 'center', 'font_size': 10})
        header_row_style = workbook.add_format({'text_wrap': True, 'bold': True, 'align': 'center', 'border': True, 'bg_color': '#F05A29',
                                                'font_color': 'white', 'valign': 'vcenter', 'font_size': 10})
        data_style = workbook.add_format({'align': 'left', 'font_size': 10})
        content_row_style = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'border': True, 'valign': 'vcenter', 'font_size': 10})
        content_text_row_style = workbook.add_format({'align': 'left', 'border': True, 'font_size': 10})
        totals_style = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'border': True, 'bold': True})
        footer_style = workbook.add_format({'align': 'left', 'text_wrap': True, 'border': True, 'font_size': 10})
        footer_title = workbook.add_format({'border': True, 'align': 'left', 'bold': True, 'font_size': 10})
        header_title = workbook.add_format({'align': 'left', 'bold': True, 'font_size': 10})
        text_format = workbook.add_format({'text_wrap': True, 'align': 'left', 'border': True, 'valign': 'vcenter', 'font_size': 10})
        text_format_invoice = workbook.add_format({'text_wrap': True, 'align': 'center', 'border': True, 'valign': 'vcenter', 'font_size': 10})
        company_text_format = workbook.add_format({'text_wrap': True, 'align': 'right', 'font_size': 10})

        sheet.merge_range('F2:I2', company.street, company_text_format)
        sheet.merge_range('F3:I3', company.street2, company_text_format)
        if company.city:
            sheet.merge_range('F4:I4', company.city, company_text_format)
        else:
            sheet.merge_range('F4:I4', ' ')
        # if company.zip:
        #     sheet.merge_range('H4:I4', company.zip, company_text_format)
        # else:
        #     sheet.merge_range('H4:I4', ' ')
        if company.country_id.name:
            sheet.merge_range('F5:I5', company.country_id.name, company_text_format)
        else:
            sheet.merge_range('F5:I5', ' ')
        if company.phone:
            sheet.merge_range('F6:I6', 'Tel.No  :,' + company.phone, company_text_format)
        else:
            sheet.merge_range('F6:I6', ' ')
        sheet.merge_range('F7:I7', company.email, company_text_format)
        sheet.merge_range('F8:I8', company.website, company_text_format)

        ad_path = tools.config['addons_path']
        custom_path = ad_path.rsplit(',', 1)[1]
        custom_path = custom_path+'/bbis_reports/static/src/img/blackbox-logo.jpg'
        sheet.insert_image('A2', custom_path)

        sheet.merge_range('A{}:I{}'.format(header_row, header_row), 'STATEMENT OF ACCOUNT', title)
        sheet.merge_range('A{}:I{}'.format(header_row+1, header_row+1), 'As of ' + date + '', normal)

        sheet.merge_range('A{}:I{}'.format(header_row+2, header_row+2), ' ')
        sheet.merge_range('A{}:I{}'.format(header_row+3, header_row+3), ' ')
        sheet.merge_range('A{}:I{}'.format(header_row+4, header_row+4), ' ')

        sheet.write('A{}'.format(header_row+5), 'Customer', header_title)
        sheet.write('B{}'.format(header_row+5), ':', normal)
        sheet.merge_range('C{}:F{}'.format(header_row+5, header_row+5), partner.name, data_style)

        sheet.write('A{}'.format(header_row+6), 'Address', header_title)
        sheet.write('B{}'.format(header_row+6), ':', normal)
        sheet.merge_range('C{}:F{}'.format(header_row+6, header_row+6), partner.street, data_style)

        if partner.street2:
            sheet.merge_range('C{}:F{}'.format(header_row + 7, header_row + 7), partner.street2, data_style)
        elif partner.city:
            sheet.merge_range('C{}:F{}'.format(header_row + 7, header_row + 7), partner.city, data_style)
        else:
            sheet.merge_range('C{}:F{}'.format(header_row + 7, header_row + 7), ' ')

        sheet.write('A{}'.format(header_row+8), 'Tel No.', header_title)
        sheet.write('B{}'.format(header_row+8), ':', normal)
        if partner.phone:
            sheet.merge_range('C{}:F{}'.format(header_row+8, header_row+8), partner.phone, data_style)
        else:
            sheet.merge_range('C{}:F{}'.format(header_row+8, header_row+8), ' ')

        sheet.write('A{}'.format(header_row+9), 'Mobile No.', header_title)
        sheet.write('B{}'.format(header_row+9), ':', normal)
        if partner.mobile:
            sheet.merge_range('C{}:F{}'.format(header_row+9, header_row+9), partner.mobile, data_style)
        else:
            sheet.merge_range('C{}:F{}'.format(header_row+9, header_row+9), ' ')

        sheet.write('A{}'.format(header_row+10), 'Email', header_title)
        sheet.write('B{}'.format(header_row+10), ':', normal)
        if partner.email:
            sheet.merge_range('C{}:F{}'.format(header_row+10, header_row+10), partner.email, data_style)
        else:
            sheet.merge_range('C{}:F{}'.format(header_row+10, header_row+10), ' ')

        sheet.write('A{}'.format(header_row+11), 'TRN.', header_title)
        sheet.write('B{}'.format(header_row+11), ':', normal)
        sheet.merge_range('C{}:F{}'.format(header_row+11, header_row+11), partner.vat, data_style)

        sheet.merge_range('A{}:I{}'.format(header_row+12, header_row+12), ' ')

        code_text = 'Customer Code:'
        if account_type == 'payable':
            code_text = 'Vendor Code:'

        sheet.write('H{}'.format(header_row+5), code_text, header_title)
        if partner.customer_id:
            sheet.write('I{}'.format(header_row+5), partner.customer_id, data_style)
        else:
            sheet.write('I{}'.format(header_row+5), ' ')

        sheet.write('H{}'.format(header_row+6), 'Payment Terms:', header_title)
        if partner.property_payment_term_id.name:
            sheet.write('I{}'.format(header_row+6), partner.property_payment_term_id.name, data_style)
        else:
            sheet.write('I{}'.format(header_row+6), ' ')

        sheet.merge_range('A{}:B{}'.format(row, row), 'Date', header_row_style)
        nrow = row-1
        sheet.write(nrow, 2, 'Ref. No.', header_row_style)
        sheet.write(nrow, 3, 'Description', header_row_style)
        sheet.merge_range('E{}:F{}'.format(row, row), 'Original Amount', header_row_style)

        transaction_text = 'Transaction Credit'
        if account_type == 'payable':
            transaction_text = 'Transaction Debit'

        sheet.write(nrow, 6, transaction_text, header_row_style)
        sheet.write(nrow, 7, 'Pending Amount', header_row_style)
        sheet.write(nrow, 8, 'Overdue by Days', header_row_style)

        sheet.set_row(nrow, 26)
        sheet.set_column('A:A', 10)
        sheet.set_column('B:B', 0.6)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 30)
        sheet.set_column('E:E', 0.5)
        sheet.set_column('F:F', 14)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)

        if account_type == 'receivable':
            for data in accounting_data:
                if data['journal'] in ('Tax Invoices', 'Cash Invoice', 'Miscellaneous Operations'):

                    if data['transaction_credit'] > 0:
                        if data['credit'] > 0:
                            due_amount = data['balance'] + data['transaction_credit']
                        else:
                            due_amount = data['balance'] - data['transaction_credit']
                    else:
                        due_amount = data['balance']

                    if due_amount != 0:
                        row = row + 1
                        new_row = row - 1

                        sheet.merge_range('A{}:B{}'.format(row, row), data['date'], text_format_invoice)
                        sheet.write(new_row, 2, data['invoice'], text_format_invoice)
                        if data['description']:
                            sheet.write('D{}'.format(row), data['description'], text_format)
                        else:
                            sheet.write('D{}'.format(row), data['ref'], text_format)
                        sheet.merge_range('E{}:F{}'.format(row, row), data['balance'], content_row_style)
                        sheet.write(new_row, 6, data['transaction_credit'], content_row_style)
                        sheet.write(new_row, 7, due_amount, content_row_style)
                        sheet.write(new_row, 8, data['days_overdue'], text_format_invoice)
                        total_amount += due_amount

            # sheet.merge_range('A{}:f{}'.format(row, row), ' ', text_format)
            sheet.write(row, 6, 'SUB TOTAL', totals_style)
            sheet.write(row, 7, total_amount, totals_style)
            row = row + 1

            for data in accounting_data:
                if data['journal'] not in ('Tax Invoices', 'Cash Invoice', 'Miscellaneous Operations'):

                    if data['transaction_credit'] > 0:
                        if data['credit'] > 0:
                            due_amount = data['balance'] + data['transaction_credit']
                        else:
                            due_amount = data['balance'] - data['transaction_credit']
                    else:
                        due_amount = data['balance']

                    if due_amount != 0:
                        row = row + 1
                        new_row = row - 1

                        sheet.merge_range('A{}:B{}'.format(row, row), data['date'], text_format_invoice)
                        sheet.write(new_row, 2, data['invoice'], text_format_invoice)
                        if data['description']:
                            sheet.write('D{}'.format(row), data['description'], text_format)
                        else:
                            sheet.write('D{}'.format(row), data['ref'], text_format)
                        sheet.merge_range('E{}:F{}'.format(row, row), data['balance'], content_row_style)
                        sheet.write(new_row, 6, data['transaction_credit'], content_row_style)
                        sheet.write(new_row, 7, due_amount, content_row_style)
                        sheet.write(new_row, 8, data['days_overdue'], text_format_invoice)
                        total_amount += due_amount

            # sheet.merge_range('A{}:E{}'.format(row, row), ' ')
            sheet.write(row, 6, 'TOTAL', totals_style)
            sheet.write(row, 7, total_amount, totals_style)
        else:
            # Payable
            for data in accounting_data:
                if data['journal'] in ('Vendor Bills', 'Expenses', 'Miscellaneous Operations'):
                    balance = abs(data['balance'])
                    transaction_credit = 0
                    if data['transaction_credit'] > 0:
                        transaction_credit = data['transaction_credit'] * -1
                        if data['credit'] < 0:
                            due_amount = balance - transaction_credit
                        else:
                            due_amount = balance + transaction_credit
                    else:
                        due_amount = balance

                    if due_amount != 0:
                        row = row + 1
                        new_row = row - 1

                        sheet.merge_range('A{}:B{}'.format(row, row), data['date'], text_format_invoice)
                        sheet.write(new_row, 2, data['ref'], text_format_invoice)
                        if data['description']:
                            sheet.write('D{}'.format(row), data['description'], text_format)
                        else:
                            sheet.write('D{}'.format(row), data['ref'], text_format)
                        sheet.merge_range('E{}:F{}'.format(row, row), balance, content_row_style)
                        sheet.write(new_row, 6, transaction_credit, content_row_style)
                        sheet.write(new_row, 7, due_amount, content_row_style)
                        sheet.write(new_row, 8, data['days_overdue'], text_format_invoice)
                        total_amount += due_amount

            sheet.write(row, 6, 'SUB TOTAL', totals_style)
            sheet.write(row, 7, total_amount, totals_style)
            row = row + 1

            for data in accounting_data:
                if data['journal'] not in ('Vendor Bills', 'Expenses', 'Miscellaneous Operations'):

                    if data['transaction_credit'] > 0:
                        if data['credit'] > 0:
                            due_amount = (data['balance'] * -1) + (data['transaction_credit'] * -1)
                        else:
                            due_amount = (data['balance'] * -1) - (data['transaction_credit'] * -1)
                    else:
                        due_amount = data['balance'] * -1

                    if due_amount != 0:
                        row = row + 1
                        new_row = row - 1

                        sheet.merge_range('A{}:B{}'.format(row, row), data['date'], text_format_invoice)
                        sheet.write(new_row, 2, data['ref'], text_format_invoice)
                        if data['description']:
                            sheet.write('D{}'.format(row), data['description'], text_format)
                        else:
                            sheet.write('D{}'.format(row), data['ref'], text_format)
                        sheet.merge_range('E{}:F{}'.format(row, row), data['balance'] * -1, content_row_style)
                        sheet.write(new_row, 6, data['transaction_credit'], content_row_style)
                        sheet.write(new_row, 7, due_amount, content_row_style)
                        sheet.write(new_row, 8, data['days_overdue'], text_format_invoice)
                        total_amount += due_amount

            sheet.write(row, 6, 'TOTAL', totals_style)
            sheet.write(row, 7, total_amount, totals_style)

        footer_row = row + 3

        if account_type == 'receivable':
            sheet.merge_range('A{}:D{}'.format(footer_row, footer_row+6), 'Notes:\n1. Please settle dues within credit terms stated '
                                                                        'otherwise credit facility will be forfeited and/or '
                                                                        'penalty will be applied. \n2. Statement will be assumed correct if no dispute or request for revision is received within ten (10) days.\n3. Payments by cheque for invoices included in this statement are valid only upon realization.', footer_style)
            sheet.merge_range('F{}:I{}'.format(footer_row, footer_row), 'Please issue all payments on below Company bank account details:', footer_style)
            sheet.write('F{}'.format(footer_row+1), 'Account Name:', footer_title)
            if company.acc_name:
                sheet.merge_range('G{}:I{}'.format(footer_row+1, footer_row+1), company.acc_name, footer_style)
            else:
                sheet.merge_range('G{}:I{}'.format(footer_row + 1, footer_row + 1), ' ', footer_style)

            sheet.write('F{}'.format(footer_row+2), 'Account Number:', footer_title)
            if bank.bank_acc_number:
                sheet.merge_range('G{}:I{}'.format(footer_row + 2, footer_row + 2),  bank.bank_acc_number, footer_style)
            else:
                sheet.merge_range('G{}:I{}'.format(footer_row + 2, footer_row + 2), ' ', footer_style)

            sheet.write('F{}'.format(footer_row+3), 'IBAN Number:', footer_title)
            if bank.bank_account_id.iban:
                sheet.merge_range('G{}:I{}'.format(footer_row + 3, footer_row + 3),  bank.bank_account_id.iban, footer_style)
            else:
                sheet.merge_range('G{}:I{}'.format(footer_row + 3, footer_row + 3), ' ', footer_style)

            sheet.write('F{}'.format(footer_row+4), 'Bank Name:', footer_title)
            if bank.bank_id.name:
                sheet.merge_range('G{}:I{}'.format(footer_row + 4, footer_row + 4),  bank.bank_id.name, footer_style)
            else:
                sheet.merge_range('G{}:I{}'.format(footer_row + 4, footer_row + 4), ' ', footer_style)

            sheet.write('F{}'.format(footer_row+5), 'Bank Address:', footer_title)
            if bank.bank_id.state:
                sheet.merge_range('G{}:I{}'.format(footer_row + 5, footer_row + 5), bank.bank_id.state.name, footer_style)
            else:
                sheet.merge_range('G{}:I{}'.format(footer_row + 5, footer_row + 5), ' ', footer_style)

            sheet.write('F{}'.format(footer_row+6), 'SWIFT Code:', footer_title)
            if bank.bank_id.bic:
                sheet.merge_range('G{}:I{}'.format(footer_row + 6, footer_row + 6), bank.bank_id.bic, footer_style)
            else:
                sheet.merge_range('G{}:I{}'.format(footer_row + 6, footer_row + 6), ' ', footer_style)


