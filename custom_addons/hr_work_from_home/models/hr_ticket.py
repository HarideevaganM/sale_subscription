from odoo import api, fields, models, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

class HrTicketAllocation(models.Model):
    _name = "hr.ticket.allocation"

    def button_confirm(self):
        self.write({'state': 'confirm'})

    def button_reset(self):
        self.write({'state': 'draft'})

    def button_approved(self):
        self.write({'state' : 'approved'})

    @api.depends('request_ids')
    def _get_bal_amount(self):
        for rec in self:
            rec.balance = rec.total_amount -  sum(rec.request_ids.mapped('amount'))

    @api.depends('amount', 'credit')
    def _get_total_amount(self):
        for rec in self:
            rec.total_amount =  rec.amount + rec.credit

    @api.onchange('from_date', 'to_date' , 'employee_id')
    def onchange_name(self):
        name = ''
        if self.from_date or self.to_date:
            name = ('%s to %s') %(self.from_date, self.to_date)
        if self.employee_id:
            name = ('%s - %s') %(name, self.employee_id.name)
        self.name = name
            
    name = fields.Char(string='Name')
    from_date = fields.Date(string="From Date", default=fields.Date.today())
    to_date = fields.Date(string="To Date", default=fields.Date.today())
    amount = fields.Float(string='Amount')
    credit = fields.Float(string='Credit')
    note = fields.Text(string='Notes')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    request_ids = fields.One2many('hr.ticket.request', 'allocation_id', string="Requests")
    balance = fields.Float(string='Balance', compute='_get_bal_amount')
    total_amount = fields.Float(string='Total Amount', compute='_get_total_amount', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirm', 'Confirm'),
            ('approved', 'Approved'),
            ],string='State', default="draft")

class HrTicketRequest(models.Model):
    _name = "hr.ticket.request"

    def button_submit(self):
        self.write({'state': 'submit'})

    def button_reset(self):
        self.write({'state': 'draft'})

    def button_confirm(self):
        self.write({'state': 'confirm'})
    
    @api.onchange('date' , 'employee_id')
    def onchange_employee_id(self):
        if self.date and self.employee_id:
            end_date = fields.Date.from_string(self.date) + relativedelta(months=12)
            name = ('%s  - Ticket request from - %s to  %s') %(self.employee_id.name, self.date , end_date)
            self.name = name

    #@api.one
    def create_je_for_ticket(self):
        """This Approve the employee ticket request from accounting department."""
        tickets_ids = self.search([('employee_id', '=', self.employee_id.id), ('id', '!=', self.id), ('state', '=', 'ceo_approved')])
        current_year = datetime.strptime(self.date, '%Y-%m-%d').date().year
        for ticket in tickets_ids:
            existing_year = datetime.strptime(ticket.date, '%Y-%m-%d').date().year
            if current_year == existing_year:
                raise UserError(_('Ticket can be requested once in a year for each employee'))
        # Check require data
        if not self.company_id.credit_account or not self.company_id.debit_account or not self.company_id.journal_id:
            raise UserError(_('Warning', "You must set debit & credit accounts and journal in company "))
        if self.amount <= 0:
            raise UserError(_('Warning', 'You must enter the ticket amount'))
        # Create JE
        move_obj = self.env['account.move']
        timenow = fields.Date.today()
        line_ids = []
        debit_sum = 0.0
        credit_sum = 0.0
        for request in self:
            amount = request.amount
            request_name = request.employee_id.name
            reference = request.allocation_id.name if request.allocation_id else request.name
            journal_id = request.company_id.journal_id
            move = {
                'narration': 'Ticket Request Of : %s  on  %s' %(request_name, request.date),
                'ref': reference,
                'journal_id': journal_id and journal_id.id,
                'date': timenow,
                'state': 'draft',
            }

            debit_account_id = request.company_id.debit_account
            credit_account_id = request.company_id.credit_account

            if debit_account_id:
                debit_line = (0, 0, {
                    'name': request_name,
                    'account_id': debit_account_id and debit_account_id.id,
                    'journal_id': journal_id and journal_id.id,
                    'date': timenow,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'currency_id': request.company_id.currency_id.id,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            if credit_account_id:
                credit_line = (0, 0, {
                    'name': request_name,
                    'account_id': credit_account_id and credit_account_id.id,
                    'journal_id': journal_id and journal_id.id,
                    'date': timenow,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'currency_id': request.company_id.currency_id.id,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            move.update({'line_ids': line_ids})
            move_obj.create(move)
        return True

    def send_mail_ticket(self):
        group_id_list = []
        ir_model_data = self.env['ir.model.data']
        ceo_group = self.env['res.groups'].browse(ir_model_data.get_object_reference('hr_work_from_home', 'group_fms_ceo')[1]).users[0]
        group_id_list.append(ir_model_data.get_object_reference('account', 'group_account_manager')[1])
        users_email = ",".join([user.email for user in self.env['res.groups'].browse(group_id_list).users if user.email])
        template_id = ir_model_data.get_object_reference('hr_work_from_home', 'email_request_ticket_contract')[1]
        template = self.env['mail.template'].browse(template_id)
        template.write({
            'email_to': users_email or '',
            'body_html':
                'Hello, Employee ticket request is approved by CEO and draft journal entiry is also created. Please check for further process </br> %s </br></br>Thank You,</p>'% ceo_group.name if ceo_group else ''
        })
        template.send_mail(self.id, force_send=True)
        return True

    def button_ceo_approved(self):
        self.create_je_for_ticket()
        self.send_mail_ticket()
        self.write({'state': 'ceo_approved'})
        return True

    name = fields.Char(string='Name')
    note = fields.Text(string='Notes')
    amount = fields.Float(string='Amount')
    destination = fields.Char(string='Destination')
    date = fields.Date(string="Date", default=fields.Date.today())
    allocation_id = fields.Many2one('hr.ticket.allocation', string="Allocation")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection([('draft', 'Draft'),('submit', 'Submit'),('confirm', 'Confirm'), ('ceo_approved', 'CEO Approved')],string='State', default="draft")