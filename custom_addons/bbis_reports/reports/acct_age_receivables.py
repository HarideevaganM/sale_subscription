from odoo import api, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class BbisAcctAgeReceivablesReport(models.AbstractModel):
    _name = 'report.bbis_reports.age_receivables_report'
    _description = 'BBIS Age Receivables Report'

    def _get_accounting_data(self, data):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        d = data['start_date']
        self.env.cr.execute(
            """
            select * from
            (select arr.partner, SUM(arr.pending_amount) as balance, arr.age
            from (select ar.partner,
            CASE
              WHEN ar.balance > 0
              THEN ar.balance - ar.transaction_credit
              ELSE ar.balance + ar.transaction_credit
            END as pending_amount,
            ar.age
            from (select
            pr.name as partner,
            aml.balance as balance,
            CASE
              WHEN aml.credit > 0 
              THEN (select coalesce(SUM(amount),0) from account_partial_reconcile where credit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
              WHEN aml.debit > 0 
              THEN (select coalesce(SUM(amount),0) from account_partial_reconcile where debit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
            END as transaction_credit,
            CASE
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 30 THEN '<30'
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 60 THEN '30-60'
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 90 THEN '60-90'
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 120 THEN '90-120'
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 360 THEN '120-360'
            ELSE '>360'
            END as age
            FROM account_move_line aml
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN res_partner pr on aml.partner_id = pr.id
            WHERE ac.internal_type = 'receivable'
            AND aml.date <= '%s'
            AND am.state in %s) as ar) as arr
            GROUP by arr.partner, arr.age) as age_receivables
            WHERE age_receivables.balance != 0
            """ % (d, d, d, d, d, d, d, d, move_state,))

        accounting_data = self.env.cr.dictfetchall()

        record = {}
        total = {
            'account': {}
        }

        # for m in range(start_range, end_range):
        for f in accounting_data:
            age = f["age"]
            partner = f["partner"] or 'Undefined'
            balance = f["balance"] or 0.00

            if partner not in record:
                record[partner] = {}

            if age not in record[partner]:
                record[partner][age] = {'balance': balance}

            if partner not in total:
                total[partner] = {'balance': 0}

            if age not in total['account']:
                total['account'][age] = {'balance': 0}

            total['account'][age]['balance'] = total['account'][age]['balance'] + record[partner][age]['balance']
            total[partner]['balance'] = total[partner]['balance'] + record[partner][age]['balance']

        final_data = {
            'list': record,
            'keys': sorted(list(record.keys())),
            'total': total,
        }

        return final_data

    @api.model
    def _get_report_values(self, docids, data=None):

        form_data = data['form']

        # form_data = {
        #     'aged_receivable_date': '2021-01-01',
        #     'target_move': 'posted',
        #     'include_cr': False,
        #     'include_db': False,
        # }

        start_date = datetime.strptime(form_data['aged_receivable_date'], '%Y-%m-%d')

        final_data = {
            'start_date': form_data['aged_receivable_date'],
            'move_state': form_data['target_move'],
        }

        return {
            'doc_model': 'account.move.line',
            'move_state': form_data['target_move'],
            'start_date': start_date,
            'include_cr': form_data['include_cr'],
            'include_db': form_data['include_db'],
            'data': self.get_accounting_data(final_data),
            'cols': ['<30', '30-60', '60-90', '90-120', '120-360', '>360'],
        }


