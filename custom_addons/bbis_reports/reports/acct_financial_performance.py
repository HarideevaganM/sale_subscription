from odoo import api, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class BbisAcctFinancialPerformance(models.AbstractModel):
    _name = 'report.bbis_reports.financial_performance'
    _description = 'BBIS Print Financial Performance'

    def _get_total_account(self, num=None, amount=0, data=None):
        if num not in data:
            data[num] = [amount]
        else:
            data[num].append(amount)

        return data

    def _get_schedules(self, data, account_type, is_rb=False):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        self.env.cr.execute(
            """
            select
            ag.name as group_name,
            ac.code as account_code,
            ac.name as account_name,
            pc.name as category_name,
            (CASE
                WHEN SUM(aml.balance) > 0
                    THEN SUM(aml.balance) * -1
                    ELSE ABS(SUM(aml.balance))
                END
            ) as balance,
            date_trunc('month', aml.date) as year_month
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN product_category pc on aml.product_category = pc.id
            WHERE aml.user_type_id in %s AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            GROUP BY group_name, account_name, account_code, category_name, year_month
            ORDER BY group_name DESC, year_month ASC
            """ % (account_type, data['start_date'], data['end_date'], move_state))

        schedules = self.env.cr.dictfetchall()

        start_range = 0
        end_range = data['date_range'] + 1

        if data['date'] == 'custom':
            start_range = data['start_date'].month
            end_range = data['end_date'].month + 1

        record = {}
        total = {
            'total_sales': {}
        }

        for m in range(start_range, end_range):
            for f in schedules:
                month = f["year_month"].month
                account_name = f["account_name"] or 'Undefined'
                category_name = f["category_name"] or 'Undefined'
                group_name = f["group_name"] or 'Undefined'

                if group_name not in record:
                    record[group_name] = {}

                if account_name not in record[group_name]:
                    record[group_name][account_name] = {}

                # new
                if category_name not in record[group_name][account_name]:
                    record[group_name][account_name][category_name] = {}

                if m not in record[group_name][account_name][category_name]:
                    record[group_name][account_name][category_name][m] = 0.00

                if m == month:
                    record[group_name][account_name][category_name][m] = f['balance']

                if group_name not in total:
                    total[group_name] = {}

                if m not in total[group_name]:
                    total[group_name][m] = 0

                if m not in total['total_sales']:
                    total['total_sales'][m] = 0

                if m == month:
                    total[group_name][m] = total[group_name][m] + record[group_name][account_name][category_name][m]
                    total['total_sales'][m] = total['total_sales'][m] + record[group_name][account_name][category_name][m]

        final_data = {
            'list': record,
            'keys': sorted(list(record.keys())),
            'total': total
        }

        return final_data

    def _get_financial_performance(self, data):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        self.env.cr.execute(
            """
            select
            aml.user_type_id as account_type,
            max(ag.name) as group_name,
            max(ac.name) as account_name,
            (CASE
                WHEN SUM(aml.balance) > 0
                    THEN SUM(aml.balance) * -1
                    ELSE ABS(SUM(aml.balance))
                END
            ) as balance,
            date_trunc('month', aml.date) as year_month
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            WHERE aml.user_type_id in (14,13,17,16,15) AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            GROUP BY aml.user_type_id, year_month
            ORDER BY aml.user_type_id ASC, account_name ASC, year_month ASC
            """ % (data['start_date'], data['end_date'], move_state))

        financial_performance = self.env.cr.dictfetchall()

        sales = {}
        cost_of_sales = {}
        gross = {}
        expenses = {}
        depreciation = {}
        net_profit = {}
        other_income = {}
        total_income = {}

        start_range = 0
        end_range = data['date_range'] + 1

        if data['date'] == 'custom':
            start_range = data['start_date'].month
            end_range = data['end_date'].month + 1

        ctr = 0
        for m in range(start_range, end_range):
            ctr = ctr + 1
            s_bal, cs_bal, exp_bal, dep_bal, oi_bal = 0, 0, 0, 0, 0

            for f in financial_performance:
                month = f["year_month"].month
                account_type = f["account_type"]

                if m == month and account_type == 14:
                    s_bal = f['balance']
                elif m == month and account_type == 17:
                    cs_bal = f['balance']
                elif m == month and account_type == 16:
                    exp_bal = f['balance']
                elif m == month and account_type == 15:
                    dep_bal = f['balance']
                elif m == month and account_type == 13:
                    oi_bal = f['balance']
                else:
                    continue
            sales[m] = s_bal
            cost_of_sales[m] = cs_bal
            gross[m] = sales[m] + cost_of_sales[m]
            expenses[m] = exp_bal
            depreciation[m] = dep_bal
            net_profit[m] = gross[m] + (expenses[m] + depreciation[m])
            other_income[m] = oi_bal
            total_income[m] = net_profit[m] + other_income[m]

        data = {
            'sales': sales,
            'cost_of_sales': cost_of_sales,
            'gross': gross,
            'expenses': expenses,
            'depreciation': depreciation,
            'net_profit': net_profit,
            'other_income': other_income,
            'total_income': total_income,
            'start_range': start_range,
            'end_range': end_range,
        }

        return data

    def _get_data(self, data):
        return self.get_financial_performance(data)

    @api.model
    def _get_report_values(self, docids, data=None):

        form_data = data['form']

        # form_data = {
        #     'start_date': '2021-01-01',
        #     'end_date': '2021-07-30',
        #     'date_filter': 'this_year',
        #     'target_move': 'posted',
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

        reports_data = self.get_data(final_data)

        year_date = start_date
        if form_data['date_filter'] != 'custom':
            year_date = datetime.strptime(start_date, '%Y-%m-%d')

        return {
            'doc_model': 'account.move.line',
            'data': reports_data,
            'date_range': date_range,
            'move_state': form_data['target_move'],
            'date': form_data['date_filter'],
            'start_date': start_date,
            'end_date': end_date,
            'year': year_date,
            'sched_sales': self.get_schedules(final_data, '(14)'),
            'sched_cost_sales': self.get_schedules(final_data, '(17)', True),
            'sched_op_expense': self.get_schedules(final_data, '(16)'),
            'get_total_account': self.get_total_account,
        }
