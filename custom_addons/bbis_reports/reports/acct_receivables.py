from odoo import api, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class BbisAcctReceivablesReport(models.AbstractModel):
    _name = 'report.bbis_reports.receivables_report'
    _description = 'BBIS Receivables Report'

    def _get_single_total_bal(self, num=[], amount=0, balance={}):
        if num not in balance:
            balance[num] = [amount]
        else:
            balance[num].append(amount)

        return balance

    # Getting the initial balance query. Commented the year select and remove the year from grouping for single line of data.
    def _get_initial_balance(self, data):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        self.env.cr.execute(
            """
            select
            pr.name as partner,
            SUM(aml.credit) as credit,
            SUM(aml.debit) as debit,
            SUM(aml.balance) as balance
            --date_trunc('year', aml.date) as year_month
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN res_partner pr on aml.partner_id = pr.id
            WHERE ac.internal_type = 'receivable' AND aml.date < '%s'
            AND am.state in %s
            GROUP BY partner
            ORDER BY partner ASC
            """ % (data['start_date'], move_state))

        accounting_data = self.env.cr.dictfetchall()

        record = {}

        # for m in range(start_range, end_range):
        for f in accounting_data:
            partner = f["partner"] or 'Undefined'

            if partner not in record:
                record[partner] = {'balance': f['balance'] or 0}

        return record

    def _get_accounting_data(self, data):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        self.env.cr.execute(
            """
            select
            pr.name as partner,
            SUM(aml.credit) as credit,
            SUM(aml.debit) as debit,
            SUM(aml.balance) as balance,
            date_trunc('month', aml.date) as year_month
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN res_partner pr on aml.partner_id = pr.id
            WHERE ac.internal_type = 'receivable' AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            GROUP BY partner, year_month
            ORDER BY partner ASC, year_month ASC
            """ % (data['start_date'], data['end_date'], move_state))

        accounting_data = self.env.cr.dictfetchall()

        start_range = 0
        end_range = data['date_range'] + 1

        if data['date'] == 'custom':
            start_range = data['start_date'].month
            end_range = data['end_date'].month + 1

        record = {}
        total = {
            'account': {}
        }

        for m in range(start_range, end_range):
            for f in accounting_data:
                month = f["year_month"].month
                partner = f["partner"] or 'Undefined'

                if partner not in record:
                    record[partner] = {}

                if m not in record[partner]:
                    record[partner][m] = {'balance': 0.00, 'credit': 0, 'debit': 0}

                if m == month:
                    record[partner][m]['balance'] = f['balance'] or 0
                    record[partner][m]['credit'] = f['credit'] or 0
                    record[partner][m]['debit'] = f['debit'] or 0

                if partner not in total:
                    total[partner] = {}

                if m not in total[partner]:
                    total[partner][m] = {'balance': 0.00, 'credit': 0, 'debit': 0}

                if m not in total['account']:
                    total['account'][m] = {'balance': 0.00, 'credit': 0, 'debit': 0}

                if m == month:
                    total[partner][m]['balance'] = total[partner][m]['balance'] + record[partner][m]['balance']
                    total[partner][m]['credit'] = total[partner][m]['credit'] + record[partner][m]['credit']
                    total[partner][m]['debit'] = total[partner][m]['debit'] + record[partner][m]['debit']

                    total['account'][m]['balance'] = total['account'][m]['balance'] + record[partner][m]['balance']
                    total['account'][m]['credit'] = total['account'][m]['credit'] + record[partner][m]['credit']
                    total['account'][m]['debit'] = total['account'][m]['debit'] + record[partner][m]['debit']

        final_data = {
            'list': record,
            'keys': sorted(list(record.keys())),
            'total': total,
            'start_range': start_range,
            'end_range': end_range,
        }

        return final_data

    @api.model
    def _get_report_values(self, docids, data=None):

        form_data = data['form']

        # form_data = {
        #     'start_date': '2021-01-01',
        #     'end_date': '2021-12-31',
        #     'date_filter': 'last_year',
        #     'target_move': 'posted',
        #     'include_cr': True,
        #     'include_db': True,
        # }

        date_now_str = datetime.now().strftime('%d/%m/%Y')
        date_now = datetime.strptime(date_now_str, '%d/%m/%Y')

        if form_data['date_filter'] == 'this_year':
            this_year = datetime.now()
            start_date = datetime.strftime(this_year, '%Y-01-01')
            end_date = datetime.strftime(this_year, '%Y-12-31')
            date_range = date_now.month
        elif form_data['date_filter'] == 'last_year':
            last_year = datetime.now() - relativedelta(years=1)
            start_date = datetime.strftime(last_year, '%Y-01-01')
            end_date = datetime.strftime(last_year, '%Y-12-31')
            date_range = 12
        else:
            start_date = datetime.strptime(form_data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(form_data['end_date'], '%Y-%m-%d')
            date_range = (end_date.month - start_date.month) + 1

            if start_date.year != end_date.year:
                raise ValidationError(_('Please select dates in the same year only.'))

        final_data = {
            'start_date': start_date,
            'end_date': end_date,
            'date': form_data['date_filter'],
            'date_range': date_range,
            'move_state': form_data['target_move'],
        }

        # check if filter date is custom and convert dates to proper date format
        if form_data['date_filter'] != 'custom':
            start_date_tmp = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_tmp = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date_tmp = start_date
            end_date_tmp = end_date

        # data previous year
        prev_year_param = {
            'start_date': start_date_tmp,
            'end_date': end_date_tmp - relativedelta(years=1),
            'date': form_data['date_filter'],
            'date_range': date_range,
            'move_state': form_data['target_move'],
        }

        year_date = start_date
        if form_data['date_filter'] != 'custom':
            year_date = datetime.strptime(start_date, '%Y-%m-%d')

        return {
            'doc_model': 'account.move.line',
            'date_range': date_range,
            'move_state': form_data['target_move'],
            'date': form_data['date_filter'],
            'start_date': start_date,
            'end_date': end_date,
            'year': year_date,
            'include_cr': form_data['include_cr'],
            'include_db': form_data['include_db'],
            'data': self.get_accounting_data(final_data),
            'initial_balance': self.get_initial_balance(prev_year_param),
            'get_single_total_bal': self.get_single_total_bal
        }