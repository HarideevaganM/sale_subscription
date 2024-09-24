from odoo import models, _
from datetime import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import pandas as pd
import string


class ScheduleEmployeeLeaveBalancesXLSX(models.AbstractModel):
    _name = 'report.bbis_hr.schedule_leave_balances_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_leaves_data(self, wizard):
        # initialize all needed fields
        form_dates = self._get_date(wizard)
        start_date = datetime.strptime(form_dates['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(form_dates['end_date'], "%Y-%m-%d").replace(hour=18)
        emp = wizard['employee_id']
        leave_type = wizard['leave_type_id']

        # initialize needed variables
        data = {}

        # begin getting data in leaves using orm
        leaves = self.env['hr.holidays.report'].search([])
        leaves = leaves.filtered(lambda field: field.state == "validate" and field.leave_type_id.id == leave_type.id)
        if emp:
            leaves = leaves.filtered(lambda field: field.employee_id.id == emp.id)

        # loop to every leaves to prepare data needed in excel
        for l in leaves:
            emp = l.employee_id
            if emp.id not in data:
                data[emp.id] = {'name': emp.name,
                                'designation': l.job_id.name,
                                'location': l.office_location_id.name,
                                'joining_date': l.joining_date,
                                'leaves': {},
                                'opening_days_balance': [],
                                }

            # lets convert date_from from str to date time format since this is very important field in report
            date_from = datetime.strptime(l.date_from, "%Y-%m-%d %H:%M:%S") if l.date_from else False
            date_to = datetime.strptime(l.date_to, "%Y-%m-%d %H:%M:%S") if l.date_to else False
            if date_from:
                year = date_from.year
                month = date_from.month

                # initialize year
                if year not in data[emp.id]['leaves']:
                    data[emp.id]['leaves'][year] = {}

                # initialize month
                if month not in data[emp.id]['leaves'][year]:
                    data[emp.id]['leaves'][year][month] = {'add': [], 'remove': []}

                # do not include initial days balance here
                if date_from >= start_date and date_to <= end_date:
                    # separate allocation request and leave request
                    if l.type == 'add':
                        data[emp.id]['leaves'][year][month]['add'] += [l.number_of_days]
                    else:
                        data[emp.id]['leaves'][year][month]['remove'] += [l.number_of_days]

                # separate initial days balance
                if date_from < start_date:
                    data[emp.id]['opening_days_balance'].append(l.number_of_days)

        return data

    def _get_date(self, data):
        form_data = data
        if form_data.date_filter == 'this_year':
            this_year = datetime.now()
            start_date = datetime.strftime(this_year, '%Y-01-01')
            end_date = datetime.strftime(this_year, '%Y-12-31')

        elif form_data.date_filter == 'last_year':
            last_year = datetime.now() - relativedelta(years=1)
            start_date = datetime.strftime(last_year, '%Y-01-01')
            end_date = datetime.strftime(last_year, '%Y-12-31')

        elif form_data.date_filter == 'joining_date':
            this_year = datetime.now()
            year = this_year.year
            emp_data = self.env['hr.employee'].search([('id', '=', form_data.employee_id.id)])
            if emp_data.joining_date:
                joining_date_str = emp_data.joining_date
                joining_date = datetime.strptime(joining_date_str, "%Y-%m-%d")
                start_date = joining_date.replace(year=year, day=1)
                end_date = joining_date + relativedelta(years=1)
                start_date = datetime.strftime(start_date, "%Y-%m-%d")
                end_date = datetime.strftime(end_date, "%Y-%m-%d")
            else:
                raise ValidationError(_('Please set an actual Joining Date for this Employee.'))

        else:
            start_date = form_data.start_date
            end_date = form_data.end_date

        if start_date > end_date:
            raise ValidationError(_('Please select the correct dates.'))

        return {
            'start_date': start_date,
            'end_date': end_date,
        }

    def _get_column_letter(self, num):
        """
        This method is used to retrieve excel columns since we have a dynamic columns in excel
        """
        alphabet = list(string.ascii_uppercase)
        alphabet_len = len(alphabet)
        whole = int(num / alphabet_len)

        if not whole:
            return alphabet[num]

        remainder = num - (whole * alphabet_len)

        return '%s%s' % (alphabet[whole-1], alphabet[remainder])

    def generate_xlsx_report(self, workbook, data, wizard):
        # convert dates from str to datetime format
        form_data = self._get_date(wizard)
        start_date = datetime.strptime(form_data['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(form_data['end_date'], "%Y-%m-%d")

        # excel formats
        default_format = {'font_size': 9, 'valign': 'vcenter', 'align': 'center', 'text_wrap': True}
        title = workbook.add_format({**default_format, 'bold': True, 'align': 'left', 'text_wrap': False})
        month_header = workbook.add_format({'border': True, 'bold': True, 'bg_color': '#ED7D31', 'font_color': 'white',
                                            **default_format})
        header1 = workbook.add_format({'border': True, 'bold': True, 'bg_color': '#548235', 'font_color': 'white',
                                       **default_format})
        header2 = workbook.add_format({'border': True, 'bold': True, 'bg_color': '#00B050', 'font_color': 'white',
                                       **default_format})

        # create new worksheet
        sheet = workbook.add_worksheet('Leaves')
        row = 0

        # add excel headers
        sheet.write(row, 0, 'BLACK BOX INTEGRATED SYSTEMS LLC', title)
        row += 1
        sheet.write(row, 0, 'SCHEDULE OF EMPLOYEES LEAVE BALANCES', title)
        row += 1
        start_date_str = start_date.strftime("%B %d, %Y").upper()
        end_date_str = end_date.strftime("%B %d, %Y").upper()
        sheet.write(row, 0, 'FROM %s - %s' % (start_date_str, end_date_str), title)

        # add column widths
        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 31)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 18)
        sheet.set_column('E:E', 13)
        sheet.set_column('F:F', 6)
        sheet.set_column('G:G', 13)

        row += 2  # add 3 to give empty space for the months
        sheet.write(row, 0, "SN", header1)
        sheet.write(row, 1, "Employee Name", header1)
        sheet.write(row, 2, "Designation", header1)
        sheet.write(row, 3, "Location", header1)
        sheet.write(row, 4, "Joining Date", header1)
        sheet.write(row, 5, "Daily Rate", header1)
        sheet.write(row, 6, "Opening Days Balance", header1)

        # freeze panes after employee name for easy scrolling
        sheet.freeze_panes(row+1, 2)

        # add empty headers
        sheet.merge_range('A%d:G%d' % (row, row), ' ', month_header)

        # using panda, get all month list from start date and end date
        month_list = [{"text": i.strftime("%b-%y"), "num": i.month, "year": i.year} for i in pd.date_range(start=start_date, end=end_date, freq='MS')]

        month_col_start = 7
        month_col = month_col_start
        for m in month_list:
            # lets add separate format from first to fourth column since individual border is needed
            cell_format = workbook.add_format({'bold': True, 'bg_color': '#ED7D31', 'font_color': 'white',
                                               **default_format})
            cell_format.set_top(1)
            cell_format.set_bottom(1)

            sheet.write(row, month_col, "Days Earned", header2)
            sheet.write(row - 1, month_col, "", cell_format)

            month_col += 1
            sheet.write(row, month_col, "Days Redeemed", header2)
            sheet.write(row - 1, month_col, "", cell_format)

            month_col += 1
            sheet.write(row, month_col, "Days Balance", header2)
            sheet.write(row - 1, month_col, m['text'], cell_format)

            month_col += 1
            sheet.write(row, month_col, "Daily Rate", header2)
            sheet.write(row - 1, month_col, "", cell_format)

            month_col += 1
            sheet.write(row, month_col, "Balance", header2)

            # add separate format for last cell since we need border right
            last_format = workbook.add_format({'bold': True, 'bg_color': '#ED7D31', 'font_color': 'white',
                                               **default_format})
            last_format.set_right()
            last_format.set_top()
            last_format.set_bottom()

            sheet.write(row - 1, month_col, "", last_format)
            month_col += 1

        # Add data from the database based on month
        row += 1
        sn = 0

        # cell formats
        items_format = {**default_format, 'border': True}
        center_format = workbook.add_format({**items_format})
        left_format = workbook.add_format({**items_format, 'align': 'left'})
        num_format = workbook.add_format({**items_format, 'num_format': '#,##0.00'})
        num_format_amount = workbook.add_format({**items_format, 'num_format': '#,##0.00', 'align': 'right'})

        leaves = self.get_leaves_data(wizard)
        items_start_row = row + 1
        for emp_id, leave in leaves.items():
            sn += 1
            center_format.set_border()
            opening_days_balance = sum(leave['opening_days_balance'])

            sheet.write(row, 0, sn, center_format)
            sheet.write(row, 1, leave['name'], left_format)
            sheet.write(row, 2, leave['designation'] or '', center_format)
            sheet.write(row, 3, leave['location'] or '', center_format)
            sheet.write(row, 4, leave['joining_date'] or '', center_format)
            sheet.write(row, 5, 100, center_format)
            sheet.write(row, 6, opening_days_balance, center_format)

            month_col = month_col_start
            total_days_balance = opening_days_balance
            for m in month_list:
                year = m['year']
                month = m['num']
                cur_row = row + 1

                if year in leave['leaves']:
                    # if year not in total_days_balance:
                    #     total_days_balance[year] = 0

                    if month in leave['leaves'][m['year']]:
                        days_earned = sum(leave['leaves'][year][month]['add'])
                        days_redeemed = sum(leave['leaves'][year][month]['remove'])
                        days_balance = days_earned + days_redeemed
                        total_days_balance += days_balance

                        sheet.write(row, month_col, days_earned, num_format)

                        month_col += 1
                        sheet.write(row, month_col, days_redeemed, num_format)

                        month_col += 1
                        days_balance_col = self.get_column_letter(month_col)
                        sheet.write(row, month_col, total_days_balance, num_format)

                        month_col += 1
                        sheet.write(row, month_col, '=F%d' % cur_row, num_format_amount)

                        month_col += 1
                        sheet.write(row, month_col, '=F%d*%s%d' % (cur_row, days_balance_col, cur_row), num_format_amount)

                        month_col += 1
                    else:
                        sheet.write(row, month_col, 0, num_format)
                        month_col += 1
                        sheet.write(row, month_col, 0, num_format)
                        month_col += 1
                        sheet.write(row, month_col, total_days_balance, num_format)
                        days_balance_col = self.get_column_letter(month_col)

                        month_col += 1
                        sheet.write(row, month_col, '=F%d' % cur_row, num_format_amount)
                        month_col += 1
                        sheet.write(row, month_col, '=F%d*%s%d' % (cur_row, days_balance_col, cur_row), num_format_amount)
                        month_col += 1
                else:
                    sheet.write(row, month_col, 0, num_format)
                    month_col += 1
                    sheet.write(row, month_col, 0, num_format)
                    month_col += 1
                    sheet.write(row, month_col, total_days_balance, num_format)
                    days_balance_col = self.get_column_letter(month_col)

                    month_col += 1
                    sheet.write(row, month_col, '=F%d' % cur_row, num_format_amount)
                    month_col += 1
                    sheet.write(row, month_col, '=F%d*%s%d' % (cur_row, days_balance_col, cur_row), num_format_amount)
                    month_col += 1
            row += 1

        # cell formats
        total_format = {**default_format, 'bold': True}
        total_left_format = workbook.add_format({**total_format})
        total_left_format.set_left()
        total_left_format.set_bottom(2)
        total_center_format = workbook.add_format({**total_format, 'num_format': '#,##0.00'})
        total_center_format.set_bottom(2)
        total_center_amount_format = workbook.add_format({**total_format, 'num_format': '#,##0.00', 'align': 'right'})
        total_center_amount_format.set_bottom(2)
        total_right_format = workbook.add_format({**total_format, 'num_format': '#,##0.00', 'align': 'right'})
        total_right_format.set_right()
        total_right_format.set_bottom(2)

        sheet.write(row, 0, "", total_left_format)
        sheet.write(row, 1, "Gross Total", total_center_format)
        sheet.write(row, 2, "", total_center_format)
        sheet.write(row, 3, "", total_center_format)
        sheet.write(row, 4, "", total_center_format)
        sheet.write(row, 5, "", total_center_format)
        sheet.write(row, 6, "=SUM(G%d:G%d)" % (items_start_row, row), total_center_format)

        month_col = month_col_start
        for m in month_list:
            col_letter = self.get_column_letter(month_col)
            col_name = "=SUM(%s%d:%s%d)" % (col_letter, items_start_row, col_letter, row)
            sheet.write(row, month_col, col_name, total_center_format)

            month_col += 1
            col_letter = self.get_column_letter(month_col)
            col_name = "=SUM(%s%d:%s%d)" % (col_letter, items_start_row, col_letter, row)
            sheet.write(row, month_col, col_name, total_center_format)

            month_col += 1
            col_letter = self.get_column_letter(month_col)
            col_name = "=SUM(%s%d:%s%d)" % (col_letter, items_start_row, col_letter, row)
            sheet.write(row, month_col, col_name, total_center_format)

            month_col += 1
            sheet.write(row, month_col, "", total_center_format)

            month_col += 1
            col_letter = self.get_column_letter(month_col)
            col_name = "=SUM(%s%d:%s%d)" % (col_letter, items_start_row, col_letter, row)
            sheet.write(row, month_col, col_name, total_right_format)

            month_col += 1
