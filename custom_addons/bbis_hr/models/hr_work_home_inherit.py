from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import math


class HRWorkHomeInherit(models.Model):
    _inherit = 'hr.work.home'
    _description = 'Work From Home'
    _order = 'create_date desc'

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid)], limit=1)

    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, readonly=True,
                                  states={'draft': [('readonly', False)], 'submit': [('readonly', False)]},
                                  default=_default_employee, track_visibility='onchange')
    from_date = fields.Datetime(string="From Date", default=fields.Datetime.now)
    to_date = fields.Datetime(string="To Date", default=fields.Datetime.now)
    department_id = fields.Many2one(related='employee_id.department_id', string='Department')
    job_id = fields.Many2one(related='employee_id.job_id', string='Job Position')
    job_date = fields.Date(related='employee_id.joining_date', string='Job Date')
    user_id = fields.Many2one(related='employee_id.parent_id', string="Manager")

    # _sql_constraints = [
    #     ('type_value',
    #      "CHECK( (employee_id IS NULL))",
    #      "The employee of this request is missing. Please make sure that your user login is linked to an employee."),
    # ]

    @api.depends('from_date', 'to_date')
    def _get_day(self):
        for rec in self:
            diff = 0.0
            from_date = fields.Datetime.from_string(rec.from_date)
            to_date = fields.Datetime.from_string(rec.to_date)
            if from_date and to_date:
                diff = to_date - from_date
            rec.no_of_days = math.ceil(diff.days + float(diff.seconds) / 86400)

    def _get_main_approvals(self):
        hr = self.env['hr.employee'].search([('job_id.name', '=', 'HR and Admin Manager')], limit=1)
        ceo = self.env['hr.employee'].search([('job_id.name', '=', 'CEO')], limit=1)

        # raise errors if no hr and ceo
        if not hr:
            raise UserError(_('There is no HR and Admin Manager Position set to employee.'))
        if not ceo:
            raise UserError(_('There is no CEO position is set.'))

        # raise errors if hr and ceo doesn't have related user
        if not hr.user_id:
            raise UserError(_('Please set the related user for HR in Employee screen.'))
        if not ceo.user_id:
            raise UserError(_('Please set the related user for CEO in Employee screen.'))

        return {"hr": hr, "ceo": ceo}

    def button_confirm(self):
        # do not allow if no of days is equal to zero
        if self.no_of_days <= 0:
            raise UserError(_('Sorry, the number of days is 0. Please make sure to add correct date and time.'))

        # get manager user
        manager = self.employee_id.parent_id

        if manager:
            manager_partner = manager.user_id.partner_id

            # show error if there's no user login added to manager
            if not manager_partner:
                raise ValidationError("Sorry, there's no related user login added to %s." % manager.name)

            self.work_from_home_request(manager_partner.id, manager_partner.name, 'requester')
            self.write({'state': 'confirm'})
            self.message_post("Request has been submitted.")

            # send email to officer
            officer = self.employee_id.coach_id
            officer_partner = self.employee_id.coach_id.user_id.partner_id
            if officer:
                self.work_from_home_request(officer_partner.id, officer.name, 'officer')

        else:
            # since there's no manager, approved it automatically for hr approval
            approvals = self.get_main_approvals()
            hr_user, hr_name = approvals['hr'].user_id, approvals['hr'].name
            self.write({'state': 'mngr_approved'})
            self.message_post("Request has been approved by the manager.")

            # if current user is hr, do not send email
            if self.env.uid != hr_user.id:
                self.work_from_home_request(hr_user.partner_id.id, hr_name, 'requester')

    def mngr_approval(self):
        """
        Make sure to allow only manager, HR and CEO for manager approval.
        In case there's no manager, proceed in updating and sending for hr approval
        """

        manager = self.employee_id.parent_id
        approvals = self.get_main_approvals()
        hr = approvals['hr']
        ceo = approvals['ceo']

        # using the current user, do not allow updating if it's not user id of manager, hr and ceo
        if self.env.uid not in (manager.user_id.id, hr.user_id.id, ceo.user_id.id):
            raise UserError(_('Sorry! You have no permission to approve this entry.'))

        # since the next approval is hr, there's no need to send an email
        if self.env.uid != hr.user_id.id:
            self.work_from_home_request(hr.user_id.partner_id.id, hr.name, 'requester')

        # proceed updating
        self.write({'state': 'mngr_approved'})
        self.message_post("Request has been approved by the manager.")

    def hr_approved(self):
        approvals = self.get_main_approvals()
        hr_approve_id = approvals['hr']
        ceo_approve_id = approvals['ceo']

        if hr_approve_id.user_id.id == self.env.uid:
            self.write({'state': 'hr_approved'})
            self.message_post("Request has been approved by the HR.")
            self.work_from_home_request(ceo_approve_id.user_id.partner_id.id, ceo_approve_id.name, 'hr_approve')
        else:
            raise UserError(_('You have no permission to approve this entry.'))

    #@api.multi
    def ceo_approved(self):
        approvals = self.get_main_approvals()
        hr_approve_id = approvals['hr']
        ceo_approve_id = approvals['ceo']
        emp = self.employee_id

        if ceo_approve_id.user_id.id == self.env.uid:
            self.write({'state': 'ceo_approved'})
            self.message_post("Request has been approved by the CEO.")

            # send email to hr
            self.work_from_home_request(hr_approve_id.user_id.partner_id.id, hr_approve_id.name, 'ceo_approve')

            # send only if there's employee user id
            emp_partner_id = self.get_employee_partner_id()
            if emp_partner_id:
                self.work_from_home_request(emp_partner_id, emp.name, 'ceo_approve')

    #@api.multi
    def action_refuse(self):
        approvals = self.get_main_approvals()
        hr = approvals['hr']
        refused_user = self.env.user.name
        emp = self.employee_id

        # Checking if the login user and the requester is same. Then throw a message.
        if self.env.uid == emp.user_id.id:
            raise UserError(_('You have no permission to refuse this entry.'))

        self.write({'state': 'refused'})
        self.message_post("The State Tag is changed to Refuse state")

        # send email to hr only but do not send if hr is the one who refused
        if self.env.uid != hr.user_id.id:
            self.work_from_home_refuse_request(hr.user_id.partner_id.id, hr.name, refused_user, 'refused', 'hr')

        # send email to employee only if there's related user
        emp_partner_id = self.get_employee_partner_id()
        if emp_partner_id:
            self.work_from_home_refuse_request(emp_partner_id, emp.name, refused_user, 'refused', 'emp')

    def _get_employee_partner_id(self):
        """
        We will get first related user and if no entries, get the address home id
        """
        emp = self.employee_id
        return emp.user_id.partner_id.id or emp.address_home_id.id or False

    #@api.multi
    def action_reset(self):
        self.write({'state': 'draft'})

    # Mail refuse for work request from home.
    def work_from_home_refuse_request(self, next_id, next_approve, refused_user, mail_to, receive_user):
        for r in self:
            r.message_post_with_view('bbis_hr.message_work_from_home', composition_mode='mass_mail',
                                     partner_ids=[(4, next_id)], auto_delete=True, auto_delete_message=True,
                                     parent_id=False, values={'next_approve': next_approve, 'mail_to': mail_to,
                                                              'refused_user': refused_user,
                                                              'receive_user': receive_user},
                                     subtype_id=self.env.ref('mail.mt_note').id)

    # Mail to HR and CEO for the approval of work request from home.
    def work_from_home_request(self, next_id, next_approve, mail_to):
        for r in self:
            r.message_post_with_view('bbis_hr.message_work_from_home', composition_mode='mass_mail',
                                     partner_ids=[(4, next_id)], auto_delete=True, auto_delete_message=True,
                                     parent_id=False, values={'next_approve': next_approve, 'mail_to': mail_to},
                                     subtype_id=self.env.ref('mail.mt_note').id)

    # Delete the entry only if it is in draft stage.
    def unlink(self):
        for req in self:
            if req.state != 'draft':
                raise ValidationError(_('You can not delete work requests which are not in draft state'))
