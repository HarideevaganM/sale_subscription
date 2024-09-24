# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

class end_services_benfits(models.Model):
    _name = 'hr.payslip'
    _inherit =  'hr.payslip', 'hr.contract'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    from_date = fields.Datetime(srting="From Date", required=False)
    to_date = fields.Datetime(srting="To Date", required=False)
    work_years = fields.Integer(string='Work Years',readonly=True,compute ='_compute_working')

    #@api.one
    def _compute_working(self):
       from_date = False
       if self.from_date:

        from_date = datetime.strptime(self.from_date, '%Y-%m-%d %H:%M:%S')
        dToday = datetime.now().date()
        self.work_years =  dToday.year - from_date.year
       return self.work_years


