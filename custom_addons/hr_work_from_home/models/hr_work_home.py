# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date

class ProposedSheduleDetails(models.Model):
    _name = "proposed.schedule.details"

    days = fields.Selection([
            ('Sunday', 'Sunday'),
            ('Monday', 'Monday'),
            ('Tuesday', 'Tuesday'),
            ('Wednesday', 'Wednesday'),
            ('Thursday', 'Thursday'),
            ('Friday', 'Friday'),
            ('Saturday', 'Saturday'),
            ],string='Days')
    start_time = fields.Float(string="Start Time")
    end_time = fields.Float(string="End Time")
    work_home_id = fields.Many2one('hr.work.home', string='Work From Home')

class ResCompany(models.Model):
    _inherit = "res.company"

    emp_signature =  fields.Binary(string='Employee’s Signature')
    manager_signature = fields.Binary(string='Dep’t. Head / Manager ‘s Signature')
    hr_signature = fields.Binary(string="HR Department Manager’s Signature")

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    work_home_ids = fields.One2many('hr.work.home', 'employee_id', string="Home Works", readonly=1)
    ticket_allocation_ids = fields.One2many('hr.ticket.request', 'employee_id', string="Tickets" , readonly=1)

class HrWorkHome(models.Model):
    _name = "hr.work.home"
    _rec_name = "employee_id"
    _inherit = ['mail.thread']

    @api.depends('from_date', 'to_date')
    def _get_day(self):
        for rec in self:
            diff = 0.0
            from_date = fields.Date.from_string(rec.from_date)
            to_date = fields.Date.from_string(rec.to_date)
            if from_date and to_date:
                diff = (to_date - from_date).days
            rec.no_of_days = diff

    employee_id = fields.Many2one('hr.employee', string="Name")
    job_id = fields.Many2one('hr.job', 'Job Position')
    job_date = fields.Date(string="Job Date")
    department_id = fields.Many2one('hr.department', 'Department')
    user_id = fields.Many2one('hr.employee', string="Manager")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    no_of_days = fields.Integer(string="No of Days", compute="_get_day")
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    add_zip = fields.Char('Zip', change_default=True)
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char(string="Phone")
    leave_type = fields.Selection([
            ('paid', 'Paid'),
            ('unpaid', 'Unpaid'),
            ('others', 'Others'),
            ], string='Leave Type', default='paid')
    resign = fields.Char(string="Description")
    reason_work_from_home = fields.Text()
    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirm', 'Submit'),
            ('mngr_approved', 'Manager Approved'),
            ('hr_approved', 'HR Approved'),
            ('ceo_approved', 'Ceo Approved'),
            ('refused', 'Refuse'),
            ], string='State', default="draft")
    schedule_ids = fields.One2many('proposed.schedule.details', 'work_home_id', string="Schedule Details")
    is_negatively = fields.Selection([('yes', 'Yes'),('no', 'No')], default="no")
    is_workload = fields.Selection([('yes', 'Yes'),('no', 'No')], default="no")
    is_practice = fields.Selection([('yes', 'Yes'),('no', 'No')], default="no")
    is_request = fields.Selection([('approved', 'Approved'),('denied', 'Denied')], default="approved")
    considerations = fields.Text()

    @api.onchange('employee_id')
    def onchange_account_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id and self.employee_id.job_id.id
            self.user_id = self.employee_id.parent_id and self.employee_id.parent_id.id
            self.job_date = self.employee_id.joining_date
            self.department_id = self.employee_id.department_id and self.employee_id.department_id.id


    def button_confirm(self):
        self.write({'state': 'confirm'})

    @api.onchange('state_id')
    def onchange_state_id(self):
        for record in self:
            if record.state_id:
                record.country_id = record.state_id.country_id or False
            else:
                record.country_id = False

    @api.onchange('country_id')
    def onchange_cont_id(self):
        state_ids = []
        if self.country_id:
            return {'domain': {'state_id': [('country_id', '=', self.country_id.id)]}}
        else:
            return {'domain': {'state_id': []}}

    #@api.multi
    def ceo_approved(self):
        self.write({'state' : 'ceo_approved'})
