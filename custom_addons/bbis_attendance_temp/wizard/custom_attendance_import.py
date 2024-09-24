import time

import select

from odoo import fields, models, api, _
import tempfile
import binascii
import xlrd
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
from csv import DictReader
from csv import reader
import pytz


# class attendaceemployee(models.Model):
#     _inherit = 'bbis.attendance.temp'

# Attendance import screen.
class customattendanceimport(models.TransientModel):
    _name = "attendance.import.file"

    employee_id = fields.Many2one('hr.employee', string='Employee')
    branch = fields.Many2one('hr.working.branch', required=True)
    file = fields.Binary('File', required=True)
    file_name = fields.Char("File Name")
    file_type = fields.Selection([('excel', 'Excel'),
                                  ('csv', 'CSV')], string='File Type', default='excel')
    month = fields.Selection([(1, 'January'),
                              (2, 'February'),
                              (3, 'March'),
                              (4, 'April'),
                              (5, 'May'),
                              (6, 'June'),
                              (7, 'July'),
                              (8, 'August'),
                              (9, 'September'),
                              (10, 'October'),
                              (11, 'November'),
                              (12, 'December')
                              ], string="Month", default=datetime.now().month, store=True, required=True)
    year = fields.Integer(string="Year", default=datetime.now().year, store=True, required=True)

    #@api.multi
    def import_file(self):
        self.env['bbis.attendance.temp'].truncate_attendances()
        for r in self:
            file_extension = r.file_name.split(".")[-1]
            if file_extension in ('xlsx', 'xls'):
                fields = []
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")

                if not self.file:
                    return False
                fp.write(binascii.a2b_base64(self.file))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                data_list = []

                # for ADNOC branch access each sheet instead of single sheet
                if r.branch.name.lower() == 'adnoc':
                    temp_list = []
                    for sheet in workbook.sheets():
                        for row_no in range(sheet.nrows):
                            if row_no <= 0:
                                fields = list(map(lambda row: str(row.value), sheet.row(row_no)))
                            else:
                                lines = list(
                                    map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                        row.value), sheet.row(row_no)))

                                if fields and lines:
                                    list_dict = dict(zip(fields, lines))
                                    temp_list.append(list_dict)

                    for k in temp_list:
                        if 'Name' not in k or not k['Name']:
                            continue

                        date_time, check_in, check_out, leave_off, remarks = '', '00:00', '00:00', '', ''

                        if 'Date' in k and k['Date']:
                            date_time = datetime(*xlrd.xldate_as_tuple(float(k['Date']), workbook.datemode)).strftime(
                                "%d/%m/%Y")

                        if 'Check_In' in k and k['Check_In']:
                            check_in = xlrd.xldate_as_tuple(float(k['Check_In']), workbook.datemode)
                            check_in = time(*check_in[3:]).strftime("%H:%M")

                        if 'Check_Out' in k and k['Check_Out']:
                            check_out = xlrd.xldate_as_tuple(float(k['Check_Out']), workbook.datemode)
                            check_out = time(*check_out[3:]).strftime("%H:%M")

                        if 'Leave/Off' in k and k['Leave/Off']:
                            leave_off = k['Leave/Off']

                        if 'Remarks' in k and k['Remarks']:
                            remarks = k['Remarks']

                        data_list += [
                            {'Name': k['Name'], 'Date': date_time, 'Check_In': check_in, 'Check_Out': check_out,
                             'Remarks': remarks, 'Leave/Off': leave_off}]
                else:
                    sheet = workbook.sheet_by_index(0)
                    for row_no in range(sheet.nrows):
                        if row_no <= 0:
                            fields = list(map(lambda row: str(row.value), sheet.row(row_no)))
                        else:
                            lines = list(
                                map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                    row.value),
                                    sheet.row(row_no)))

                            if fields and lines:
                                color_dict = dict(zip(fields, lines))
                                data_list.append(color_dict)

                exclude_import = self.env['hr.attendance.exclude.import']
                for line in data_list:
                    if r.branch.name.lower() == 'bbis':
                        name = line.get('Name').strip()
                        exclude = exclude_import.search([('name', '=', name)])
                        if exclude:
                            continue
                        self._prepare_data(line)
                    elif r.branch.name.lower() == 'musaffah':
                        name = line.get('First Name').strip()
                        exclude = exclude_import.search([('name', '=', name)])
                        if exclude:
                            continue
                        self._prepare_data_musaffah(line)
                    elif r.branch.name.lower() == 'adnoc':
                        name = line.get('Name').strip()
                        exclude = exclude_import.search([('name', '=', name)])
                        if exclude:
                            continue
                        self._prepare_data_otherBranches(line)
                    else:
                        raise ValidationError('Sorry! Unable to process. Please contact system administrator')
            else:
                raise ValidationError('Invalid File Type! Please select only Excel or CSV File.')

            if r.branch.name.lower() in ('bbis', 'musaffah'):
                self.env['bbis.attendance.temp'].compute_time_in_out(r.month, r.year, r.branch)

            return {
                'type': 'ir.actions.act_window',
                'name': _('Temporary Attendances'),
                'view_type': 'form',
                'res_model': 'bbis.attendance.temp',
                'view_mode': 'tree,form',
                'view_id': False,
                'target': 'current',
                'context': {'search_default_employee': 1}
            }

    def check_employee_name(self, name):
        if not name:
            raise UserError(_('Column for First/Employee Name has no value. '
                              'Please make sure to add or delete if not needed.'))

        emp = self.env['hr.employee'].search([('name', '=', name)], limit=1)
        if not emp:
            raise UserError(_('Sorry, the record {} in file does not exist in HR Employees. '
                              'Please make sure if this employee exist or check spelling before adding.'.format(name)))

        return emp

    def _prepare_data(self, line):
        name = line.get('Name').strip()
        emp = self.check_employee_name(name)

        if emp:
            self.env['bbis.attendance.temp'].create({'name': emp.id,
                                                     'date_time': line.get('Date/Time'),
                                                     'branch': self.branch.id,
                                                     'month': self.month,
                                                     'year': self.year})

    def _prepare_data_musaffah(self, line):
        name = line.get('First Name').strip()
        emp = self.check_employee_name(name)

        Actual_Date = datetime.strftime(datetime.strptime(line.get('Date') + ' ' + line.get('Time'), "%Y-%m-%d %H:%M"),
                                        "%m/%d/%Y %H:%M")
        if emp:
            self.env['bbis.attendance.temp'].create({'name': emp.id,
                                                     'date_time': Actual_Date,
                                                     'branch': self.branch.id,
                                                     'month': self.month,
                                                     'year': self.year})

    def _prepare_data_otherBranches(self, line):
        name = line.get('Name').strip()

        if name in (0 or '0'):
            return False

        emp = self.check_employee_name(name)

        dubai = pytz.timezone('Asia/Dubai')
        utc = pytz.utc

        if line.get('Name') in (0, '0', '') or line.get('Date') in ('', 0):
            return False

        Date = line.get('Date')
        tmp_check_in = line.get('Check_In')

        if line.get('Check_In') == '' or line.get('Check_In') == '00:00':
            prev_day = max(self.env['bbis.attendance.temp'].search([], order='id desc'))
            tmp_in = datetime.strptime(prev_day.check_in, "%Y-%m-%d %H:%M:%S")
            tmp_out = datetime.strptime(prev_day.check_out, "%Y-%m-%d %H:%M:%S")
            if tmp_in.hour > tmp_out.hour:
                offset = dubai.utcoffset(tmp_out)

                tmp_check_in = datetime.strftime(tmp_out + offset, '%H:%M')

        check_in = line.get('Date') + ' ' + tmp_check_in
        Actual_checkIn = datetime.strptime(check_in, "%d/%m/%Y %H:%M")
        if line.get('Check_Out') == '' or line.get('Check_Out') == '00:00':
            check_out = line.get('Date') + ' ' + tmp_check_in
        else:
            check_out = line.get('Date') + ' ' + line.get('Check_Out')
        Actual_checkOut = datetime.strptime(check_out, "%d/%m/%Y %H:%M")

        if Actual_checkIn > Actual_checkOut:
            Actual_checkOut = Actual_checkOut + relativedelta(days=1)

        Actual_checkIn = dubai.localize(Actual_checkIn)
        Actual_checkOut = dubai.localize(Actual_checkOut)
        # convert date time to UTC

        if line.get('Check_In') == '' or line.get('Check_In') == '0:00' and line.get('Check_Out') == '' or line.get('Check_Out') == '0:00':
            time_in_utc = Actual_checkIn + relativedelta(hours=20)
            time_out_utc = Actual_checkOut + relativedelta(hours=20)
        else:
            time_in_utc = Actual_checkIn.astimezone(utc)
            time_out_utc = Actual_checkOut.astimezone(utc)
        remarks = ''

        if time_in_utc == time_out_utc:
            if tmp_check_in == '00:00' and line.get('Check_Out') == '00:00':
                remarks = remarks + 'Leave or Absent'
            else:
                remarks = remarks + 'No Check Out'

        if line.get('Leave/Off') != '0':
            remarks = line.get('Leave/Off')

        if line.get('Remarks') != '0':
            remarks = remarks + '  ' + line.get('Remarks')

        excel_check_in_month = datetime.strptime(check_in, '%d/%m/%Y %H:%M')
        if excel_check_in_month.month != self.month:
            raise UserError(_('Please choose the correct month for Import.'))

        if emp:
            self.env['bbis.attendance.temp'].create({'name': emp.id,
                                                 'date_time': datetime.strptime(Date, '%d/%m/%Y')
                                                .strftime('%m/%d/%Y') + ' - (Done)',
                                                 'check_in': time_in_utc,
                                                 'check_out': time_out_utc,
                                                 'remarks': remarks,
                                                 'branch': self.branch.id,
                                                 'month': self.month,
                                                 'year': self.year})

    def compute_checkout(self):
        checkout_count = self.env['bbis.attendance.temp'].search_count([])
        return checkout_count


class Attendance_Data(models.Model):
    _inherit = 'bbis.attendance.temp'

    #@api.multi
    def method_a(self):
        self.env['bbis.attendance.temp'].truncate_attendances()
