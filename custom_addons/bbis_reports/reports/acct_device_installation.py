from odoo import api, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import calendar


class BbisAcctReceiptsReport(models.AbstractModel):
    _name = 'report.bbis_reports.device_installations'
    _description = 'BBIS Device Installations Report'

    def _get_partner_list(self, partners):
        partner_name = sorted(partners)
        return partner_name

    def _get_accounting_data(self, data):
        move_state = "('posted')" if data['move_state'] == 'posted' else "('posted', 'draft')"
        self.env.cr.execute(
            """
            select
            CONCAT(pt.name, ' [',pt.default_code, ']') as product_name,
            rp.name as partner_name,
            SUM(CASE
                WHEN ai.type in ('out_refund','in_refund')
                    THEN aml.quantity * -1
                    ELSE ABS(aml.quantity)
                END
            ) as quantity,
            date_trunc('month', aml.date) as year_month
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_invoice ai on aml.invoice_id = ai.id
            LEFT JOIN res_partner rp on aml.partner_id = rp.id
            LEFT JOIN product_category pc on aml.product_category = pc.id
            LEFT JOIN product_product pp on aml.product_id = pp.id
            LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
            WHERE pc.name = 'Unit Device' AND aml.user_type_id = 14 AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s
            GROUP BY product_name, partner_name, year_month, ai.type
            ORDER BY partner_name ASC
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
                product_name = f["product_name"] or 'Undefined'
                partner_name = f["partner_name"] or 'Undefined'

                if product_name not in record:
                    record[product_name] = {}

                if partner_name not in record[product_name]:
                    record[product_name][partner_name] = {}

                if m not in record[product_name][partner_name]:
                    record[product_name][partner_name][m] = {'quantity': []}

                if m == month:
                    record[product_name][partner_name][m]['quantity'].append(f['quantity'])

                if product_name not in total:
                    total[product_name] = {}

                if m not in total[product_name]:
                    total[product_name][m] = {'quantity': []}

                if m not in total['account']:
                    total['account'][m] = {'quantity': []}

                if m == month:
                    total[product_name][m]['quantity'].append(f['quantity'])
                    total['account'][m]['quantity'].append(f['quantity'])
        final_data = {
            'list': record,
            'keys': sorted(list(record.keys())),
            'total': total,
            'start_range': start_range,
            'end_range': end_range,
        }

        return final_data

    def _get_report_values(self, docids, data=None):

        form_data = data['form']

        # form_data = {
        #     'start_date': '2021-01-01',
        #     'end_date': '2021-04-30',
        #     'date_filter': 'custom',
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
            'data': self.get_accounting_data(final_data),
            'get_partner_list': self.get_partner_list,
        }


# Device Installation Excel Report
class BBISDeviceInstallationExcel(models.AbstractModel):
    _name = 'report.bbis_reports.device_installation_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Device Installation Excel Report'

    def generate_xlsx_report(self, workbook, data, partner):

        form_data = data['form']
        move_state = "('posted')" if form_data['target_move'] == 'posted' else "('posted', 'draft')"

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

        # if start_date.year != end_date.year:
        #     raise ValidationError(_('Please select dates in the same year only.'))

        self.env.cr.execute(
            """
            select
            CONCAT(pt.name, ' [',pt.default_code, ']') as product_name,
            rp.name as partner_name,
            SUM(CASE
                WHEN ai.type in ('out_refund','in_refund')
                    THEN aml.quantity * -1
                    ELSE ABS(aml.quantity)
                END
            ) as quantity,
            date_trunc('month', aml.date) as year_month
            FROM account_move_line aml
            LEFT JOIN account_group ag ON ag.id = aml.group_id
            LEFT JOIN account_account ac on ac.id = aml.account_id
            LEFT JOIN account_move am on aml.move_id = am.id
            LEFT JOIN account_invoice ai on aml.invoice_id = ai.id
            LEFT JOIN res_partner rp on aml.partner_id = rp.id
            LEFT JOIN product_category pc on aml.product_category = pc.id
            LEFT JOIN product_product pp on aml.product_id = pp.id
            LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
            WHERE pc.name = 'Unit Device' AND aml.user_type_id = 14 AND aml.date BETWEEN '%s' and '%s'
            AND am.state in %s  
            GROUP BY product_name, partner_name, year_month, ai.type
            ORDER BY product_name, partner_name ASC
            """ % (start_date, end_date, move_state))

        device_data = self.env.cr.dictfetchall()

        start_range = 1
        end_range = date_range + 1

        if form_data['date_filter'] == 'custom':
            start_date = datetime.strptime(form_data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(form_data['end_date'], '%Y-%m-%d')
            start_range = start_date.month
            end_range = end_date.month + 1

        # if data['date'] == 'custom':
        #     start_range = data['start_date'].month
        #     end_range = data['end_date'].month + 1

        record = {}
        total = {
            'account': {}
        }

        for m in range(start_range, end_range):
            for f in device_data:
                month = f["year_month"].month
                product_name = f["product_name"] or 'Undefined'
                partner_name = f["partner_name"] or 'Undefined'

                if product_name not in record:
                    record[product_name] = {}

                if partner_name not in record[product_name]:
                    record[product_name][partner_name] = {}

                if m not in record[product_name][partner_name]:
                    record[product_name][partner_name][m] = {'quantity': []}

                if m == month:
                    record[product_name][partner_name][m]['quantity'].append(f['quantity'])

                if product_name not in total:
                    total[product_name] = {}

                if m not in total[product_name]:
                    total[product_name][m] = {'quantity': []}

                if m not in total['account']:
                    total['account'][m] = {'quantity': []}

                if m == month:
                    total[product_name][m]['quantity'].append(f['quantity'])
                    total['account'][m]['quantity'].append(f['quantity'])

        final_data = {
            'list': record,
            'keys': sorted(list(record.keys())),
            'total': total,
            'start_range': start_range,
            'end_range': end_range,
        }

        row = 0
        column = 3
        sheet = workbook.add_worksheet('Device Installations')
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 12)
        sheet.set_column('C:C', 12)
        sheet.set_column('D:D', 12)

        title = workbook.add_format({'bold': True, 'align': 'left', 'font_size': 18})
        main_header_row_style = workbook.add_format(
            {'valign': 'vcenter', 'align': 'center', 'font_size': 10, 'bold': True,
             'bg_color': '#3bb44a', 'color': 'white', 'border': True})
        header_row_style = workbook.add_format({'valign': 'vcenter', 'align': 'center', 'font_size': 10, 'bold': True,
                                                'bg_color': '#F05A29', 'color': 'white', 'text_wrap': True,
                                                'border': True})
        product_row_style = workbook.add_format({'align': 'left', 'font_size': 10, 'bold': True, 'bg_color': '#777777',
                                                 'color': 'white', 'border': True})
        total_product_row_style = workbook.add_format(
            {'align': 'left', 'font_size': 10, 'bold': True, 'border': True})
        total_row_style = workbook.add_format(
            {'font_size': 10, 'bold': True, 'align': 'center', 'border': True})
        partner_row_style = workbook.add_format({'align': 'left', 'font_size': 10, 'border': True})
        qty_row_style = workbook.add_format({'font_size': 10, 'align': 'center', 'border': True})

        # Header Section #
        sheet.write(row, row, 'DEVICE INSTALLATION REPORT', title)
        row = row + 1
        sheet.merge_range('A{}:D{}'.format(row + 1, 3), 'Particular', header_row_style)
        for month in range(start_range, end_range + 1):
            column_month = month - start_range + 1
            end_column = column + column_month + 1

        sheet.write(row, end_column - 1, '', header_row_style)
        sheet.write(row + 1, end_column - 1, 'Total Qty', header_row_style)

        for month in range(start_range, end_range):
            month_name = calendar.month_abbr[month]
            if form_data['date_filter'] == 'custom':
                month_year = start_date
            else:
                month_year = datetime.strptime(start_date, '%Y-%m-%d')
            column_month = month - start_range + 1
            end_column = column + column_month + 1
            sheet.write(row, column + column_month, month_name + ' ' + str(month_year.year), main_header_row_style)
            sheet.write(row + 1, column + column_month, 'Quantity', main_header_row_style)

        row = 3
        if len(final_data['keys']) > 0:
            for data in final_data['keys']:
                total_device_qty = 0
                total_product_qty = 0
                for month in range(start_range, end_range + 1):
                    column_month = month - start_range + 1
                    end_column = column + column_month + 1
                    sheet.write(row, column + column_month, '',
                                product_row_style)
                sheet.merge_range('A{}:D{}'.format(row + 1, row + 1), data, product_row_style)

                for partner_list in sorted(final_data['list'][data]):
                    total_qty = 0
                    row = row + 1
                    sheet.merge_range('A{}:D{}'.format(row + 1, row + 1), partner_list, partner_row_style)
                    for month in range(start_range, end_range):
                        column_month = month - start_range + 1
                        end_column = column + column_month + 1
                        sheet.write(row, column + column_month, sum(final_data['list'][data][partner_list][month]['quantity']),qty_row_style)
                        total_qty = total_qty + sum(final_data['list'][data][partner_list][month]['quantity'])

                    sheet.write(row, end_column, total_qty, qty_row_style)
                row = row + 1

                for month in range(start_range, end_range):
                    column_month = month - start_range + 1
                    end_column = column + column_month + 1
                    sheet.write(row, column + column_month, sum(final_data['total'][data][month]['quantity']), total_row_style)
                    total_product_qty = total_product_qty + sum(final_data['total'][data][month]['quantity'])

                sheet.merge_range('A{}:D{}'.format(row + 1, row + 1), 'Total' + '  ' + data, total_product_row_style)
                sheet.write(row, end_column, total_product_qty, total_row_style)
                row = row + 1

            total_device_qty = 0
            for month in range(start_range, end_range):
                column_month = month - start_range + 1
                end_column = column + column_month + 1
                sheet.write(row, column + column_month, sum(final_data['total']['account'][month]['quantity']), header_row_style)
                total_device_qty = total_device_qty + sum(final_data['total']['account'][month]['quantity'])

            sheet.merge_range('A{}:D{}'.format(row + 1, row + 1), 'Total Devices', header_row_style)
            sheet.write(row, end_column, total_device_qty, header_row_style)


