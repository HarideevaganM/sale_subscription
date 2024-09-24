# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class PrintBBISAttendanceReport(models.TransientModel):
    _name = 'monthly.attendance.report'
    _description = 'Wizard: Monthly Attendance Report'

    account_reports = fields.Selection([('monthly_attendance', 'Monthly Attendance')],
                                       string='Report')
    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    branch_id = fields.Many2one('hr.working.branch', string="Office Location")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    is_attendance_temp = fields.Boolean()

    def download_attendance_temp(self):
        start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d')

        if start_date > end_date:
            raise ValidationError("Sorry! Start date must be lesser than end date.")

        return self.env.ref('bbis_attendance_temp.monthly_attendance_temp_report').report_action(self, data=self.read()[0])

    #@api.multi
    def download_attendance(self):
        start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d')

        if start_date > end_date:
            raise ValidationError("Sorry! Start date must be lesser than end date.")

        return self.env.ref('bbis_attendance_temp.monthly_attendance_report').report_action(self, data=self.read()[0])
