# -*- coding: utf-8 -*-
import datetime
from odoo import fields, models, api, exceptions, _
from odoo.exceptions import ValidationError,UserError
date_format = "%Y-%m-%d"

class ResCompany(models.Model):
    _inherit = "res.company"

    fianace_signature = fields.Binary(string="Fianance Manager Sign")


class HrLeaveBalance(models.Model):
    _name = 'hr.leave.balance'
    _description = "Hr Leave Balance"

    other_leave_id = fields.Many2one('other.settlements')
    total = fields.Float(string="Total")
    balance = fields.Float(string="Balance")
    daily_wage = fields.Float(string="Daily Wage")
    calculation = fields.Float(string="Calculation")

class HrFlightTicket(models.Model):
    _name = 'hr.flight.ticket'
    _description = "Flight Ticket"

    total = fields.Float(string="Total")
    destination = fields.Char(string="Destination",)
    journey_date = fields.Date(string="Journey Date")
    other_ticket_id = fields.Many2one('other.settlements')

class HrOtherGratuity(models.Model):
    _name = 'hr.other.gratuity'
    _description = "Flight Ticket"

    total = fields.Float(string="Total")
    daily_wage = fields.Float(string="Daily Wage")
    worked_years = fields.Integer(string="Service Duration")
    calculation = fields.Float(string="Calculation")
    other_settlement_id = fields.Many2one('other.settlements')
    gratuity_id  = fields.Many2one('hr.gratuity')

    @api.onchange('gratuity_id')
    def onchange_employee(self):
        if self.gratuity_id:
            self.daily_wage = self.gratuity_id.daily_wage
            self.worked_years = self.gratuity_id.worked_years 
            self.calculation = self.gratuity_id.calculation
            self.total = self.gratuity_id.gratuity_amount 

class OtherSettlements(models.Model):
    _name = 'other.settlements'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Settlement"

    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validated'), ('approve', 'Approved'), ('cancel', 'Cancelled')], default='draft', track_visibility='onchange')
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_name = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_dept = fields.Many2one('hr.department', string='Department')
    employee_job_id = fields.Many2one('hr.job', string='Job Tittle')
    gratuity_ids = fields.One2many('hr.other.gratuity', 'other_settlement_id')
    leave_ids = fields.One2many('hr.leave.balance', 'other_leave_id')
    ticket_ids = fields.One2many('hr.flight.ticket', 'other_ticket_id')
    joined_date = fields.Date(string="Joined Date")
    last_date = fields.Date(string="Last Working Date")
    worked_years = fields.Integer(string="Service Duration")
    notice_period = fields.Integer(string="Notice Period")
    leave_balance = fields.Float(string="Leave Balance")
    notice_period_amount = fields.Float(string="Notice Period Amount")
    allowance = fields.Char(string="Dearness Allowance", default=0)
    total_payable_amount = fields.Float(string="Total Payable Amount", compute="_total_payable_amount")
    basic_salary = fields.Float(string="Basic Salary", required=True, default=0)
    last_month_salary = fields.Integer(string="Last Salary", required=True, default=0)
    gratuity_amount = fields.Integer(string="Gratuity Payable", required=True, default=0, readony=True, help=("Gratuity is calculated based on the equation Last salary * Number of years of service * 15 / 26 "))
    ticket_allowance = fields.Selection([('yes', 'Yes'), ('no', 'No')], default="no")
    type_of_contract = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], default='unlimited')
    reason = fields.Selection([('resign', 'Resignation'), ('terminate', 'Terminate'), ('retirement', 'Retirement')], string="Type of Sepration", required="True", default='retirement')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)


    @api.depends('gratuity_ids', 'leave_ids', 'ticket_ids', 'notice_period_amount')
    def _total_payable_amount(self):
        for rec in self:
            gratual_amount = sum(rec.gratuity_ids.mapped('total'))
            leave_amount = sum(rec.leave_ids.mapped('total'))
            ticket_amount = sum(rec.ticket_ids.mapped('total'))
            total = gratual_amount  + leave_amount + ticket_amount + rec.notice_period_amount
            rec.total_payable_amount = total

    # assigning the sequence for the record
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('other.settlements')
        return super(OtherSettlements, self).create(vals)

    # Check whether any Settlement request already exists
    @api.onchange('employee_name')
    def check_request_existence(self):
        for rec in self:
            if rec.employee_name:
                settlement_request = self.env['other.settlements'].search([('employee_name', '=', rec.employee_name.id), ('state', 'in', ['draft', 'validate', 'approve'])])
                if settlement_request:
                    raise ValidationError(_('A settlement request is already processed for this employee'))

    #@api.multi
    def validate_function(self):
        # calculating the years of work by the employee
        not_same_employee  = self.gratuity_ids.filtered(lambda x: self.employee_name and x.gratuity_id.employee_name and self.employee_name != x.gratuity_id.employee_name.employee_id)
        if not_same_employee:
            raise UserError(_('Gratuity employee and settlement employee must be same'))
        worked_years = int(datetime.datetime.now().year) - int(self.joined_date.split('-')[0])
        if worked_years >= 1:
            self.worked_years = worked_years
            cr = self._cr  # find out the correct  date of last salary of  employee
            query = """select amount from hr_payslip_line psl 
                       inner join hr_payslip ps on ps.id=psl.slip_id
                       where ps.employee_id="""+str(self.employee_name.id)+\
                       """and ps.state='done' and psl.code='NET' 
                       order by ps.date_from desc limit 1"""
            cr.execute(query)
            data = cr.fetchall()
            self.last_month_salary = data[0][0] if data else 0.0
            amount = ((self.last_month_salary + int(self.allowance)) * int(worked_years) * 15) / 26
            self.gratuity_amount = round(amount) if self.state == 'approve' else 0
            self.write({'state': 'validate'})
        else:
            self.write({'state': 'draft'})
            self.worked_years = worked_years
            raise exceptions.except_orm(_('Employee Working Period is less than 1 Year'),
                                  _('Only an Employee with minimum 1 years of working, will get the Settlement advantage'))
        self.employee_name.active = False


    def approve_function(self):
        if not self.allowance.isdigit() :
            raise ValidationError(_('Allowance value should be numeric !!'))
        self.write({'state': 'approve'})
        amount = ((self.last_month_salary + int(self.allowance)) * int(self.worked_years) * 15) / 26
        self.gratuity_amount = round(amount) if self.state == 'approve' else 0

    def cancel_function(self):
        self.write({'state': 'cancel'})

    def draft_function(self):
        self.write({'state': 'draft'})

    @api.onchange('employee_name')
    def onchange_employee(self):
        if self.employee_name:
            self.employee_dept = self.employee_name.department_id and self.employee_name.department_id.id 
            self.employee_job_id = self.employee_name.job_id and self.employee_name.job_id.id 
            self.joined_date = self.employee_name.joining_date
            self.last_date = self.employee_name.resign_date