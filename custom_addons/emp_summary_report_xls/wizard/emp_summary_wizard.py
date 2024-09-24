# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class EmpSummaryWizard(models.TransientModel):
    _name = 'emp.summary.wizard'

    @api.model
    def start_month(self):
        now = fields.Datetime.from_string(fields.Date.today())
        return now - timedelta(days=30)

    start_date = fields.Date(string="Start Date", default=start_month)
    end_date = fields.Date(string="End Date", default=fields.Date.today())

    #@api.multi
    def print_report(self):
        employee_ids = self.env['hr.employee'].browse(self.env.context.get('active_ids'))
        if not employee_ids:
            raise ValidationError(_('Please select emplyee'))

        data = {
            'employee_ids': employee_ids.ids,
            'start_date' : self.start_date,
            'end_date' : self.end_date
        }
        return self.env.ref('emp_summary_report_xls.emp_summary_xlsx').with_context(discard_logo_check=True).report_action(self, data=data)