# Added on 31-03-2013. Aged Receivable Excel Report.
class BBISAgedReceivablesReportExcel(models.AbstractModel):
    _name = 'report.bbis_reports.aged_receivables_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Aged Receivables Report Excel'

    def generate_xlsx_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet('PO Report')
        self.print_header(data, workbook, sheet)
        self.get_account_data(data, workbook, sheet)

    # Excel report Name and header columns adding.
    def print_header(self, data, workbook, sheet):
        format_main_head = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 15, 'align': 'center', 'bold': True,
             'font_color': 'blue'})
        format_header = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 10, 'align': 'center', 'color': 'white',
             'text_wrap': True, 'bg_color': '#ed7d31', 'valign': 'vcenter'})
        subsequent_format_header = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 10, 'align': 'center', 'color': 'white',
             'text_wrap': True, 'bg_color': '#00b050', 'valign': 'vcenter'})

        # Supplier PO Report
        sheet.merge_range('A1:L1', 'AR  AGEING SCHEDULE REPORT', format_main_head)
        sheet.write('A2', 'SN', format_header)
        sheet.write('B2', 'Company Name', format_header)
        sheet.write('C2', '30 Days', format_header)
        sheet.write('D2', '30 to 60 Days', format_header)
        sheet.write('E2', '60 to 90 Days', format_header)
        sheet.write('F2', '90 to 120 Days', format_header)
        sheet.write('G2', '120 to 360 Days', format_header)
        sheet.write('H2', '>360 Days', format_header)
        sheet.write('I2', 'Total Balance', format_header)
        sheet.write('J2', 'Subsequent Payment', subsequent_format_header)
        sheet.write('K2', 'Sales Person', format_header)
        sheet.write('L2', 'Accounting Person', format_header)

    def _get_account_data(self, data, workbook, sheet):
        partner_name = ''
        partner_balance = 0
        age_less_30 = 0
        age_less_60 = 0
        age_less_90 = 0
        age_less_120 = 0
        age_less_360 = 0
        age_above_1yr = 0
        total_subsequent_payment = 0

        format_normal = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 10, 'align': 'right', 'valign': 'vcenter'})
        format_text = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 10, 'align': 'left', 'valign': 'vcenter',
             'text_wrap': True})
        totals_style = workbook.add_format(
            {'bold': True, 'align': 'center', 'bg_color': '#ed7d31', 'border': True, 'valign': 'vcenter',
             'font_size': 10, 'num_format': '#,##0.00', 'color': 'white'})
        content_row_style = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'border': True})
        sub_content_row_style = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'border': True
                                                     , 'bg_color': '#00b050'})

        form_data = data['form']
        move_state = "('posted')" if form_data['target_move'] == 'posted' else "('posted', 'draft')"
        start_date = form_data['aged_receivable_date']
        subsequent_pay_date = form_data['subsequent_pay_date']

        self.env.cr.execute(
            """
            select * from
            (select arr.partner, arr.sales_person_id, arr.accounting_person_id, SUM(arr.pending_amount) as balance, arr.age
            from (select ar.partner, ar.sales_person_id, ar.accounting_person_id,
            CASE
              WHEN ar.balance > 0
              THEN ar.balance - ar.transaction_credit
              ELSE ar.balance + ar.transaction_credit
            END as pending_amount,
            ar.age
            from (select
            pr.name as partner,users.id as sales_person_id, users1.id as accounting_person_id,
            aml.balance as balance,
            CASE
              WHEN aml.credit > 0 
              THEN (select coalesce(SUM(amount),0) from account_partial_reconcile where credit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
              WHEN aml.debit > 0 
              THEN (select coalesce(SUM(amount),0) from account_partial_reconcile where debit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
            END as transaction_credit,
            CASE
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 30 THEN '<30'
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 60 THEN '30-60'
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 90 THEN '60-90'
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 120 THEN '90-120'
            WHEN extract(day from '%s' - aml.date_maturity::timestamp) <= 360 THEN '120-360'
            ELSE '>360'
            END as age
            FROM account_move_line aml
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN res_partner pr on aml.partner_id = pr.id
            LEFT JOIN res_users users on users.id = pr.user_id
            LEFT JOIN res_users users1 on users1.id = pr.accounting_person
            WHERE ac.internal_type = 'receivable'
            AND aml.date <= '%s'
            AND am.state in %s) as ar) as arr
            GROUP by arr.partner, arr.sales_person_id, arr.accounting_person_id, arr.age
            Order by arr.partner) as age_receivables
            WHERE age_receivables.balance != 0
            """ % (start_date, start_date, start_date, start_date, start_date, start_date, start_date,
                   start_date, move_state,))

        receivables_data = self.env.cr.dictfetchall()

        self.env.cr.execute(
            """select
            pr.name as partner,
            SUM(aml.credit) as credit
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_journal aj on aml.journal_id = aj.id
            LEFT JOIN res_partner pr on aml.partner_id = pr.id
            WHERE ac.code = '132200' AND aj.type IN ('cash','bank') AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            GROUP BY partner
            ORDER BY partner ASC
        """ % (start_date, subsequent_pay_date, move_state,))
        payment_received = self.env.cr.dictfetchall()

        sheet.set_column('A:A', 6)
        sheet.set_column('B:B', 60)
        sheet.set_column('C:J', 13)
        sheet.set_column('K:L', 30)

        row = 1
        for receivables in receivables_data:
            if receivables['partner'] != partner_name:
                partner_balance = receivables['balance']
                row += 1
            else:
                row = row
                partner_balance += receivables['balance']

            sheet.write(row, 0, row - 1, format_normal)
            sheet.write(row, 1, receivables['partner'], format_text)
            if receivables['age'] == '<30':
                sheet.write(row, 2, receivables['balance'], content_row_style)
                age_less_30 = age_less_30 + receivables['balance']
            elif receivables['age'] == '30-60':
                sheet.write(row, 3, receivables['balance'], content_row_style)
                age_less_60 = age_less_60 + receivables['balance']
            elif receivables['age'] == '60-90':
                sheet.write(row, 4, receivables['balance'], content_row_style)
                age_less_90 = age_less_90 + receivables['balance']
            elif receivables['age'] == '90-120':
                sheet.write(row, 5, receivables['balance'], content_row_style)
                age_less_120 = age_less_120 + receivables['balance']
            elif receivables['age'] == '120-360':
                sheet.write(row, 6, receivables['balance'], content_row_style)
                age_less_360 = age_less_360 + receivables['balance']
            elif receivables['age'] == '>360':
                sheet.write(row, 7, receivables['balance'], content_row_style)
                age_above_1yr = age_above_1yr + receivables['balance']

            # For loop for find out the Subsequent payments of customer in the period.
            for receipts in payment_received:
                if receivables['partner'] == receipts['partner'] and receipts['partner'] != partner_name:
                    sheet.write(row, 9, receipts['credit'], sub_content_row_style)
                    total_subsequent_payment = total_subsequent_payment + receipts['credit']

            if receivables['sales_person_id']:
                sale_user = self.env['res.users'].search([('id', '=', receivables['sales_person_id'])])
                sheet.write(row, 10, sale_user.name, format_text)
            else:
                sheet.write(row, 10, '', format_text)
            if receivables['accounting_person_id']:
                account_user = self.env['res.users'].search([('id', '=', receivables['accounting_person_id'])])
                sheet.write(row, 11, account_user.name, format_text)
            else:
                sheet.write(row, 11, '', format_text)

            partner_name = receivables['partner']
            sheet.write(row, 8, partner_balance, content_row_style)

        age_balance = age_less_30 + age_less_60 + age_less_90 + age_less_120 + age_less_360 + age_above_1yr

        balance_row = row + 1
        sheet.merge_range('A{}:B{}'.format(balance_row + 1, balance_row + 1), 'Totals', totals_style)
        sheet.write(balance_row, 2, age_less_30, totals_style)
        sheet.write(balance_row, 3, age_less_60, totals_style)
        sheet.write(balance_row, 4, age_less_90, totals_style)
        sheet.write(balance_row, 5, age_less_120, totals_style)
        sheet.write(balance_row, 6, age_less_360, totals_style)
        sheet.write(balance_row, 7, age_above_1yr, totals_style)
        sheet.write(balance_row, 9, total_subsequent_payment, totals_style)
        sheet.write(balance_row, 10, '', totals_style)
        sheet.write(balance_row, 11, '', totals_style)
        # sheet.merge_range('J{}:K{}'.format(balance_row + 1, balance_row + 1), '', totals_style)

        sheet.write(balance_row, 8, age_balance, totals_style)

        # Adding border for blank rows.
        sheet.conditional_format(2, 0, row - 1, 11,
                                 {'type': 'blanks', 'format': content_row_style})
        # Adding border for blank rows.
        sheet.conditional_format(2, 9, row, 9,
                                 {'type': 'blanks', 'format': sub_content_row_style})
