# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date

class HrHolidays(models.Model):
    _inherit = "hr.holidays"

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        bal_ticket = 0.0
        bal_leave = 0.0
        if self.employee_id:
            bal_ticket = sum(self.employee_id.mapped('ticket_allocation_ids').mapped('amount'))
            bal_leave = self.employee_id.remaining_leaves
        self.balance_leave = bal_leave
        self.balance_available = bal_ticket

    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    illness_type = fields.Char('Type of Illness')
    add_zip = fields.Char('Zip', change_default=True)
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    is_certificate = fields.Selection([('yes', 'Yes'),('no', 'No')] , default='yes', string='Medical Certificate')
    contact_no = fields.Char('Contact No')
    duty_date = fields.Date(string="Duty Date")
    balance_available = fields.Float(string="Balance Tickets")
    balance_leave = fields.Float(string="Balance Leaves")
    ticket_eligibility = fields.Selection([('yes', 'Yes'),('no', 'No')], default='no', string='Ticket Eligibility')
    attachment_id = fields.Binary(string='Certificates')
    file_name = fields.Char('Filename')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'HOD Approval'),
        ('validate1', 'HR Approval'),
        ('refuse', 'Refused'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
            help="The status is set to 'To Submit', when a leave request is created." +
            "\nThe status is 'To Approve', when leave request is confirmed by user." +
            "\nThe status is 'Refused', when leave request is refused by manager." +
            "\nThe status is 'Approved', when leave request is approved by manager.")
