# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class BiometricAttendanceWizard(models.TransientModel):
    _name = 'biometric.attendance.wizard'
    _description = 'Biometric Attendance Wizard'

    def default_biometric(self):
        return self.env['biometric.device'].browse(self._context.get('active_id'))

    name = fields.Many2one('biometric.device', required=True, default=default_biometric)
    branch = fields.Many2one(related="name.branch")
    firmware = fields.Char(related="name.firmware")
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
                              ], string="Month", default=datetime.now().month, required=True)
    year = fields.Integer(string="Year", default=datetime.now().year, required=True)

    def download_attendance(self):
        self.ensure_one()
        self.name.download_attendance(self.month, self.year)
