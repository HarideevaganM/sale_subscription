# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrHolidays(models.Model):
    _inherit = 'hr.holidays'

    leave_balance_count = fields.Char(string="Remaining Leave Days")

    @api.onchange('holiday_status_id')
    def onchange_leave_balance(self):
        if self.employee_id and self.holiday_status_id:
            data_days = self.holiday_status_id.get_days(self.employee_id.id)
            result = data_days.get(self.holiday_status_id.id, {})
            self.leave_balance_count = result.get('remaining_leaves', 0)