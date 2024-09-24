from odoo import api, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import odoo.tools as tools


# Ledger Report - Account Wise Report.
class BbisLedgerAccountExcel(models.AbstractModel):
    _name = 'report.bbis_reports.ledger_account_coa_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Ledger Account - Accounts'

    def generate_xlsx_report(self, workbook, data, account):
        form_data = data['form']
        company = self.env.user.company_id

        if not form_data['soa_start_date']:
            raise ValidationError(_('Please select start date.'))

        account_id = form_data['account'][0]
        account = self.env['account.account'].search([('id', '=', account_id)], limit=1)

        date_now_str = datetime.now().strftime('%d/%m/%Y')
        date_now = datetime.strptime(date_now_str, '%d/%m/%Y')

        move_state = "('posted')" if form_data['target_move'] == 'posted' else "('posted', 'draft')"

        if form_data['date_filter'] == 'this_year':
            this_year = datetime.now()
            date = datetime.strftime(this_year, '%Y-01-01')
            end_date = datetime.strftime(this_year, '%Y-12-31')
        elif form_data['date_filter'] == 'last_year':
            last_year = datetime.now() - relativedelta(years=1)
            date = datetime.strftime(last_year, '%Y-01-01')
            end_date = datetime.strftime(last_year, '%Y-12-31')
        else:
            date = form_data['start_date']
            end_date = form_data['end_date']

        sheet = workbook.add_worksheet('Ledger Account')
        row = 19
        header_row = 11

        # Initial Balance Query Starting
        self.env.cr.execute(
            """
            select
            ac.name as account,
            sum(aml.debit) as debit,
            sum(aml.credit) as credit,
           'Opening Balance' as description,
            sum(aml.balance) as balance,
            sum(aml.amount_residual) as amount_residual,
            (CASE
                WHEN sum(aml.credit) > 0 
                THEN (select COALESCE(SUM(amount),0) from account_partial_reconcile where DATE(max_date) <=  '%s'::timestamp)
                ELSE (select COALESCE(SUM(amount),0) from account_partial_reconcile where DATE(max_date) <=  '%s'::timestamp)
                END
            ) as transaction_credit
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_journal aj on aj.id = aml.journal_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_invoice ai on aml.invoice_id = ai.id
            WHERE aml.date < '%s'
            AND ac.id = %d  AND am.state in %s
            group by ac.name
            """ % (date, date, date, account_id, move_state))

        initial_data = self.env.cr.dictfetchall()
        # Initial Balance  Query End

        # Current transactions queries.
        self.env.cr.execute(
            """
            select
            aml.id as id,
            ac.name as account,
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
            ac.code,
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
            WHERE aml.date >= '%s' and aml.date <= '%s'
            AND ac.id = %d AND am.state in %s
            ORDER BY aml.date ASC
            """ % (date, date, date, date, end_date, account_id, move_state))
        # Current transactions queries End.

        accounting_data = self.env.cr.dictfetchall()

        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'font_size': 20})
        normal = workbook.add_format({'align': 'center', 'font_size': 10})
        header_row_style = workbook.add_format({'text_wrap': True, 'bold': True, 'align': 'center',
                                                'border': True, 'bg_color': '#F05A29',
                                                'font_color': 'white', 'valign': 'vcenter', 'font_size': 10})
        data_style = workbook.add_format({'align': 'left', 'font_size': 10})
        content_row_style = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'border': True,
                                                 'valign': 'vcenter', 'font_size': 10})
        content_text_row_style = workbook.add_format({'align': 'left', 'border': True, 'font_size': 10})
        totals_style = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'border': True, 'bold': True})
        footer_style = workbook.add_format({'align': 'left', 'text_wrap': True, 'border': True, 'font_size': 10})
        footer_title = workbook.add_format({'border': True, 'align': 'left', 'bold': True, 'font_size': 10})
        header_title = workbook.add_format({'align': 'left', 'bold': True, 'font_size': 10})
        text_format = workbook.add_format({'text_wrap': True, 'align': 'left', 'border': True,
                                           'valign': 'vcenter', 'font_size': 10})
        text_format_invoice = workbook.add_format({'text_wrap': True, 'align': 'center', 'border': True,
                                                   'valign': 'vcenter', 'font_size': 10})
        company_text_format = workbook.add_format({'text_wrap': True, 'align': 'right', 'font_size': 10})

        if company.street:
            sheet.merge_range('F2:J2', company.street, company_text_format)
        if company.street2 and company.city:
            sheet.merge_range('F3:J3', company.street2 + ', ' + company.city, company_text_format)
        elif company.street2:
            sheet.merge_range('F3:J3', company.street2, company_text_format)
        else:
            sheet.merge_range('F3:J3', ' ')
        if company.country_id.name:
            sheet.merge_range('F4:J4', company.country_id.name, company_text_format)
        else:
            sheet.merge_range('F4:J4', ' ')
        if company.phone:
            sheet.merge_range('F5:J5', 'Tel.No  :' + company.phone, company_text_format)
        else:
            sheet.merge_range('F5:J5', ' ')
        sheet.merge_range('F6:J6', 'Email :' + company.email, company_text_format)
        sheet.merge_range('F7:J7', 'Website :' + company.website, company_text_format)

        ad_path = tools.config['addons_path']
        custom_path = ad_path.rsplit(',', 1)[1]
        custom_path = custom_path + '/bbis_reports/static/src/img/blackbox-logo.jpg'
        sheet.insert_image('A2', custom_path)

        date = datetime.strptime(date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        from_to_date = '{}  {}'.format(date.strftime('%d-%b-%Y'), ' to  ' + end_date.strftime('%d-%b-%Y'))
        sheet.merge_range('A{}:J{}'.format(header_row, header_row), 'LEDGER ACCOUNT', title)
        sheet.merge_range('A{}:J{}'.format(header_row + 1, header_row + 1), from_to_date, normal)

        sheet.merge_range('A{}:J{}'.format(header_row + 2, header_row + 2), ' ')
        sheet.merge_range('A{}:J{}'.format(header_row + 3, header_row + 3), ' ')
        sheet.merge_range('A{}:J{}'.format(header_row + 4, header_row + 4), ' ')

        sheet.write('A{}'.format(header_row + 5), 'Account Code', header_title)
        sheet.write('B{}'.format(header_row + 5), ':', normal)
        sheet.merge_range('C{}:F{}'.format(header_row + 5, header_row + 5), account.code, data_style)

        sheet.write('A{}'.format(header_row + 6), 'Account Name', header_title)
        sheet.write('B{}'.format(header_row + 6), ':', normal)
        sheet.merge_range('C{}:F{}'.format(header_row + 6, header_row + 6), account.name, data_style)

        sheet.merge_range('A{}:B{}'.format(row, row), 'Date', header_row_style)
        nrow = row - 1
        sheet.write(nrow, 2, 'REF', header_row_style)
        sheet.write(nrow, 3, 'Account', header_row_style)
        sheet.write(nrow, 4, 'Description', header_row_style)
        sheet.merge_range('F{}:G{}'.format(row, row), 'Initial Balance', header_row_style)
        sheet.write(nrow, 7, 'Debit', header_row_style)
        sheet.write(nrow, 8, 'Credit', header_row_style)
        sheet.write(nrow, 9, 'Balance', header_row_style)

        sheet.set_row(nrow, 26)
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 0.6)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 30)
        sheet.set_column('F:F', 0.6)
        sheet.set_column('G:G', 14)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 16)
        sheet.set_column('J:J', 17)

        initial_amount = 0
        for balance in initial_data:
            row = row + 1
            initial_amount = balance['balance']
            sheet.merge_range('A{}:B{}'.format(row, row), ' ', text_format_invoice)
            sheet.write('C{}'.format(row), ' ', text_format_invoice)
            sheet.write('D{}'.format(row), ' ', text_format_invoice)
            sheet.write('E{}'.format(row), balance['description'], text_format)
            sheet.merge_range('F{}:G{}'.format(row, row), ' ', content_row_style)
            sheet.write('H{}'.format(row), ' ', content_row_style)
            sheet.write('I{}'.format(row), ' ', content_row_style)
            sheet.write('J{}'.format(row), balance['balance'], content_row_style)

        balance_amount, total_debit, total_credit = initial_amount, 0, 0
        for data in accounting_data:
            row = row + 1
            trn_date = datetime.strptime(data['date'], '%Y-%m-%d')
            trn_date = trn_date.strftime('%d-%b-%Y')

            sheet.merge_range('A{}:B{}'.format(row, row), trn_date, text_format_invoice)
            sheet.write('C{}'.format(row), data['ref'], text_format_invoice)
            sheet.write('D{}'.format(row), data['code'], text_format_invoice)
            if data['description']:
                sheet.write('E{}'.format(row), data['description'], text_format)
            else:
                sheet.write('E{}'.format(row), data['ref'], text_format)

            sheet.merge_range('F{}:G{}'.format(row, row), initial_amount, content_row_style)
            sheet.write('H{}'.format(row), data['debit'], content_row_style)
            sheet.write('I{}'.format(row), data['credit'], content_row_style)

            if data['debit'] > 0:
                balance_amount = data['debit'] + initial_amount
                sheet.write('J{}'.format(row), balance_amount, content_row_style)
                initial_amount = balance_amount

            elif data['credit'] > 0:
                balance_amount = initial_amount - data['credit']
                sheet.write('J{}'.format(row), balance_amount, content_row_style)
                initial_amount = balance_amount

            total_debit += data['debit']
            total_credit += data['credit']
            # total_balance += due_amount

        sheet.write(row, 7, total_debit, totals_style)
        sheet.write(row, 8, total_credit, totals_style)
        sheet.write(row, 9, balance_amount, totals_style)
        row += 1
