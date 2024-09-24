# -*- coding: utf-8 -*-
from odoo import api, fields, models,_
from num2words import num2words

class HR(models.Model):
    _inherit = "hr.employee"

    salary = fields.Float(string="Monthly Salary", compute='_compute_total_salsary')
    joining_date = fields.Date(string="Joining  Date")

    def _compute_total_salsary(self):
        for rec in self:
            contract_id = self.env['hr.contract'].search([('employee_id', '=', rec.id)], limit=1)
            if contract_id and contract_id.wage:
                rec.salary = (contract_id.wage + contract_id.total_allowance + contract_id.hra) - contract_id.total_deduction

    def numtoword(self):
        for rec in self:
            value = num2words(rec.salary)
            return value