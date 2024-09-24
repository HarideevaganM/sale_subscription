from odoo import api, models, _
from datetime import datetime


class BbisAcctAgeReceivablesReport(models.AbstractModel):
    _name = 'report.bbis_reports.age_payables_report'
    _description = 'BBIS Age Payables Report'

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
            aml.balance * - 1 as balance,
            CASE
              WHEN aml.credit > 0 
              THEN (select coalesce(SUM(amount),0) from account_partial_reconcile where credit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
              ELSE (select coalesce(SUM(amount),0) from account_partial_reconcile where debit_move_id = aml.id and DATE(max_date) <= '%s'::timestamp)
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
            WHERE ac.internal_type = 'payable'
            AND aml.date <= '%s'
            AND am.state in %s) as ar) as arr
            GROUP by arr.partner, arr.age) as age_payables
            WHERE age_payables.balance != 0
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
