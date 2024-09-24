from odoo import api, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class BbisAcctFinancialPerformanceComp(models.AbstractModel):
    _name = 'report.bbis_reports.financial_performance_comp'
    _description = 'BBIS Print Comparative Financial Performance'

    def _get_income_difference(self, current_data, prev_data, cur_year, prev_year):
        result = {}
        for f in current_data[cur_year]:
            if f not in result:
                result[f] = {'aed': 0, 'percentile': 0}

            cy = current_data[cur_year][f]
            py = prev_data[prev_year][f]

            result[f]['aed'] = cy - py

            if py != 0:
                result[f]['percentile'] = (result[f]['aed'] / py) * 100

        return result

    def _get_sched_difference(self, current_data, prev_data, cur_year, prev_year):
        result = {}

        for group, g_value in current_data[cur_year]['list'].items():
            if group not in result:
                result[group] = {}
                for account, a_value in g_value.items():
                    if account not in result[group]:
                        result[group][account] = {x: {'aed': y, 'percentile': 0.00} for x, y in a_value.items()}

        for group, g_value in prev_data[prev_year]['list'].items():
            if group not in result:
                result[group] = {}
                for account, a_value in g_value.items():
                    if account not in result[group]:
                        result[group][account] = {x: {'aed': y, 'percentile': 0.00} for x, y in a_value.items()}
            else:
                for account, a_value in g_value.items():
                    if account in result[group]:
                        for cat, cat_value in a_value.items():
                            if cat in result[group][account].keys():
                                result[group][account][cat]['aed'] = result[group][account][cat]['aed'] - cat_value

                                if cat_value != 0:
                                    result[group][account][cat]['percentile'] = (result[group][account][cat]['aed'] / cat_value) * 100
                    else:
                        result[group][account] = {x: {'aed': y, 'percentile': 0.00} for x, y in a_value.items()}
        return result

    def _get_schedules(self, data, account_type, is_rb=False):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        self.env.cr.execute(
            """
            select
            ag.name as group_name,
            aml.product_category as category_id,
            MAX(pc.name) as category_name,
            ac.name as account_name,
            (CASE
                WHEN SUM(aml.balance) > 0
                    THEN SUM(aml.balance) * -1
                    ELSE ABS(SUM(aml.balance))
                END
            ) as balance,
            max(aml.date) as date_month,
            date_trunc('year', aml.date) as date_year
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN product_category pc on aml.product_category = pc.id
            WHERE aml.user_type_id in %s AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            GROUP BY group_name, category_id, account_name, date_year
            ORDER BY group_name ASC, date_year ASC, category_name ASC
            """ % (account_type, data['start_date'], data['end_date'], move_state))

        schedules = self.env.cr.dictfetchall()

        start_range = 0
        end_range = data['date_range'] + 1

        if data['date'] == 'custom':
            start_range = data['start_date'].month
            end_range = data['end_date'].month + 1

        cur_year = data['cur_year']

        record = {}
        total = {'amount': 0}

        for m in range(start_range, end_range):
            for f in schedules:
                month = datetime.strptime(f["date_month"], '%Y-%m-%d').month
                account_name = f["account_name"] or 'Undefined'
                category_name = f["category_name"] or 'Undefined'
                group_name = f["group_name"] or 'Undefined'

                if group_name not in record:
                    record[group_name] = {}

                if account_name not in record[group_name]:
                    record[group_name][account_name] = {}

                if category_name not in record[group_name][account_name]:
                    record[group_name][account_name][category_name] = 0

                if m == month:
                    record[group_name][account_name][category_name] = f['balance']

                if group_name not in total:
                    total[group_name] = 0

                if m == month:
                    total[group_name] = total[group_name] + record[group_name][account_name][category_name]
                    total['amount'] = total['amount'] + record[group_name][account_name][category_name]

        final_data = {
            cur_year: {
                'list': record,
                'keys': sorted(list(record.keys())),
                'total': total
            }
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
            max(aml.date) as date_month,
            date_trunc('year', aml.date) as date_year
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            WHERE aml.user_type_id in (14,13,17,16,15) AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            GROUP BY aml.user_type_id, date_year
            ORDER BY aml.user_type_id ASC, account_name ASC, date_year ASC
            """ % (data['start_date'], data['end_date'], move_state))

        financial_performance = self.env.cr.dictfetchall()

        cur_year = data['cur_year']

        sales = 0
        cost_of_sales = 0
        gross = 0
        expenses = 0
        depreciation = 0
        net_profit = 0
        other_income = 0
        total_income = 0

        start_range = 0
        end_range = data['date_range'] + 1

        if data['date'] == 'custom':
            start_range = data['start_date'].month
            end_range = data['end_date'].month + 1

        for m in range(start_range, end_range):
            for f in financial_performance:
                month = datetime.strptime(f["date_month"], '%Y-%m-%d').month
                account_type = f["account_type"] or 'Undefined'

                if m == month and account_type == 14:
                    sales = f['balance']
                elif m == month and account_type == 17:
                    cost_of_sales = f['balance']
                elif m == month and account_type == 16:
                    expenses = f['balance']
                elif m == month and account_type == 15:
                    depreciation = f['balance']
                elif m == month and account_type == 13:
                    other_income = f['balance']
                else:
                    continue

            gross = sales + cost_of_sales
            net_profit = gross + (expenses + depreciation)
            total_income = net_profit + other_income

        data = {
            'sales': sales,
            'cost_of_sales': cost_of_sales,
            'gross': gross,
            'expenses': expenses,
            'depreciation': depreciation,
            'net_profit': net_profit,
            'other_income': other_income,
            'total_income': total_income,
        }

        final_data = {
            cur_year: data,
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
        # }

        date_now_str = datetime.now().strftime('%d/%m/%Y')
        date_now = datetime.strptime(date_now_str, '%d/%m/%Y')

        if form_data['date_filter'] == 'this_year':
            this_year = datetime.now()
            start_date = datetime.strftime(this_year, '%Y-01-01')
            end_date = datetime.strftime(this_year, '%Y-12-31')
            date_range = date_now.month
            this_month = this_year.month
        elif form_data['date_filter'] == 'last_year':
            last_year = datetime.now() - relativedelta(years=1)
            start_date = datetime.strftime(last_year, '%Y-01-01')
            end_date = datetime.strftime(last_year, '%Y-12-31')
            date_range = 12
            this_month = 12
        else:
            start_date = datetime.strptime(form_data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(form_data['end_date'], '%Y-%m-%d')
            date_range = (end_date.month - start_date.month) + 1
            this_month = end_date.month

            if start_date.year != end_date.year:
                raise ValidationError(_('Please select dates in the same year only.'))

        current_year = start_date
        if form_data['date_filter'] != 'custom':
            current_year = datetime.strptime(start_date, '%Y-%m-%d')

        # get current year paramaeters
        cur_year_param = {
            'start_date': start_date,
            'end_date': end_date,
            'date': form_data['date_filter'],
            'date_range': date_range,
            'move_state': form_data['target_move'],
            'cur_year': current_year.year,
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
            'start_date': start_date_tmp - relativedelta(years=1),
            'end_date': end_date_tmp - relativedelta(years=1),
            'date': form_data['date_filter'],
            'date_range': date_range,
            'move_state': form_data['target_move'],
            'cur_year': int(current_year.year) - 1,
        }

        # get current month parameters
        cur_month_param = {
            'start_date': end_date_tmp.replace(day=1),
            'end_date': end_date_tmp,
            'date': form_data['date_filter'],
            'date_range': date_range,
            'move_state': form_data['target_move'],
            'cur_year': current_year.year,
        }

        # get previous month parameters
        prev_month_param = {
            'start_date': (end_date_tmp - relativedelta(years=1)).replace(day=1),
            'end_date': end_date_tmp - relativedelta(years=1),
            'date': form_data['date_filter'],
            'date_range': date_range,
            'move_state': form_data['target_move'],
            'cur_year': int(current_year.year) - 1,
        }

        cur_year_data = self.get_financial_performance(cur_year_param)
        prev_year_data = self.get_financial_performance(prev_year_param)
        cur_month_data = self.get_financial_performance(cur_month_param)
        prev_month_data = self.get_financial_performance(prev_month_param)
        cur_year = current_year.year
        prev_year = int(current_year.year) - 1

        # calculate difference in AED and Percentile in Month
        month_diff = self.get_income_difference(cur_month_data, prev_month_data, cur_year, prev_year)

        # calculate difference in AED and Percentile in Year
        year_diff = self.get_income_difference(cur_year_data, prev_year_data, cur_year, prev_year)

        cur_year_sales = self.get_schedules(cur_year_param, '(14)')
        prev_year_sales = self.get_schedules(prev_year_param, '(14)')
        cur_month_sales = self.get_schedules(cur_month_param, '(14)')
        prev_month_sales = self.get_schedules(prev_month_param, '(14)')

        cur_year_cost_sales = self.get_schedules(cur_year_param, '(17)', True)
        prev_year_cost_sales = self.get_schedules(prev_year_param, '(17)', True)
        cur_month_cost_sales = self.get_schedules(cur_month_param, '(17)', True)
        prev_month_cost_sales = self.get_schedules(prev_month_param, '(17)', True)

        cur_year_expenses = self.get_schedules(cur_year_param, '(16)')
        prev_year_expenses = self.get_schedules(prev_year_param, '(16)')
        cur_month_expenses = self.get_schedules(cur_month_param, '(16)')
        prev_month_expenses = self.get_schedules(prev_month_param, '(16)')

        # calculate difference in AED and Percentile in Year
        year_diff_sales = self.get_sched_difference(cur_year_sales, prev_year_sales, cur_year, prev_year)
        year_diff_cost_sales = self.get_sched_difference(cur_year_cost_sales, prev_year_cost_sales, cur_year, prev_year)
        year_diff_expenses = self.get_sched_difference(cur_year_expenses, prev_year_expenses, cur_year, prev_year)

        return {
            'doc_model': 'account.move.line',
            'data': cur_year_data,
            'data_prev': prev_year_data,
            'cur_month_data': cur_month_data,
            'prev_month_data': prev_month_data,
            'month_diff': month_diff,
            'year_diff': year_diff,
            'date_range': date_range,
            'move_state': form_data['target_move'],
            'date': form_data['date_filter'],
            'start_date': start_date,
            'end_date': end_date,
            'cur_year': cur_year,
            'prev_year': prev_year,
            'cur_month': this_month,
            'cur_year_sales': cur_year_sales,
            'prev_year_sales': prev_year_sales,
            'cur_month_sales': cur_month_sales,
            'prev_month_sales': prev_month_sales,
            'year_diff_sales': year_diff_sales,
            'cur_year_cost_sales': cur_year_cost_sales,
            'prev_year_cost_sales': prev_year_cost_sales,
            'year_diff_cost_sales': year_diff_cost_sales,
            'cur_month_cost_sales': cur_month_cost_sales,
            'prev_month_cost_sales': prev_month_cost_sales,
            'cur_year_expenses': cur_year_expenses,
            'prev_year_expenses': prev_year_expenses,
            'cur_month_expenses': cur_month_expenses,
            'prev_month_expenses': prev_month_expenses,
            'year_diff_expenses': year_diff_expenses,
        }
