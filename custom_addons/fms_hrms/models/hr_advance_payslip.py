# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models


class SalaryRuleInput(models.Model):
    _inherit = 'hr.payslip'

    def get_inputs(self, contract_ids, date_from, date_to):
        """This Compute the other inputs to employee payslip."""
        contract_obj = self.env['hr.contract']
        res = super(SalaryRuleInput, self).get_inputs(contract_ids, date_from, date_to)
        emp_id = contract_obj.browse(contract_ids.id).employee_id
        adv_salary = self.env['salary.advance'].search([('employee_id', '=', emp_id.id)])
        for adv_obj in adv_salary:
            current_date = datetime.strptime(str(date_from), '%Y-%m-%d').date().month
            existing_date = datetime.strptime(str(adv_obj.date), '%Y-%m-%d').date().month
            if current_date == existing_date:
                amount = adv_obj.advance
                for result in res:
                    if adv_obj.state == 'approve' and amount != 0 and result.get('code') == 'SAR':
                        result['amount'] = amount
        return res
