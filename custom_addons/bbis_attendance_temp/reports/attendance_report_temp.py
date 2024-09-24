from odoo import models
from datetime import datetime
import pytz


class BbisAttendanceReportTempXlsx(models.AbstractModel):
    _name = 'report.bbis_attendance_temp.attendance_temp_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_in_out(self, emp_id, data):
        start_date = data['start_date']
        end_date = data['end_date']

        self.env.cr.execute(
            """
            SELECT CURRENT_DATE + i AS date_date,
            att_tmp.check_in, att_tmp.check_out, att_tmp.remarks
            from generate_series(date '%s' - CURRENT_DATE, date '%s' - CURRENT_DATE) i
            LEFT JOIN (
                SELECT name, date_time, check_in, check_out, remarks,
                check_in::timestamp at time zone 'utc' at time zone 'Asia/Dubai' AS check_in_dubai
                FROM bbis_attendance_temp
            ) AS att_tmp on CURRENT_DATE + i = att_tmp.check_in_dubai::date
            AND att_tmp.name = %d
            """ % (start_date, end_date, emp_id)
        )

        data = self.env.cr.dictfetchall()

        return data

    def _get_attendance_data(self, data):
        branch = data['branch_id'][0]

        self.env.cr.execute(
            """
            select emp.employee_id, emp.name, emp.id, dept.name as department,
            branch.monday, branch.tuesday, branch.wednesday, branch.thursday, branch.friday, branch.saturday,
            branch.sunday
            from hr_employee emp
            left join hr_department dept on dept.id = emp.department_id
            left join hr_working_branch branch on branch.id = emp.working_branch
            where branch.id = %d and emp.active = true
            
            """ % branch)

        attendance_data = self.env.cr.dictfetchall()

        record = {}

        for att in attendance_data:
            name = att['name'] or 'Undefined'
            employee_id = att['employee_id']
            department = att['department']

            if name not in record:
                record[name] = {'employee_id': employee_id, 'id': att['id'], 'department': department, 'off': []}

        final_data = {
            'list': record,
            'keys': sorted(list(record.keys())),
        }

        return final_data

    def generate_xlsx_report(self, workbook, data, orders):
        start_date = data['start_date']
        end_date = data['end_date']
        branch = data['branch_id']

        title_format = workbook.add_format({'bold': True, 'border': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 13})
        header_format = workbook.add_format(
            {'bold': True, 'border': True, 'font_size': 11, 'align': 'center', 'valign': 'vcenter',
             'bg_color': '#FFFF00', 'font_color': 'black'})
        cell_format_center = workbook.add_format(
            {'valign': 'vcenter', 'border': True, 'font_size': 11, 'align': 'center', 'text_wrap': False})
        day_off_format = workbook.add_format(
            {'border': True, 'font_size': 11, 'align': 'center', 'valign': 'vcenter',
             'bg_color': '#F8CBAD', 'font_color': 'black'})

        # start_date_1 = datetime.strptime(start_date, '%Y-%m-%d')
        # end_date_1 = datetime.strptime(end_date, '%Y-%m-%d')

        # from_to_date = '{} - {}'.format(start_date_1.strftime('%b %d, %Y'), end_date_1.strftime('%b %d, %Y'))
        # sheet_title = '{} Attendance Report from {}'.format(branch[1], from_to_date)

        branch_obj = self.env['hr.working.branch'].browse(branch[0])
        day_off = []

        # get all days off per branch
        if branch_obj.monday:
            day_off.append('monday')
        if branch_obj.tuesday:
            day_off.append('tuesday')
        if branch_obj.wednesday:
            day_off.append('wednesday')
        if branch_obj.thursday:
            day_off.append('thursday')
        if branch_obj.friday:
            day_off.append('friday')
        if branch_obj.saturday:
            day_off.append('saturday')
        if branch_obj.sunday:
            day_off.append('sunday')

        employees = self.get_attendance_data(data)

        # if no records found
        if not len(employees['keys']):
            sheet = workbook.add_worksheet()
            sheet.write(0, 0, "No record found")

        for emp in employees['keys']:
            emp_sheet = workbook.add_worksheet(emp)
            row, col = 0, 0

            # emp_sheet.merge_range('A1:G1', sheet_title, title_format)
            # row += 1
            emp_sheet.write(row, 0, "Date", header_format)
            emp_sheet.write(row, 1, "ID", header_format)
            emp_sheet.write(row, 2, "Employee Name", header_format)
            emp_sheet.write(row, 3, "Department", header_format)
            emp_sheet.write(row, 4, "Check-In Time", header_format)
            emp_sheet.write(row, 5, "Last-Out Time", header_format)
            emp_sheet.write(row, 6, "Remarks", header_format)

            emp_sheet.set_column(0, 0, 13)  # Date
            emp_sheet.set_column(1, 1, 7)  # ID
            emp_sheet.set_column(2, 2, 30)  # Emp Name
            emp_sheet.set_column(3, 3, 15)  # Department
            emp_sheet.set_column(4, 4, 15)  # Check in
            emp_sheet.set_column(5, 5, 15)  # Check out
            emp_sheet.set_column(6, 6, 30)  # Remarks

            emp_sheet.set_row(row, 30)

            row += 1

            emp_data = employees['list'][emp]
            in_out_data = self.get_in_out(emp_data['id'], data)

            for inout in in_out_data:

                date_tmp = datetime.strptime(inout['date_date'], '%Y-%m-%d')
                att_date = date_tmp.strftime("%d/%m/%Y")
                check_in = ''
                check_out = ''
                remarks = inout['remarks'] or ''

                if inout['check_in']:
                    check_in_dubai_tz = self.get_dubai_time(inout['check_in'])
                    check_out_dubai_tz = self.get_dubai_time(inout['check_out'])

                    check_in = check_in_dubai_tz.strftime("%I:%M %p")
                    check_out = check_out_dubai_tz.strftime("%I:%M %p")

                if (date_tmp.strftime('%A').lower() in day_off and not check_in) or ('day off' in remarks.lower()):
                    emp_sheet.write(row, 0, att_date, cell_format_center)
                    emp_sheet.merge_range('B{}:G{}'.format(row+1, row+1), date_tmp.strftime('%A') + " Off", day_off_format)
                else:
                    emp_sheet.write(row, 0, att_date, cell_format_center)
                    emp_sheet.write(row, 1, emp_data['employee_id'], cell_format_center)
                    emp_sheet.write(row, 2, emp, cell_format_center)
                    emp_sheet.write(row, 3, emp_data['department'], cell_format_center)

                    # check if no time in
                    if not check_in or (check_in == "12:00 AM" and check_out == "12:00 AM"):
                        check_in = ""
                        check_out = ""
                        remarks = ""

                        # check if there's leave
                        holidays = self.check_holidays(emp_data['id'], inout['date_date'])
                        if holidays:
                            check_in = "L"
                            check_out = "L"
                            remarks = holidays[0]['type']
                        else:
                            # check if WFH in online attendance
                            whm = self.check_online_attendance(emp_data['id'], inout['date_date'])
                            if whm:
                                check_in_dubai_tz = self.get_dubai_time(whm[0]['check_in'])
                                check_out_dubai_tz = self.get_dubai_time(whm[0]['check_out'])

                                check_in = check_in_dubai_tz.strftime("%I:%M %p")
                                check_out = check_out_dubai_tz.strftime("%I:%M %p")
                                remarks = "Work From Home"
                            else:
                                # check if it is under global leaves
                                global_leaves = self.check_global_leaves(inout['date_date'])

                                if global_leaves:
                                    check_in = "H"
                                    check_out = "H"
                                    remarks = global_leaves[0]['name']
                                else:
                                    # before marking as absent, make sure that date is not greater than current date
                                    if date_tmp <= datetime.today():
                                        check_in = "A"
                                        check_out = "A"
                                        remarks = "Absent"
                    # Worked in a week off.(Over Time)
                    else:
                        if date_tmp.strftime('%A').lower() in day_off:
                            remarks = 'Overtime'

                    emp_sheet.write(row, 4, check_in, cell_format_center)
                    emp_sheet.write(row, 5, check_out, cell_format_center)
                    emp_sheet.write(row, 6, remarks, cell_format_center)

                row += 1

    def _get_dubai_time(self, date_time):
        date_time_tmp = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')

        # initiate date time to utc time
        utc = pytz.utc
        date_utc = utc.localize(date_time_tmp)

        # convert date time to dubai time
        dubai = pytz.timezone('Asia/Dubai')
        dubai_time = date_utc.astimezone(dubai)

        return dubai_time

    def check_global_leaves(self, date):
        self.env.cr.execute(
            """
            select name from resource_calendar_leaves
            WHERE DATE(date_from) <= '%s' and DATE(date_to) >= '%s'
            limit 1
            """ % (date, date)
        )

        return self.env.cr.dictfetchall()

    def check_online_attendance(self, emp_id, date):
        self.env.cr.execute(
            """
            select check_in, check_out from hr_attendance
            WHERE employee_id = %d and DATE(check_in) = '%s'
            and is_online_attendance = true
            limit 1
            """ % (emp_id, date)
        )

        return self.env.cr.dictfetchall()

    def check_holidays(self, emp_id, date):
        self.env.cr.execute(
            """
            select l.id, l.name, l.date_from, l.date_to, lt.name as type
            from hr_holidays l
            LEFT JOIN hr_holidays_status lt on lt.id = l.holiday_status_id
            WHERE employee_id = %d and DATE(date_from) <= '%s' and DATE(date_to) >= '%s'
            and state = 'validate' and type = 'remove'
            limit 1
            """ % (emp_id, date, date)
        )

        return self.env.cr.dictfetchall()
