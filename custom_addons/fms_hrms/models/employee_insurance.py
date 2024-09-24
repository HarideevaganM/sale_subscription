# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil import relativedelta
from odoo import models, fields, api, _


class EmployeeInsurance(models.Model):
    _name = 'hr.insurance'
    _description = 'HR Insurance'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    policy_id = fields.Many2one('insurance.policy', string='Policy', required=True)
    amount = fields.Float(string='Policy Amount', required=True)
    sum_insured = fields.Float(string="Sum Insured", required=True)
    policy_coverage = fields.Selection([('monthly', 'Monthly'), ('yearly', 'Yearly')],
                                       required=True, default='monthly',
                                       string='Policy Coverage',)
    date_from = fields.Date(string='Date From',
                            default=time.strftime('%Y-%m-%d'), readonly=True)
    date_to = fields.Date(string='Date To',   readonly=True,
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    state = fields.Selection([('active', 'Active'),
                              ('expired', 'Expired'), ],
                             default='active', string="State",compute='get_status')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)

    def get_status(self):
        current_datetime = datetime.now()
        for i in self:
            from_date = datetime.strptime(str(i.date_from), '%Y-%m-%d')
            to_date = datetime.strptime(str(i.date_to), '%Y-%m-%d')
            if from_date <= current_datetime <= to_date:
                i.state = 'active'
            else:
                i.state = 'expired'

    @api.constrains('policy_coverage')
    @api.onchange('policy_coverage')
    def get_policy_period(self):
        if self.policy_coverage == 'monthly':
            self.date_to = str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]
        if self.policy_coverage == 'yearly':
            self.date_to = str(datetime.now() + relativedelta.relativedelta(months=+12))[:10]


class InsuranceRuleInput(models.Model):
    _inherit = 'hr.payslip'

    # insurance_amount = fields.Float("Insurance amount", compute='get_inputs')

    def get_inputs(self, contract_ids, date_from, date_to):
        """This Compute the other inputs to employee payslip."""
        res = super(InsuranceRuleInput, self).get_inputs(contract_ids, date_from, date_to)
        contract_obj = self.env['hr.contract']
        for i in contract_ids:
            if contract_ids[0]:
                emp_id = contract_obj.browse(i[0].id).employee_id
                for result in res:
                    if emp_id.deduced_amount_per_month != 0 and result.get('code') == 'INSUR':
                        result['amount'] = emp_id.deduced_amount_per_month
        return res


class InsurancePolicy(models.Model):
    _name = 'insurance.policy'

    name = fields.Char(string='Name', required=True)
    note_field = fields.Html(string='Comment')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
