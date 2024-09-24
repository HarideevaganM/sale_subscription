from odoo import models, _
from datetime import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class EmployeeLeaveReportXLSX(models.AbstractModel):
    _name = 'report.bbis_hr.leave_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_date(self, data, workbook):
        form_data = data['form']
        if form_data['date_filter'] == 'this_year':
            this_year = datetime.now()
            start_date = datetime.strftime(this_year, '%Y-01-01')
            end_date = datetime.strftime(this_year, '%Y-12-31')

        elif form_data['date_filter'] == 'last_year':
            last_year = datetime.now() - relativedelta(years=1)
            start_date = datetime.strftime(last_year, '%Y-01-01')
            end_date = datetime.strftime(last_year, '%Y-12-31')

        else:
            start_date = form_data['start_date']
            end_date = form_data['end_date']

        if start_date > end_date:
            raise ValidationError(_('Please select the correct dates.'))

        return {
            'start_date': start_date,
            'end_date': end_date,
        }

    def generate_xlsx_report(self, workbook, data, products):
        form_data = self._get_date(data, workbook)
        start_date = form_data['start_date']
        end_date = form_data['end_date']

        sheet = workbook.add_worksheet('Employee Leave Report')
        self.env.cr.execute(
            """
            select hr_employee.name as employee,hr_holidays_status.name as leave_type,hr_holidays.date_from,
            hr_holidays.date_to,case when type = 'remove' then hr_holidays.number_of_days * -1 end as leaves_taken,
            case when type = 'add' then hr_holidays.number_of_days end as accrued_leaves,
            case when hr_holidays.state = 'draft' then 'Draft' when hr_holidays.state = 'submit' then 'Submitted'
            when hr_holidays.state = 'confirm' then 'Officer Approval' 
            when hr_holidays.state = 'validate2' then 'Manager Approval' 
            when hr_holidays.state = 'validate1' then 'HR Approval' 
            when hr_holidays.state = 'validate' then 'CEO Approved'
            when hr_holidays.state = 'cancel' then 'Cancelled' else 'Refused' end as leave_status
            from hr_holidays inner join hr_employee on
            hr_holidays.employee_id = hr_employee.id 
            inner join  hr_holidays_status on 
            hr_holidays.holiday_status_id = hr_holidays_status.id
            where hr_employee.id = '%s' and hr_holidays.date_from >= '%s'
            and hr_holidays.date_from <= '%s' and hr_holidays.date_from is not null
            order by employee, leave_type, date_from
            """ % (data['employee_id'], start_date, end_date))

        emp_leave_data = self.env.cr.dictfetchall()

        self.env.cr.execute(
            """
            select hr_employee.name as employee,hr_holidays_status.name as leave_type
            from hr_holidays inner join hr_employee on
            hr_holidays.employee_id = hr_employee.id 
            inner join  hr_holidays_status on 
            hr_holidays.holiday_status_id = hr_holidays_status.id
            where hr_employee.id = '%s' and hr_holidays.date_from >= '%s'
            and hr_holidays.date_from <= '%s' and hr_holidays.date_from is not null
            group by employee, leave_type
            order by employee, leave_type
            """ % (data['employee_id'], start_date, end_date))

        grouped_leave_data = self.env.cr.dictfetchall()

        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'font_size': 20, 'border': True})
        normal = workbook.add_format({'align': 'center', 'border': True, 'valign': 'vcenter'})
        grouped_values = workbook.add_format({'align': 'center', 'border': True, 'valign': 'vcenter'})
        header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border': True, 'bg_color': '#F05A29',
                                                'text_wrap': True, 'font_color': 'white', 'valign': 'vcenter'})
        content_row_style = workbook.add_format({'align': 'center', 'num_format': '#,##0.00', 'border': True})

        sheet.merge_range('A1:H1', 'Employees Leave Report', title)
        sheet.merge_range('A2:H2', 'From: ' + datetime.strftime(datetime.strptime(start_date, '%Y-%m-%d'), '%d-%m-%Y')
                          + ' To: ' + datetime.strftime(datetime.strptime(end_date, '%Y-%m-%d'), '%d-%m-%Y') + ' ',
                          normal)

        sheet.merge_range('A3:H3', '', normal)

        row = 3

        sheet.write(row, 0, 'Employee Name', header_row_style)
        sheet.write(row, 1, 'Leave Type', header_row_style)
        sheet.write(row, 2, 'Date From', header_row_style)
        sheet.write(row, 3, 'Date To', header_row_style)
        sheet.write(row, 4, 'No:Of Days', header_row_style)
        sheet.write(row, 5, 'Consumed Leaves', header_row_style)
        sheet.write(row, 6, 'Total Leaves', header_row_style)
        sheet.write(row, 7, 'Remaining Leaves', header_row_style)

        sheet.set_column('A:A', 35)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 12)
        sheet.set_column('D:D', 12)
        sheet.set_column('E:E', 12)
        sheet.set_column('F:F', 12)
        sheet.set_column('G:G', 12)
        sheet.set_column('H:H', 12)

        row = 4
        start_row = 4
        ending_row = 4
        leave_type_rows = []

        for group_leave_data in grouped_leave_data:
            total_leaves_taken = 0
            total_leaves_accrued = 0
            for leave_data in emp_leave_data:
                if group_leave_data['leave_type'] == leave_data['leave_type']:

                    sheet.write(row, 2, datetime.strftime(datetime.strptime(leave_data['date_from'],
                                                                            '%Y-%m-%d %H:%M:%S'), '%d-%m-%Y'), normal)
                    sheet.write(row, 3, datetime.strftime(datetime.strptime(leave_data['date_to'],
                                                                            '%Y-%m-%d %H:%M:%S'), '%d-%m-%Y'), normal)
                    sheet.write(row, 4, leave_data['leaves_taken'], normal)
                    if leave_data['leaves_taken']:
                        total_leaves_taken = total_leaves_taken + leave_data['leaves_taken']
                    if leave_data['accrued_leaves']:
                        total_leaves_accrued = total_leaves_accrued + leave_data['accrued_leaves']
                    sheet.conditional_format('A4:H' + str(row), {'type': 'blanks', 'format': content_row_style})
                    if row <= start_row:
                        sheet.write(row, 0, leave_data['employee'], grouped_values)
                        sheet.write(row, 1, group_leave_data['leave_type'], grouped_values)
                        sheet.write(row, 5, total_leaves_taken, grouped_values)
                        sheet.write(row, 6, total_leaves_accrued, grouped_values)
                        sheet.write(row, 7, total_leaves_accrued - total_leaves_taken, grouped_values)
                    row += 1
                    ending_row = row
                    # if leave_type_rows and leave_data['leave_type'] not in leave_type_rows:
                    #     start_row = row

                    leave_type_rows.append(leave_data['leave_type'])

            remaining_leaves = total_leaves_accrued - total_leaves_taken

            if row > start_row + 1:
                sheet.merge_range('A{}:A{}'.format(start_row + 1, ending_row), leave_data['employee'], grouped_values)
                sheet.merge_range('B{}:B{}'.format(start_row + 1, ending_row), group_leave_data['leave_type'], grouped_values)
                sheet.merge_range('F{}:F{}'.format(start_row + 1, ending_row), total_leaves_taken, grouped_values)
                sheet.merge_range('G{}:G{}'.format(start_row + 1, ending_row), total_leaves_accrued, grouped_values)
                sheet.merge_range('H{}:H{}'.format(start_row + 1, ending_row), remaining_leaves, grouped_values)
            start_row = row
