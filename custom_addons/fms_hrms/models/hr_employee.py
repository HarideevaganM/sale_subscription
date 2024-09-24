# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp

HOURS_PER_DAY = 8


# Fields inherited in Hr Employee #
class HREmployee(models.Model):
    _inherit = "hr.employee"

    # Compute document count ##
    # @api.multi
    def _document_count(self):
        for each in self:
            each.document_count = len(self.env['hr.employee.document'].sudo().search([('employee_ref', '=', each.id)]))
            # each.document_count = len(document_ids)

    # @api.multi
    def _loan_count(self):
        for each in self:
            each.loan_count = len(self.env['hr.loans'].sudo().search([('employee_ref', '=', each.id)]))
            # each.loan_count = len(loan_ids)

    # Attached document return function ##
    # @api.multi
    def document_view(self):
        self.ensure_one()
        domain = [
            ('employee_ref', '=', self.id)]
        return {
            'name': _('Documents'),
            'domain': domain,
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            # 'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'context': "{'default_employee_ref': %s}" % self.id
        }

    # @api.multi
    def loan_view(self):
        self.ensure_one()
        domain = [
            ('employee_ref', '=', self.id)]
        return {
            'name': _('Loans'),
            'domain': domain,
            'res_model': 'hr.loans',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            # 'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_ref': '%s'}" % self.id
        }

    # @api.multi
    def send_birthday_wish(self):
        today_date = datetime.today().date()
        for employee in self.env['hr.employee'].search([]):
            if employee.birthday:
                emp_birthdate = datetime.strptime(str(employee.birthday), '%Y-%m-%d').date()
                if today_date.day == emp_birthdate.day and today_date.month == emp_birthdate.month:
                    template_id = self.env.ref('fl_birthday_wish.email_birthday_wishes_employee_template')
                    template_id.send_mail(employee.id, force_send=True)

    def mail_notification(self):
        """Sending mail notification for ID,Passport, joining date and birthday wishes"""
        now = datetime.now() + timedelta(days=1)
        probationary = datetime.now().date()-relativedelta(months=6)
        date_now = now.date()
        match = self.search([])
        for i in match:
            if i.id_expiry_date:
                exp_date = fields.Date.from_string(i.id_expiry_date) - timedelta(days=14)
                if date_now >= exp_date:
                    mail_content = "  Hello  " + i.name + ",<br>Your ID " + i.identification_id + "is going to expire on " + \
                                   str(i.id_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('ID-%s Expired On %s') % (i.identification_id, i.id_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()
        match1 = self.search([])
        for i in match1:
            if i.passport_expiry_date:
                exp_date1 = fields.Date.from_string(i.passport_expiry_date) - timedelta(days=180)
                if date_now >= exp_date1:
                    mail_content = "  Hello  " + i.name + ",<br>Your Passport " + i.passport_id + "is going to expire on " + \
                                   str(i.passport_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('Passport-%s Expired On %s') % (i.passport_id, i.passport_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()
            if i.joining_date:
                joining_exp_date = fields.Date.from_string(i.joining_date) - relativedelta(years=1)
                if date_now <= joining_exp_date:
                    mail_content = "  Hello  " + i.name
                    main_content = {
                        'subject': _('One year of joining'),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()
            if i.joining_date:
                probationary_exp = fields.Date.from_string(i.joining_date) -relativedelta(months=6)
                if date_now == probationary_exp:
                    mail_content = "  Hello  " + i.name
                    main_content = {
                        'subject': _('Probationary Period'),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()

    age = fields.Integer("Age")
    employee_id = fields.Char("Employee ID")
    children = fields.Integer("Children")
    bank_number_id = fields.Char("Bank Account No")
    bank_name = fields.Many2one("bank.name", "Bank Name")
    branch_name = fields.Many2one("branch.name", "Branch Name")
    labour_card = fields.Char("Labour Card Number")
    labour_card_date = fields.Date("Labour Card Expiry Date")
    medical_card = fields.Char("Medical Card Number")
    personal_mobile = fields.Char(string='Mobile', store=True)
    private_email = fields.Char(string="Private Email", groups="hr.group_hr_user", store=True)
    phone = fields.Char(string="Private Phone",groups="hr.group_hr_user", store=True)
    # emergency_contact = fields.One2many('hr.emergency.contact', 'employee_obj', string='Emergency Contact')
    joining_date = fields.Date(string='Joining Date')
    id_expiry_date = fields.Date(string='Expiry Date', help='Expiry date of Identification ID')
    passport_expiry_date = fields.Date(string='Expiry Date', help='Expiry date of Passport ID')
    id_attachment_id = fields.Many2many('ir.attachment', 'id_attachment_rel', 'id_ref', 'attach_ref',
                                        string="Attachment", help='You can attach the copy of your Id')
    passport_attachment_id = fields.Many2many('ir.attachment', 'passport_attachment_rel', 'passport_ref', 'attach_ref1',
                                              string="Attachment",
                                              help='You can attach the copy of Passport')
    fam_ids = fields.One2many('hr.employee.family', 'employee_id', string='Family', help='Family Information')
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
    country_address_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Payroll Nationality', ondelete='restrict')
    eid_number = fields.Char("EID No")
    uid_number = fields.Char("UID No")
    visa_issue_date = fields.Date("Visa Issue Date")
    # Document ##
    document_count = fields.Integer(compute='_document_count', string='# Documents')
    loan_count = fields.Integer(compute='_loan_count',string='# Loans')
    loan_amt = fields.Float(string='# Loans', related="")
    document_line = fields.One2many('hr.employee.document', 'employee_ref',string='# Documents')
    # Insurance ##
    insurance_percentage = fields.Float(string="Company Percentage ")
    deduced_amount_per_month = fields.Float(string="Salary deduced per month", compute="get_deduced_amount")
    deduced_amount_per_year = fields.Float(string="Salary deduced per year", compute="get_deduced_amount")
    insurance = fields.One2many('hr.insurance', 'employee_id', string="Insurance",
                                domain=[('state', '=', 'active')])

    # Computes deduction amount for Insurance ##
    def get_deduced_amount(self):
        current_datetime = datetime.now()
        for emp in self:
            ins_amount = 0
            for ins in emp.insurance:
                from_date = datetime.strptime(str(ins.date_from), '%Y-%m-%d')
                to_date = datetime.strptime(str(ins.date_to), '%Y-%m-%d')
                if from_date < current_datetime < to_date:
                    if ins.policy_coverage == 'monthly':
                        ins_amount = ins_amount + (ins.amount*12)
                    else:
                        ins_amount = ins_amount + ins.amount
            emp.deduced_amount_per_year = ins_amount-((ins_amount*emp.insurance_percentage)/100)
            emp.deduced_amount_per_month = emp.deduced_amount_per_year/12

    # Calculates age using DOB ##
    @api.onchange('birthday')
    def onchange_birthday(self):
        if self.birthday:
            date1 = datetime.strptime(str(self.birthday), "%Y-%m-%d").date()
            date2 = date.today()
            self.age = relativedelta(date2, date1).years
            if self.age <= 18:
                raise ValidationError(_('Invalid Date of Birth. Please enter a valid DATE OF BIRTH'))


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    age = fields.Integer("Age", related='employee_id.age')
    bank_number_id = fields.Char("Bank Account No", related='employee_id.bank_number_id')
    bank_name = fields.Many2one("bank.name", "Bank Name", related='employee_id.bank_name')
    branch_name = fields.Many2one("branch.name", "Branch Name", related='employee_id.branch_name')
    labour_card = fields.Char("Labour Card Number", related='employee_id.labour_card')
    labour_card_date = fields.Date("Labour Card Expiry Date", related='employee_id.labour_card_date')
    medical_card = fields.Char("Medical Card Number", related='employee_id.medical_card')
    personal_mobile = fields.Char(string='Mobile', store=True, related='employee_id.personal_mobile')
    joining_date = fields.Date(string='Joining Date', related='employee_id.joining_date')
    id_expiry_date = fields.Date(string='Expiry Date', help='Expiry date of Identification ID', related='employee_id.id_expiry_date')
    passport_expiry_date = fields.Date(string='Expiry Date', help='Expiry date of Passport ID', related='employee_id.passport_expiry_date')
    street = fields.Char(related='employee_id.street')
    street2 = fields.Char(related='employee_id.street2')
    zip = fields.Char(change_default=True, related='employee_id.zip')
    city = fields.Char(related='employee_id.city')
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',related='employee_id.state_id')
    country_address_id = fields.Many2one('res.country', string='Country', ondelete='restrict', related='employee_id.country_address_id')
    country_id = fields.Many2one('res.country', string='Payroll Nationality', ondelete='restrict', related='employee_id.country_id')
    eid_number = fields.Char("EID No", related='employee_id.eid_number')
    uid_number = fields.Char("UID No", related='employee_id.uid_number')
    visa_issue_date = fields.Date("Visa Issue Date", related='employee_id.visa_issue_date')
    loan_amt = fields.Float(string='# Loans', related='employee_id.loan_amt')
    insurance_percentage = fields.Float(string="Company Percentage", related='employee_id.insurance_percentage')


# Manages Employee Documents With Expiry Notifications ##
class HrEmployeeDocument(models.Model):
    _name = 'hr.employee.document'
    _description = 'HR Employee Documents'

    def mail_reminder(self):
        """Sending document expiry notification to employees."""
        now = datetime.now() + timedelta(days=1)
        date_now = now.date()
        match_ids = self.search([])
        group_id_list = []
        ir_model_data = self.env['ir.model.data']
        group_id_list.append(self.env.ref('hr.group_hr_user').id)
        users_email = ",".join([user.email for user in self.env['res.groups'].browse(group_id_list).users if user.email and user.email == 'sharthy@fms-tech.com'])
        if users_email:
            for i in match_ids.filtered(lambda x: x.expiry_date and x.employee_ref):
                exp_date = fields.Date.from_string(i.expiry_date) - relativedelta(weeks=1)
                if date_now >= exp_date:
                    mail_content = "  Hello  " + str(i.employee_ref.name) + ",<br>Your Document " + i.name + "is going to expire on " + str(i.expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('Document-%s of %s Expired On %s') % (i.name, i.employee_ref.name, i.expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': users_email,
                    }
                    self.env['mail.mail'].create(main_content).send()

    @api.constrains('expiry_date')
    def check_expr_date(self):
        """checking document expiry date for user warning"""
        for each in self:
            if each.expiry_date:
                exp_date = fields.Date.from_string(each.expiry_date)
                if exp_date < date.today():
                    raise UserError('Your Document Is Expired.')

    @api.onchange("document_name")
    def onchange_required_document(self):
        if self.document_name:
            self.name = self.document_name.document_number
            self.mandatory = True
            if self.mandatory == False:
                raise ValidationError(_('Kindly attach the Required Document'))

    name = fields.Char(string='Document Number', required=True,copy=False, help='You can give your Document number.')
    description = fields.Text(string='Description', copy=False)
    expiry_date = fields.Date(string='Expiry Date', copy=False)
    employee_ref = fields.Many2one('hr.employee', invisible=1, copy=False)
    doc_attachment_id = fields.Many2many('ir.attachment', 'doc_attach_rel', 'doc_id', 'attach_id3', string="Attachment",
                                         help='You can attach the copy of your document', copy=False)
    issue_date = fields.Date(string='Submitted Date', default=fields.datetime.now(), copy=False)
    mandatory = fields.Boolean('Mandatory')
    document_name = fields.Many2one('employee.checklist', string='Document name', help='Type of Document', required=True)


# ir attachment for Employee document ##
# class HrEmployeeAttachment(models.Model):
#     _inherit = 'ir.attachment'
#
#     doc_attach_rel = fields.Many2many('hr.employee.document', 'doc_attachment_id', 'attach_id3', 'doc_id',
#                                       string="Attachment", invisible=1)


class BankName(models.Model):
    _name = 'bank.name'

    name = fields.Char(string="Name")


class BranchName(models.Model):
    _name = 'branch.name'

    name = fields.Char(string="Name")


# class HrEmployeeContractName(models.Model):
#     """This class is to add emergency contact table"""
#     _name = 'hr.emergency.contact'
#     _description = 'HR Emergency Contact'
#
#     number = fields.Char(string='Number', help='Contact Number')
#     relation = fields.Char(string='Contact', help='Relation with employee')
#     employee_obj = fields.Many2one('hr.employee', invisible=1)
# access_hr_emergency_contact_user,hr.emergency.contact.user,fms_hrms.model_hr_emergency_contact,base.group_user,1,1,1,0
# access_hr_emergency_contact_manager,hr.emergency.contact.manager,fms_hrms.model_hr_emergency_contact,hr.group_hr_manager,1,1,1,1

class HrEmployeeFamilyInfo(models.Model):
    """Table to keep employee family information"""
    _name = 'hr.employee.family'
    _description = 'HR Employee Family'

    member_name = fields.Char(string='Name', related='employee_ref.name', store=True)
    employee_ref = fields.Many2one(string="Is Employee",
                                   help='If family member currently is an employee of same company, '
                                        'then please tick this field',
                                   comodel_name='hr.employee')
    employee_id = fields.Many2one(string="Employee", help='Select corresponding Employee', comodel_name='hr.employee',
                                  invisible=1)
    relation = fields.Selection([('father', 'Father'),
                                 ('mother', 'Mother'),
                                 ('daughter', 'Daughter'),
                                 ('son', 'Son'),
                                 ('wife', 'Wife')], string='Relationship', help='Relation with employee')
    member_contact = fields.Char(string='Contact No', related='employee_ref.personal_mobile', store=True)


# Hr Leave management ##
# class HrHolidayStatusInherit(models.Model):
#     _inherit = 'hr.holidays.status'
#
#     leave_code = fields.Char("Code")

#~ 
#~ class HrHolidaysInherit(models.Model):
    #~ _inherit = 'hr.holidays'

    #~ date_from = fields.Date('Start Date', readonly=True, index=True, copy=False,
        #~ states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    #~ date_to = fields.Date('End Date', readonly=True, copy=False,
        #~ states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')


    #~ @api.onchange('holiday_status_id')
    #~ def onchange_holiday_status_id(self):
        #~ """ Validation to avail eligible Leave """
        #~ emp_id=self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        #~ contract_id=self.env['hr.contract'].search([])
        #~ now = datetime.now().date()-relativedelta(months=6)
        #~ if self.holiday_status_id.leave_code == "AL":
            #~ date_joined = datetime.strptime(emp_id.joining_date , '%Y-%m-%d')
            #~ today = now.strftime('%d-%m-%Y')
            #~ joined_date = date_joined.strftime('%d-%m-%Y')
            #~ if joined_date < today:
                #~ raise ValidationError(_('You are not eligible to avail this Leave type'))
        #~ for con_id in contract_id:
            #~ if self.holiday_status_id.leave_code == "SL":
                #~ if self.number_of_days_temp <= 14 :
                    #~ con_id.wage = con_id.wage
                #~ elif self.number_of_days_temp >= 15 :
                    #~ con_id.wage = (con_id.wage)*0.75
                #~ elif self.number_of_days_temp >= 28 :
                    #~ con_id.wage = (con_id.wage)*0.50
                #~ elif self.number_of_days_temp >= 42 :
                    #~ con_id.wage = (con_id.wage)*0.25
                #~ elif self.number_of_days_temp >= 70 :
                    #~ con_id.wage = 0
                #~ else:
                    #~ con_id.wage = 0


class HrSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    visa_validity = fields.Boolean("Get email notification on employee VISA expiration",
                                    help="""Allow to define from how many days before to start alert
                                    Employee and other configured addresses will get the notification emails each day.""")
    limit_amount = fields.Integer("from", size=10)

    def get_default_visa_details(self,fields):
        ir_values = self.env['ir.values']
        visa_validity = ir_values.get_default('sale.config.settings', 'visa_validity')
        limit_amount = ir_values.get_default('sale.config.settings', 'limit_amount')
        return {'visa_validity': visa_validity, 'limit_amount': limit_amount}


class ReminderVisa(models.Model):
    _inherit = 'hr.contract'

    #~ @api.one
    #~ @api.depends('wage','hra')
    #~ def _hra_compute(self):
        #~ self.hra = self.wage*0.10

    # @api.one
    @api.depends('mobile_allowance','fuel_allowance','allowance1','allowance2','allowance3','allowance4')
    def _compute_allowance(self):
        for rec in self:
            rec.total_allowance = rec.mobile_allowance + rec.fuel_allowance + rec.allowance1 + rec.allowance2 + rec.allowance3 + rec.allowance4

    # @api.one
    @api.depends('deduction1','loan_deduction','deduction2','deduction3','deduction4','deduction5','deduction6','deduction7')
    def _compute_deduction(self):
        for rec in self:
            rec.total_deduction = rec.loan_deduction + rec.deduction1 + rec.deduction2 + rec.deduction3 + rec.deduction4 + rec.deduction5 + rec.deduction6 + rec.deduction7

    # @api.one
    @api.depends('earnings1','earnings2','earnings3','earnings4','earnings5','earnings6')
    def _compute_earnings(self):
        for rec in self:
            rec.total_earnings = rec.earnings1 + rec.earnings2 + rec.earnings3 + rec.earnings4 + rec.earnings5 + rec.earnings6

    #~ @api.one
    #~ @api.depends('gross','basic')
    #~ def _compute_gross(self):
        #~ print("CONTRACT",self.gross)
        #~ self.gross = self.basic+self.total_allowance

    mobile_allowance = fields.Float("Mobile Allowance",digits=dp.get_precision('Payroll'))
    hra = fields.Float("HRA",digits=dp.get_precision('Payroll'))
    #~ gross = fields.Float("Gross",compute='_compute_gross')
    basic = fields.Float("Basic",digits=dp.get_precision('Payroll'))
    fuel_allowance = fields.Float("Fuel Allowance",digits=dp.get_precision('Payroll'))
    allowance1 = fields.Float("Car Allowance",digits=dp.get_precision('Payroll'))
    allowance2 = fields.Float("Overtime Allowance",digits=dp.get_precision('Payroll'))
    allowance3 = fields.Float("Site Allowance",digits=dp.get_precision('Payroll'))
    allowance4 = fields.Float("Other Allowances",digits=dp.get_precision('Payroll'))
    total_allowance = fields.Float("Total Allowance", compute='_compute_allowance',digits=dp.get_precision('Payroll'))
    deduction1 = fields.Float("Advance Deduction",digits=dp.get_precision('Payroll'))
    deduction2 = fields.Float("ROP Fines",digits=dp.get_precision('Payroll'))
    deduction3 = fields.Float("Other Deduction",digits=dp.get_precision('Payroll'))
    deduction4 = fields.Float("Deduction 4",digits=dp.get_precision('Payroll'))
    deduction5 = fields.Float("Deduction 5",digits=dp.get_precision('Payroll'))
    deduction6 = fields.Float("Deduction 6",digits=dp.get_precision('Payroll'))
    deduction7 = fields.Float("Deduction 7",digits=dp.get_precision('Payroll'))
    total_deduction = fields.Float("Total Deduction", compute='_compute_deduction',digits=dp.get_precision('Payroll'))
    earnings1 = fields.Float("Earnings 1",digits=dp.get_precision('Payroll'))
    earnings2 = fields.Float("Earnings 2",digits=dp.get_precision('Payroll'))
    earnings3 = fields.Float("Earnings 3",digits=dp.get_precision('Payroll'))
    earnings4 = fields.Float("Earnings 4",digits=dp.get_precision('Payroll'))
    earnings5 = fields.Float("Earnings 5",digits=dp.get_precision('Payroll'))
    earnings6 = fields.Float("Earnings 6",digits=dp.get_precision('Payroll'))
    total_earnings = fields.Float("Total Earnings", compute='_compute_earnings',digits=dp.get_precision('Payroll'))
    wage = fields.Monetary('Basic', digits=(16, 2), required=True, track_visibility="onchange", help="Employee's monthly gross wage.")
    paid_leave = fields.Char("Paid Leave")
    nationality = fields.Char(string='Nationality')

    # @api.onchange('nationality')
    # def set_caps(self):
    #     val = str(self.nationality)
    #     self.nationality = val.upper()

    def mail_reminder_visa(self):
        i = self.env['res.config.settings'].search([],limit=1, order='id desc')
        x = self.env['res.config.settings'].browse(i and i[0])
        if x.visa_validity != False:
            tommorrow = datetime.now()+timedelta(days=x.limit_amount)
            date_tommorrow = tommorrow.date()
            issue_obj = self.env['hr.contract']
            match = issue_obj.search([('visa_expire', '<=', date_tommorrow)])
            for i in match:
                browse_hr_contract = issue_obj.browse(i)
                browse_id = browse_hr_contract.employee_id
                self.send_email_employee(browse_id.id, browse_id.name, browse_hr_contract.visa_expire,
                                         date_tommorrow)
        else:
            pass

    def send_email_employee(self, emp_id, emp_name, exp_date, no_days):
        email_template_obj = self.env['mail.template']
        template_ids = email_template_obj.search([('name', '=', 'Visa Alert Email For Employees')])
        template_brwse = email_template_obj.browse(template_ids)
        email_to = self.pool.get('hr.employee').browse(emp_id).work_email
        body_html = "  Hello  "+emp_name+",<br>Your visa is going to expire on "+str(exp_date) +\
                    ". Please renew it before expiry date"
        if template_ids:
            values = email_template_obj.generate_email(template_ids[0], emp_id)
            values['subject'] = template_brwse.subject
            values['email_to'] = email_to
            values['body_html'] = body_html
            values['body'] = body_html
            values['email_from'] = template_brwse.email_from
            values['res_id'] = False
            mail_mail_obj = self.env['mail.mail']
            msg_id = mail_mail_obj.create(values)
        if msg_id:
            mail_mail_obj.send([msg_id])
        return True


class LoanView(models.Model):
    _name = 'hr.loans'

    name = fields.Many2one("hr.employee", "Employee Name", default=lambda self: self.env.user.id )
    department_id = fields.Many2one("hr.department", "Department", related='name.department_id', readonly=True)
    job_id = fields.Many2one("hr.job", "Job position", related='name.job_id', readonly=True)
    request_date = fields.Date("Loan request date", default=fields.Date.today())
    confirm_date = fields.Date("Loan Confirmed date")
    loan_amt = fields.Float("Loan Amount")
    employee_ref = fields.Many2one('hr.employee', invisible=1, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'Submitted'),
        ('waiting_approval_2', 'Waiting Approval'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    @api.onchange('loan_amt')
    def onchange_loan_amt(self):
        loan_obj =self.env["hr.employee"].search([('id','=', self.name.id)])
        if loan_obj:
            loan_obj.update({'loan_amt':self.loan_amt})

    # @api.multi
    def action_refuse(self):
        return self.write({'state': 'refuse'})

    # @api.multi
    def action_submit(self):
        self.write({'state': 'waiting_approval_1'})

    # @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    # @api.multi
    def action_approve(self):
        self.write({'state': 'waiting_approval_2'})

    def action_double_approve(self):
        self.write({'state': 'approve', 'confirm_date': datetime.now()})
