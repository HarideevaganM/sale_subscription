# -*- coding: utf-8 -*-
import tempfile
import binascii
import logging
import xlrd
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
import pytz
import time
from odoo.exceptions import Warning
from odoo import models, fields, api, exceptions, _
_logger = logging.getLogger(__name__)
from io import StringIO
import io
from odoo.exceptions import ValidationError, UserError

try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')

class Attendances(models.Model):
    _inherit= "hr.attendance"

    card_number = fields.Char(string="Card Number")
    employee_card = fields.Char(string="Employee ID")
    # enter
    entry_door_name = fields.Char(string="Enter Door")
    entry_point = fields.Char(string="Entry Point")
    entry_remark = fields.Char(string="Enter Remark")
    entry_sl_no = fields.Char(strig='Enter Event No')
    entry_alarm_date = fields.Date()
    # exist
    exist_remark = fields.Char(strig='Exist Remark')
    exist_point = fields.Char(string="Exist Point")
    exist_door_name = fields.Char(string="Exist Door")
    exist_sl_no = fields.Char(strig='Enter Event No')

class Attendances(models.TransientModel):
    _name= "import.attendances.wizard"

    file = fields.Binary('File')

    #@api.multi
    def import_file(self):
        fields = []
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        if not self.file:
            return False
        fp.write(binascii.a2b_base64(self.file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        data_list = []
        for row_no in range(sheet.nrows):
            if row_no <= 0:
                fields = list(map(lambda row: str(row.value), sheet.row(row_no)))
            else:
                lines = list(map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                if fields and lines:
                    color_dict = dict(zip(fields, lines))
                    data_list.append(color_dict)
        for line in data_list:
            value = self._prepaire_data(line)
            if value:
                attendance_id = self.env['hr.attendance'].create(value)
        return True

    def _prepaire_data(self, line):
        values = {}
        employee_id  = self.env['hr.employee']
        name = line.get('Employee Name')
        card = int(float(line.get('Employee ID')))
        cur_date = False

        if not name and not card:
            raise UserError(_('Employee Name or Employee ID not exist in file'))

        employee_id = self._find_employee(name, card)
        date_time = line.get('Alarm Date') and line.get('Alarm Time')
        if not date_time:
            raise UserError(_('Alarm Date and Alarm Time not exist in file'))

        cur_date_tz = ('%s %s') %(line.get('Alarm Date'), line.get('Alarm Time'))
        if cur_date_tz:
            cur_date_convert = datetime.strptime(cur_date_tz, '%m-%d-%Y %H:%M:%S')
            if cur_date_convert:
                timezone = pytz.timezone(self._context.get('tz') or 'UTC')
                cur_date = timezone.localize(cur_date_convert).astimezone(pytz.UTC)

        if cur_date and line.get('Entry/Exit') and employee_id:
            if line.get('Entry/Exit') == 'Exit':
                in_attandance_id = self.env['hr.attendance'].search([('entry_alarm_date', '=', line.get('Alarm Date')), ('employee_id', '=', employee_id.id), ('entry_point','=', 'Entry')], limit=1)
                if in_attandance_id:
                    in_attandance_id.write({'exist_door_name': line.get('Door Name') if line.get('Door Name') else False,
                    'exist_point': line.get('Entry/Exit') if line.get('Entry/Exit') else False,
                    'check_out' : cur_date, 
                    'exist_sl_no': line.get('Event Slno') if line.get('Event Slno') else False,
                    'exist_remark': line.get('Message Description') if line.get('Message Description') else False
                })
            else:
                values.update({
                    'employee_id': employee_id and employee_id.id,
                    'check_in': cur_date,
                    'entry_door_name': line.get('Door Name') if line.get('Door Name') else False,
                    'card_number': line.get('Card Number') if line.get('Card Number') else False,
                    'employee_card': line.get('Employee ID') if line.get('Employee ID') else False ,
                    'entry_point': line.get('Entry/Exit') if line.get('Entry/Exit') else False,
                    'entry_sl_no' : line.get('Event Slno') if line.get('Event Slno') else False,
                    'entry_alarm_date': line.get('Alarm Date') if line.get('Alarm Date') else False,
                    'entry_remark': line.get('Message Description') if line.get('Message Description') else False,
                })
                return values
        return values

    def _find_employee(self, name, card):
        employee_id = self.env['hr.employee'].search([('name', '=', name), ('employee_id', '=',  card)], limit=1)
        if employee_id:
            return employee_id
        else:
            raise UserError(_('Employee with given Name and ID not exist'))
        return False