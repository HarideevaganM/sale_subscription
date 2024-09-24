from odoo import models, _
from datetime import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class ScheduleEmployeeLeaveSummaryXLSX(models.AbstractModel):
    _name = 'report.bbis_hr.schedule_leave_summary_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_leaves_data(self, wizard):
        # initialize all needed fields
        form_dates = self._get_date(wizard)
        start_date = datetime.strptime(form_dates['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(form_dates['end_date'], "%Y-%m-%d").replace(hour=18)
        emp = wizard['employee_id']

        # initialize needed variables
        data = {}

        # begin getting data in leaves using orm
        leaves = self.env['hr.holidays.report'].sudo().search([])
        leaves = leaves.filtered(lambda field: field.state == "validate")
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
                                'opening_days_balance': {},
                                }

            # lets convert date_from from str to date time format since this is very important field in report
            date_from = datetime.strptime(l.date_from, "%Y-%m-%d %H:%M:%S") if l.date_from else False
            date_to = datetime.strptime(l.date_to, "%Y-%m-%d %H:%M:%S") if l.date_to else False

            if date_from:
                year = date_from.year
                month = date_from.month
                leave_type = l.leave_type_id.id

                # initialize leave type
                if leave_type not in data[emp.id]['leaves']:
                    data[emp.id]['leaves'][leave_type] = {}

                # initialize year
                if year not in data[emp.id]['leaves'][leave_type]:
                    data[emp.id]['leaves'][leave_type][year] = {}

                # initialize month
                if month not in data[emp.id]['leaves'][leave_type][year]:
                    data[emp.id]['leaves'][leave_type][year][month] = {'add': {'total': [], 'details': []},
                                                                       'remove': {'total': [], 'details': []}}

                # format dates
                date_from_local = date_from + relativedelta(hours=4)
                date_to_local = date_to + relativedelta(hours=4)

                date_from_format_date = date_from_local.strftime("%b %d, %Y")
                date_from_format_datetime = date_from_local.strftime("%b %d, %Y %I:%M %p")
                date_to_format_date = date_to_local.strftime("%b %d, %Y")
                date_to_format_datetime = date_to_local.strftime("%b %d, %Y %I:%M %p")

                # add the formats in details object
                details = {'date_from': l.date_from, 'date_from_format_date': date_from_format_date,
                           'date_from_format_datetime': date_from_format_datetime,
                           'date_to': l.date_to, 'date_to_format_date': date_to_format_date,
                           'date_to_format_datetime': date_to_format_datetime, 'num_days': l.number_of_days,
                           'reason': l.reason}

                # do not add initial balance here
                if date_from >= start_date and date_to <= end_date:
                    # separate allocation request and leave request
                    if l.type == 'add':
                        data[emp.id]['leaves'][leave_type][year][month]['add']['total'] += [l.number_of_days]
                        data[emp.id]['leaves'][leave_type][year][month]['add']['details'] += [details]
                    else:
                        data[emp.id]['leaves'][leave_type][year][month]['remove']['total'] += [l.number_of_days]
                        data[emp.id]['leaves'][leave_type][year][month]['remove']['details'] += [details]

                # separate initial days balance
                if date_from < start_date:
                    # initialize leave type
                    if leave_type not in data[emp.id]['opening_days_balance']:
                        data[emp.id]['opening_days_balance'][leave_type] = []

                    data[emp.id]['opening_days_balance'][leave_type].append(l.number_of_days)

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

    def generate_xlsx_report(self, workbook, data, wizard):
        # convert dates from str to datetime format
        form_data = self._get_date(wizard)
        start_date = datetime.strptime(form_data['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(form_data['end_date'], "%Y-%m-%d")

        # excel formats
        default_format = {'font_size': 9, 'valign': 'vcenter', 'align': 'center', 'text_wrap': True}
        title = workbook.add_format({**default_format, 'bold': True, 'align': 'left', 'text_wrap': False})
        header0 = workbook.add_format({'border': True, 'bold': True, 'bg_color': '#ED7D31', 'font_color': 'white',
                                            **default_format})
        header1 = workbook.add_format({'border': True, 'bold': True, 'bg_color': '#548235', 'font_color': 'white',
                                       **default_format})

        # create new worksheet
        sheet = workbook.add_worksheet('Leave Summary')
        row = 0

        # add excel headers
        sheet.write(row, 0, 'BLACK BOX INTEGRATED SYSTEMS LLC', title)
        row += 1
        sheet.write(row, 0, 'LEAVES SUMMARY', title)
        row += 1
        start_date_str = start_date.strftime("%B %d, %Y").upper()
        end_date_str = end_date.strftime("%B %d, %Y").upper()
        sheet.write(row, 0, 'FROM %s - %s' % (start_date_str, end_date_str), title)

        # add column widths
        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 31)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 18)
        sheet.set_column('E:F', 13)
        sheet.set_column('G:G', 13)
        sheet.set_column('H:H', 50)
        sheet.set_column('I:I', 13)
        sheet.set_column('J:J', 50)
        sheet.set_column('K:M', 13)

        row += 1
        sheet.write(row, 0, "SN", header1)
        sheet.write(row, 1, "Employee Name", header1)
        sheet.write(row, 2, "Designation", header1)
        sheet.write(row, 3, "Location", header1)
        sheet.write(row, 4, "Joining Date", header1)
        sheet.write(row, 5, "Leave Type", header1)
        sheet.write(row, 6, "Opening \nLeaves Balance", header0)
        sheet.write(row, 7, "Consumed Leaves Details", header0)
        sheet.write(row, 8, "Total \nConsumed Leaves", header0)
        sheet.write(row, 9, "Leaves Allocation Details", header0)
        sheet.write(row, 10, "Total \nLeaves Allocation", header0)
        sheet.write(row, 11, "Total \nLeaves Balance", header0)
        sheet.write(row, 12, "Remaining \nLeaves", header0)

        # freeze panes after employee name for easy scrolling
        sheet.freeze_panes(row + 1, 2)

        # cell formats
        items_format = {**default_format, 'border': True}
        center_format = workbook.add_format({**items_format})
        left_format = workbook.add_format({**items_format, 'align': 'left'})
        num_format = workbook.add_format({**items_format, 'num_format': '#,##0.00'})
        num_format_amount = workbook.add_format({**items_format, 'num_format': '#,##0.00', 'align': 'right'})

        sn = 0
        row += 1
        items_start_row = row

        leaves = self.get_leaves_data(wizard)
        for emp_id, leave in leaves.items():

            for l_type in leave['leaves']:
                sn += 1
                # get leave type
                leave_type = self.env['hr.holidays.status'].browse(l_type)
                leave_dates = ''
                remove_total = 0
                add_leave_dates = ''
                add_total = 0
                opening_balance = sum(leave['opening_days_balance'][l_type]) if l_type in leave['opening_days_balance'] else 0

                sheet.write(row, 0, sn, center_format)
                sheet.write(row, 1, leave['name'], left_format)
                sheet.write(row, 2, leave['designation'] or '', center_format)
                sheet.write(row, 3, leave['location'] or '', center_format)
                sheet.write(row, 4, leave['joining_date'] or '', center_format)
                sheet.write(row, 5, leave_type.name or '', center_format)
                sheet.write(row, 6, opening_balance or 0, center_format)

                for y, yv in leave['leaves'][l_type].items():
                    for m, mv in yv.items():
                        remove_total += sum(mv['remove']['total'])
                        add_total += sum(mv['add']['total'])
                        remove_details = mv['remove']['details']
                        add_details = mv['add']['details']

                        for d in remove_details:
                            leave_dates += '%s - %s (%s Days)\n -- %s \n' % (d['date_from_format_datetime'],
                                                                                     d['date_to_format_datetime'],
                                                                                     abs(d['num_days']), d['reason'])
                        for a in add_details:
                            add_leave_dates += '%s (%s Days)\n -- %s \n' % (a['date_from_format_datetime'],
                                                                            a['num_days'], a['reason'])

                sheet.write(row, 7, leave_dates[:-1], left_format)
                sheet.write(row, 8, abs(remove_total), num_format)
                sheet.write(row, 9, add_leave_dates[:-1], left_format)
                sheet.write(row, 10, add_total, num_format)
                sheet.write(row, 11, add_total + opening_balance, num_format)
                sheet.write(row, 12, sum([opening_balance, add_total, remove_total]), num_format)

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
        total_right_format = workbook.add_format({**total_format, 'num_format': '#,##0.00'})
        total_right_format.set_right()
        total_right_format.set_bottom(2)

        sheet.write(row, 0, "", total_left_format)
        sheet.write(row, 1, "Gross Total", total_center_format)
        sheet.write(row, 2, "", total_center_format)
        sheet.write(row, 3, "", total_center_format)
        sheet.write(row, 4, "", total_center_format)
        sheet.write(row, 5, "", total_center_format)
        sheet.write(row, 6, "=SUM(G%d:G%d)" % (items_start_row, row), total_center_format)
        sheet.write(row, 7, "", total_center_format)
        sheet.write(row, 8, "=SUM(I%d:I%d)" % (items_start_row, row), total_center_format)
        sheet.write(row, 9, "", total_center_format)
        sheet.write(row, 10, "=SUM(K%d:K%d)" % (items_start_row, row), total_center_format)
        sheet.write(row, 11, "=SUM(L%d:L%d)" % (items_start_row, row), total_center_format)
        sheet.write(row, 12, "=SUM(M%d:M%d)" % (items_start_row, row), total_right_format)
