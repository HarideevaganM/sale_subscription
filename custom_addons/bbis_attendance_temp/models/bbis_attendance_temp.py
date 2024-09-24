# -*- coding: utf-8 -*-
import calendar
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from itertools import groupby
import pytz


class BbisAttendanceTemp(models.Model):
    _name = 'bbis.attendance.temp'
    _description = 'BBIS Attendance Upload'
    _order = 'name, date_time asc'

    # name = fields.Char(required=True, string="Employee Name")
    name = fields.Many2one('hr.employee', required=True, string="Employee Name")
    date_time = fields.Char(string="Date/Time")
    check_in = fields.Datetime()
    check_out = fields.Datetime()
    remarks = fields.Char(string="Remarks")
    branch = fields.Many2one('hr.working.branch', required=True)
    month = fields.Integer(string="Month", store=True, required=True)
    year = fields.Integer(string="Year", store=True, required=True)

    @api.onchange('check_in')
    def _get_month_year(self):
        self.ensure_one()
        if self.check_in:
            check_in_date = datetime.strptime(self.check_in, '%Y-%m-%d %H:%M:%S')
            self.year = check_in_date.year
            self.month = check_in_date.month

    def _get_attendance_count(self):
        count = self.env['bbis.attendance.temp'].search_count([])
        return count

    def find_employee(self, name):
        employee_id = self.env['hr.employee'].search([('name', '=', name)], limit=1)
        if employee_id:
            return employee_id
        else:
            raise UserError(_('Employee with given name: "{}" does not exist on Employee records. '
                              'Please make sure this record exist.'.format(name)))

    def compute_time_in_out(self, month, year, branch, biometric=False):
        """
        This will recompile the data, since in each day, the attendance time in and time out is in separate rows,
        it needs to delete other time in/out and retain only first time in and last time out.
        """

        # Select all attendance records
        attendances = self.search([])

        # Select individual names from the attendance
        individual_names = self.read_group([('name', '!=', '')], ['name'], ['name'])

        # store on this variable the recompiled data with only the first time in and last time out
        clean_attendances = []
        if attendances:
            # First loop individual names to all the attendance
            for ind_name in individual_names:

                emp_name = ind_name['name'][0]

                # store employee date and time in and check out
                emp_date_times = []

                for att in attendances:
                    if att.name.id == emp_name:

                        date_time_tmp = att.date_time
                        try:
                            if biometric:
                                date_time = datetime.strptime(date_time_tmp, '%Y-%m-%d %H:%M:%S')
                            else:
                                date_time = datetime.strptime(date_time_tmp, '%m/%d/%Y %H:%M')
                        except:
                            raise ValidationError('Either attendance computations has already been done '
                                                  'or datetime format is incorrect.'
                                                  'Please reset and import attendance again.')

                        emp_date_times.append(date_time)

                # Sort the date_time in ascending order
                sorted_emp_date_time = sorted(emp_date_times)

                # group sorted_emp_date_time by day
                for check_day, check_timings in groupby(sorted_emp_date_time, key=lambda x: x.date()):

                    # convert check_timings to list to get the first time in and last timeout
                    check_timings_list = list(check_timings)

                    # get first time in
                    first_time_in = check_timings_list[0]
                    last_time_out = check_timings_list[-1]

                    # convert date time to dubai time
                    dubai = pytz.timezone('Asia/Dubai')
                    first_time_in_dubai_tz = dubai.localize(first_time_in)
                    last_time_out_dubai_tz = dubai.localize(last_time_out)

                    # convert date time to UTC
                    utc = pytz.utc
                    first_time_in_utc = first_time_in_dubai_tz.astimezone(utc)
                    last_time_out_utc = last_time_out_dubai_tz.astimezone(utc)

                    # only add last time out if timings are greater than 1, otherwise leave it empty
                    if len(check_timings_list) <= 1:
                        last_time_out_utc = first_time_in_utc
                        remarks = 'No Check Out'
                    else:
                        remarks = ''
                        # last_time_out_utc = ''

                    # add the per day time in and time out to clean_attendances
                    clean_attendances.append({
                        'name': emp_name,
                        'date_time': check_day.strftime('%d/%m/%Y') + ' - (Done)',
                        'check_in': first_time_in_utc,
                        'check_out': last_time_out_utc,
                        'remarks': remarks,
                        'branch': branch.id,
                        'month': month,
                        'year': year})

            # check if there is a record to be saved
            if clean_attendances:

                # delete first all the records. Don't worry it is already stored on clean_attendances
                self.env.cr.execute('TRUNCATE only bbis_attendance_temp RESTART IDENTITY')

                # insert the recompiled data to database
                for r in clean_attendances:
                    self.create(r)

            return {'status': 1, 'title': 'Compute Attendance Time In/Out',
                    'message': 'Attendance was successfully computed'}
        else:
            return {'status': 0, 'title': 'Compute Attendance Time In/Out', 'message':
                'Please upload attendances to be computed.'}

    def upload_attendances(self):
        # first_day = self.env['bbis.attendance.temp'].search([('month', '!=', '')], limit=1)
        # day_count = calendar.monthrange(first_day.year, first_day.month)[1]

        attendances = self.env['bbis.attendance.temp'].search([])
        if attendances:

            for att in attendances:
                employee_id = att.name

                # emp_count = self.env['bbis.attendance.temp'].search_count([('name', '=', employee_id.name)])
                if not att.branch:
                    raise UserError(_('Please make sure to add Office Location of the employee. Employee Name: ' + employee_id.name + '.'))

                if att.check_in > att.check_out:
                    att.check_out = datetime.strptime(att.check_out, '%Y-%m-%d %H:%M:%S') + timedelta(days=1)

                attendance = {
                    'employee_id': employee_id.id,
                    # 'name': att.name,
                    'check_in': att.check_in,
                    'check_out': att.check_out,
                    'remarks': att.remarks
                }

                self.env['hr.attendance'].create(attendance)

            return {'status': 1, 'title': 'Upload Attendance', 'message': 'Attendance was successfully uploaded'}

        else:
            return {'status': 0, 'title': 'Upload Attendance', 'message': 'Please upload attendance to upload.'}

    def truncate_attendances(self):

        self.env.cr.execute('TRUNCATE only bbis_attendance_temp RESTART IDENTITY')

        return {'title': 'Reset Attendance', 'message': 'Attendance was successfully reset'}

    # Generating the all dates in a particular month for the time of attendance.
    def process_all_dates(self, month, year, branch):
        month = int(month)
        year = int(year)
        last_day = calendar.monthrange(year, month)[1]
        new_days = list()

        employee_names = self.env['hr.employee'].search([('working_branch', '=', branch.id)])
        if employee_names:
            for emp_id in employee_names:
                days = list(range(1, last_day + 1))
                attendance_temp = self.env['bbis.attendance.temp'].search([('name', '=', emp_id.name)])
                if attendance_temp:
                    for attendance in attendance_temp:
                        check_in = datetime.strptime(attendance.check_in, '%Y-%m-%d %H:%M:%S')
                        if check_in.month != month:
                            raise UserError(_('Please choose the correct month for Import.'))
                        if check_in.day in days and month == check_in.month and year == check_in.year:
                            new_days.append(check_in.day)

                        if new_days != []:
                            days.remove(check_in.day)

                        else:
                            sql = "delete from bbis_attendance_temp where name = '" + emp_id.name + "'"
                            self.env.cr.execute(sql)

                for day in days:
                    new_day = datetime.strftime(datetime(year, month, day, 0, 0), '%d/%m/%Y %H:%M')
                    new_date = datetime(year, month, day)
                    new_day = datetime.strptime(new_day, "%d/%m/%Y %H:%M")

                    if new_day.strftime("%A") == 'Saturday' or new_day.strftime("%A") == 'Sunday':
                        remarks = 'Day Off'
                    else:
                        remarks = 'Leave or Absent'

                    dubai = pytz.timezone('Asia/Dubai')
                    new_day = dubai.localize(new_day)

                    # convert date time to UTC
                    utc = pytz.utc
                    new_day = new_day.astimezone(utc)

                    self.env['bbis.attendance.temp'].create({'name': emp_id.name,
                                                             'date_time': datetime.strftime(new_date,
                                                                                            '%d/%m/%Y') + ' - (Done)',
                                                             'check_in': new_day,
                                                             'check_out': new_day,
                                                             'remarks': remarks,
                                                             'branch': branch.id,
                                                             'month': month,
                                                             'year': year})

