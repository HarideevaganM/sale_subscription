from odoo import api, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class BbisAcctSalesReport(models.AbstractModel):
    _name = 'report.bbis_reports.sales_report'
    _description = 'BBIS Sales Report'

    def _get_sales_list(self, data, account_type, is_rb=False):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        self.env.cr.execute(
            """
            select
            aml.date as date,
            ag.name as group_name,
            pt.name as product_name,
            pc.name as product_category,
            pr.name as partner,
            aml.quantity as quantity,
            (CASE
            WHEN aml.balance > 0
            THEN aml.balance * -1
            ELSE ABS(aml.balance)
            END
            ) as balance
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN product_category pc on aml.product_category = pc.id
            LEFT JOIN product_product pp on aml.product_id = pp.id
            LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
            LEFT JOIN res_partner pr on aml.partner_id = pr.id
            WHERE aml.user_type_id in %s AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            ORDER BY date ASC, group_name ASC
            """ % (account_type, data['start_date'], data['end_date'], move_state))

        res = self.env.cr.dictfetchall()
        return res

    def _get_accounting_data(self, data, account_type, is_rb=False):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        self.env.cr.execute(
            """
            select
            ag.name as group_name,
            --aml.product_category as category_id,
            SUM(CASE
                WHEN ai.type in ('out_refund','in_refund')
                    THEN aml.quantity * -1
                    ELSE ABS(aml.quantity)
                END
            ) as quantity,
            pc.name as category_name,
            (CASE
                WHEN SUM(aml.balance) > 0
                    THEN SUM(aml.balance) * -1
                    ELSE ABS(SUM(aml.balance))
                END
            ) as balance,
            SUM(aml.credit) as credit,
            SUM(aml.debit) as debit,
            (aml_tax.total_tax * SUM(aml.credit)) as tax,
            date_trunc('month', aml.date) as year_month
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_invoice ai on aml.invoice_id = ai.id
            LEFT JOIN product_category pc on aml.product_category = pc.id
            LEFT JOIN (
                SELECT 
                (act.amount / 100) as total_tax,
                amlt_rel.account_move_line_id as aml_id
                FROM account_tax act
                INNER JOIN account_move_line_account_tax_rel amlt_rel on amlt_rel.account_tax_id = act.id
            ) as aml_tax ON aml_tax.aml_id = aml.id
            WHERE aml.user_type_id in %s AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            GROUP BY group_name, category_name, year_month, aml_tax.total_tax,ai.type
            ORDER BY group_name DESC, year_month ASC
            """ % (account_type, data['start_date'], data['end_date'], move_state))

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
                category_name = f["category_name"] or 'Undefined'
                group_name = f["group_name"] or 'Undefined'

                if group_name not in record:
                    record[group_name] = {}

                if category_name not in record[group_name]:
                    record[group_name][category_name] = {}

                if m not in record[group_name][category_name]:
                    record[group_name][category_name][m] = {'balance': 0.00, 'quantity': 0, 'tax': 0}

                if m == month:
                    record[group_name][category_name][m]['balance'] += f['balance'] if f['balance'] else 0
                    record[group_name][category_name][m]['quantity'] += f['quantity'] if f['quantity'] else 0
                    record[group_name][category_name][m]['tax'] += f['tax'] if f['tax'] else 0

                if group_name not in total:
                    total[group_name] = {}

                if m not in total[group_name]:
                    total[group_name][m] = {'balance': 0.00, 'quantity': 0, 'tax': 0}

                if m not in total['account']:
                    total['account'][m] = {'balance': 0.00, 'quantity': 0, 'tax': 0}

                if m == month:
                    total[group_name][m]['balance'] += f['balance'] if f['balance'] else 0
                    total[group_name][m]['quantity'] += f['quantity'] if f['quantity'] else 0
                    total[group_name][m]['tax'] += f['tax'] if f['tax'] else 0

                    total['account'][m]['balance'] += f['balance'] if f['balance'] else 0
                    total['account'][m]['quantity'] += f['quantity'] if f['quantity'] else 0
                    total['account'][m]['tax'] += f['tax'] if f['tax'] else 0

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
        #     'end_date': '2021-06-30',
        #     'date_filter': 'this_year',
        #     'target_move': 'posted',
        #     'include_sales_qty': False,
        #     'include_tax': True,
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
            'include_sales_qty': form_data['include_sales_qty'],
            'include_tax': form_data['include_tax'],
            'data': self.get_accounting_data(final_data, '(14)'),
            # 'sale_list': self.get_sales_list(final_data, '(14)'),
        }
