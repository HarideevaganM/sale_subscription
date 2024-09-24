# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime


class Hr(models.Model):
    _inherit='hr.employee'

    overtime = fields.Boolean(string='Overtime?')


class HrHolidays(models.Model):
    _inherit='hr.holidays'

    select_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string="Month")


class HrPayslip(models.Model):
    _inherit='hr.payslip'

    no_of_days = fields.Float('Number of Days', compute='get_total_month_days')

    # to get total month days
    @api.depends('no_of_days')
    def _get_total_month_days(self):
        d1 = datetime.strptime(self.date_from, '%Y-%m-%d')
        d2 = datetime.strptime(self.date_to, '%Y-%m-%d')
        total_days = str((d2 - d1).days + 1)
        self.no_of_days = total_days