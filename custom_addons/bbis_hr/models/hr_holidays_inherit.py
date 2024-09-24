import calendar

from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import UserError, AccessError, ValidationError
import math
from dateutil.relativedelta import relativedelta


class accrual_process_inherit(models.Model):
    """inherited holidays screen for adding the pattern of leave approvals."""

    _inherit = "hr.holidays"

    next_approver_id = fields.Many2one('hr.employee', status='Next Approver', compute='_get_next_approver', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Officer Approved'),
        ('validate2', 'Manager Approved'),
        ('validate1', 'HR Approved'),
        ('refuse', 'Refused'),
        ('validate', 'CEO Approved'),
    ], string='Status', readonly=False, store=True, default='draft',
        help="The status is set to 'To Submit', when a leave request is created." +
             "\nThe status is 'Submitted', when leave request is submit by first user." +
             "\nThe status is 'Office Approve', when leave request is confirmed by first approver." +
             "\nThe status is 'Manager Approve', when leave request is Approved by Manager approver." +
             "\nThe status is 'HR Approve', when leave request is Approved by HR." +
             "\nThe status is 'CEO Approve', when leave request is Approved by CEO." +
             "\nThe status is 'Refused', when leave request is refused by manager.")

    @api.model
    def _get_employee_names(self):
        final_list = []
        employees_list = self.env['hr.employee'].search([('active', '=', True)])
        for r in employees_list:
            emp_value = (r.name, r.name)
            final_list.append(emp_value)
        return final_list

    delegate_to = fields.Selection(selection='get_employee_names', string="Delegate Work To")
    is_processed = fields.Integer(string="Processed Flag")
    requested_date = fields.Datetime(string="Requested Date", default=fields.Datetime.now, readonly=True)
    fields_hide = fields.Boolean(string='Hide', compute="_compute_hide", default=False)
    joining_date = fields.Date(related='employee_id.joining_date', string='Joining Date', readonly=True)
    job_id = fields.Many2one(related='employee_id.job_id', string='Job Position', readonly=True)
    officer = fields.Many2one(related='employee_id.coach_id', string='Department Officer', readonly=True)
    manager = fields.Many2one(related='employee_id.parent_id', string='Department Manager', readonly=True)
    report_note_hr = fields.Text('HR Comments')
    report_note_ceo = fields.Text('CEO Comments')
    is_unused_leave = fields.Boolean('Unused Leaves')
    last_approval_date = fields.Datetime(default=fields.Datetime.now, readonly=True)

    @api.model
    def create(self, vals):
        res = super(accrual_process_inherit, self).create(vals)

        # apply this only if holiday type is remove
        if self.type == 'remove':
            # only allow applying leaves to other team member within their respective department
            # if res.create_uid.employee_ids.department_id != res.employee_id.department_id:
            #     raise ValidationError("Sorry! You can only apply other leaves within your respective department.")

            # we will not allow officer to apply leaves on their manager
            if res.create_uid.employee_ids.parent_id == res.employee_id:
                raise ValidationError("Sorry! Your not allowed to apply leaves for your manager.")

        return res

    @api.depends('holiday_status_id')
    def _compute_hide(self):
        if self.holiday_status_id.leave_code == 'SL':
            self.fields_hide = True
        else:
            self.fields_hide = False

    # @api.onchange('delegate_to')
    # def _get_delegate_employee(self):
    #     if self.department_id and self.delegate_to:
    #         employee = self.env['hr.employee'].search([('name', '=', self.delegate_to)])
    #         if self.department_id.id != employee.department_id.id:
    #             raise UserError(_('Sorry, you can only delegate your work within your respective department.'))

    #@api.multi
    def _get_current_status(self):
        status = ''
        if self.state == 'draft':
            status = 'To Submit'
        if self.state == 'submit':
            status = 'Submitted'
        elif self.state == 'confirm':
            status = 'Office Approval'
        elif self.state == 'validate2':
            status = 'Manager Approval'
        elif self.state == 'validate1':
            status = 'HR Approval'
        elif self.state == 'validate':
            status = 'CEO Approval'
        elif self.state == 'refuse':
            status = 'Refused'
        return status

    # For getting the next status.
    @api.onchange('employee_id')
    def _get_next_approver(self):
        for r in self:
            if not r.next_approver_id:
                r.state = 'draft'
            if self.employee_id and self.env.uid != r.employee_id.user_id.id and self.type == 'remove':
                return {'value': {}, 'warning': {'title': 'Message', 'message': 'You are applying the leave for '
                                                                                + self.employee_id.name}}

    def send_user_notification(self, rec, values):
        """ Send user notifications for approvals """
        # Add base link
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        values['base_url'] = base_url

        # add title to next approval
        partner_id = self.env['res.partner'].browse(values.get('next_id'))
        # do not send if email from and email to are the same
        if self.env.user.email_formatted == partner_id.email_formatted:
            return

        body = self.env.ref('bbis_hr.message_hr_holidays').render(values=values)
        mail_values = {
            'email_from': self.env.user.email_formatted,
            "email_to": partner_id.email_formatted,
            'subject': rec.display_name,
            'body_html': body,
            'auto_delete': True,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

    def send_user_notification_no_partner(self, rec, values):
        """ Send user notifications for approvals """
        # Add base link
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        values['base_url'] = base_url

        body = self.env.ref('bbis_hr.message_hr_holidays').render(values=values)
        mail_values = {
            'email_from': self.env.user.email_formatted,
            "email_to": values.get("email_to"),
            'subject': rec.display_name,
            'body_html': body,
            'auto_delete': True,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

    def first_leave_request_hr_assistant(self, next_id, next_approve):
        """ The first default mail to hr assistant."""
        mail_to = 'mail_to_hr_assistant'
        for rec in self:
            rec.message_post(body="Leave request has been sent to %s." % next_approve)
            values = {'next_approve': next_approve, "mail_to": mail_to, "object": self, "next_id": next_id}
            self.send_user_notification(rec, values)

    def send_hr_override_notification(self, next_id, next_approve, holiday_id):
        """Mail to HR or Hr Assistant if the next approver will not approve the request in one day."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        hr_holidays = self.env['hr.holidays'].search([('id', '=', holiday_id)])
        partner_id = self.env['res.partner'].browse(next_id)
        for rec in hr_holidays:
            rec.message_post(body="Leave request has been sent to %s." % next_approve)
            values = {"object": rec, 'next_approve': next_approve, "next_id": next_id, "base_url": base_url}
            # do not send if email from and email to are the same
            if self.env.user.email_formatted == partner_id.email_formatted:
                return

            body = self.env.ref('bbis_hr.hr_override_notification').render(values=values)
            mail_values = {
                'email_from': self.env.user.email_formatted,
                "email_to": partner_id.email_formatted,
                'subject': 'Leave Request - Override',
                'body_html': body,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

    def send_leave_request_mail(self, next_id, next_approve):
        """ Mail to the next approval """
        # Do not send notification to the current user if it's the same to the next approval.
        # This can be a higher employee applied leaves on behalf of that employee

        if self.env.user.partner_id.id == next_id:
            return

        for rec in self:
            rec.message_post(body="Leave request has been sent to %s for approval." % next_approve)

            values = {"object": self, 'next_approve': next_approve, "next_id": next_id}
            self.send_user_notification(rec, values)

    def send_leave_delegate_mail(self, next_id, next_approve):
        """Mail to the delegated employee"""
        mail_to = 'delegate'
        for rec in self:
            if rec.next_approver_id.name != rec.delegate_to:
                rec.message_post(
                    body="Your leave request has been sent to %s as the delegated employee." % rec.delegate_to)
                values = {"object": self, 'next_approve': next_approve, "next_id": next_id, 'mail_to': mail_to}
                self.send_user_notification(rec, values)

    def send_leave_approval_mail(self, next_id, next_approve):
        """Approved Mail from CEO"""

        mail_to = 'ceo_approve'
        for rec in self:
            values = {"object": self, 'next_approve': next_approve, "next_id": next_id, 'mail_to': mail_to,
                      'requester': rec.employee_id.name}
            self.send_user_notification(rec, values)

    def leave_approval_mail_user(self, next_id, approved_employee):
        """Mail to requester after approved by each officer."""

        mail_to = 'requester'
        for rec in self:
            if rec.is_processed != 1 and rec.type == 'remove':
                values = {"object": self, 'next_approve': approved_employee, "next_id": next_id, 'mail_to': mail_to,
                          'requester': rec.employee_id.name}
                self.send_user_notification(rec, values)

    def leave_refuse_mail_user(self, next_id, approved_employee):
        """ Mail to requester after refused by one of the approvals """
        mail_to = 'refuse'
        mail_receiver = 'employee'
        for r in self:
            # only mail user if they are requesting for leave
            if r.is_processed != 1 and r.type == 'remove':
                r.message_post(body="Leave refusal has been sent to the employee.")
                values = {"object": self, 'next_approve': approved_employee, "next_id": next_id, 'mail_to': mail_to,
                          'mail_receive': mail_receiver, 'refuser': self.env.user.name, 'requester': r.employee_id.name}
                self.send_user_notification(r, values)

    def leave_refuse_mail_hr(self, next_id, hr_employee):
        """Mail to HR after refused by one of the approvals."""

        mail_to = 'refuse'
        mail_receiver = 'hr'
        for r in self:
            # only mail user if they are requesting for leave
            if r.is_processed != 1 and r.type == 'remove':
                r.message_post(body="Leave refusal has been sent to HR.")
                values = {"object": self, "next_id": next_id, 'mail_to': mail_to, 'mail_receive': mail_receiver,
                          'refuser': self.env.user.name, 'requester': hr_employee}

                self.send_user_notification(r, values)

    #@api.multi
    def _get_date_diff(self, last_approval_date):
        """Function to get the difference of request date and current date."""
        day_diff = 0
        current_date = datetime.now()
        if last_approval_date:
            request_date = datetime.strptime(last_approval_date, "%Y-%m-%d %H:%M:%S")
            difference = current_date - request_date
            day_diff = difference.days
        return day_diff

    #@api.multi
    def action_submit(self):
        """Function for submit the leave request."""
        for holiday in self:
            # for allocation request, we don't need to follow approvals. Immediately approved but make sure
            user = self.env.user
            is_hr_manager = user.has_group('fms_access_group.group_profile_hr_manager')
            if holiday.type == "add" or holiday.is_processed == 1:
                # make sure only user with hr manager access can approve allocation request
                if not is_hr_manager:
                    raise ValidationError("Sorry! Only HR manager has the permission to submit allocation request.")
                holiday.state = 'validate'

            # check if there's date from and date to and the type is remove.
            if holiday.type == 'remove' and not (holiday.date_from or holiday.date_to):
                raise ValidationError("Please make sure to add the duration of your leave.")

            approvals = self.get_main_approvals()
            hr_approve_id = approvals['hr']
            ceo_approve_id = approvals['ceo']
            hr_assistant_id = approvals['hr_assistant']

            delegate_user = False
            if holiday.delegate_to:
                delegate_user = self.env['hr.employee'].search([('name', '=', holiday.delegate_to)], limit=1)

            if holiday.type == "remove":
                # if it is processed automatically, do not proceed to approvals
                if holiday.is_processed:
                    # make sure only user with hr manager access can approve allocation request
                    if not is_hr_manager:
                        raise ValidationError("Sorry! Only HR manager has the permission to submit allocation request.")
                    # immediately cut the methods here
                    return True

                # check if duty date is lesser than date to
                if holiday.duty_date and holiday.date_to:
                    to_date = datetime.strptime(holiday.date_to, "%Y-%m-%d %H:%M:%S")
                    duty_date = datetime.strptime(holiday.duty_date, "%Y-%m-%d")

                    if duty_date < to_date.replace(hour=0, minute=0, second=0):
                        raise UserError(_('The duty date should be after the leave end date.'))

                # If officer not assigned.
                if not holiday.employee_id.coach_id:
                    # If manager not assigned.
                    if not holiday.employee_id.parent_id:
                        # The requester is HR.
                        if holiday.employee_id.id == hr_approve_id.id:
                            holiday.write({'state': 'validate1', 'first_approver_id': holiday.employee_id.id,
                                           'next_approver_id': ceo_approve_id.id})
                            self.send_leave_request_mail(ceo_approve_id.user_id.partner_id.id, ceo_approve_id.name)
                        else:
                            # Else mail send to HR and status become manager approved.
                            if not self.is_hr_manager_on_leave(hr_approve_id):
                                self.process_hr_notification(hr_approve_id)
                            else:
                                holiday.write({'state': 'validate2', 'first_approver_id': holiday.employee_id.id,
                                               'next_approver_id': hr_assistant_id.id})

                    # If the manager is assigned.
                    else:
                        if holiday.employee_id.parent_id:
                            if not holiday.employee_id.parent_id.user_id:
                                raise UserError(
                                    _('Please set the related user for Department Manager in Employee screen.'))
                        # The requester and the creator of the request are not same.
                        if holiday.user_id.id != self.env.uid:
                            # Check whether the manager of the requester and the creator user are the same.
                            if holiday.employee_id.parent_id.user_id.id == self.env.uid:
                                # Then the request move to HR.
                                self.process_hr_notification(hr_approve_id)
                            else:
                                holiday.write({'state': 'confirm', 'first_approver_id': holiday.employee_id.id,
                                               'next_approver_id': holiday.employee_id.parent_id.id})
                                self.send_leave_request_mail(holiday.employee_id.parent_id.user_id.partner_id.id,
                                                             holiday.employee_id.parent_id.name)
                        # If the requester and the creator are same.
                        else:
                            holiday.write({'state': 'confirm', 'first_approver_id': holiday.employee_id.id,
                                           'next_approver_id': holiday.employee_id.parent_id.id})
                            self.send_leave_request_mail(holiday.employee_id.parent_id.user_id.partner_id.id,
                                                         holiday.employee_id.parent_id.name)
                else:
                    if holiday.employee_id.coach_id:
                        # Check the coach id is assigned for the requester.
                        if not holiday.employee_id.coach_id.user_id:
                            raise UserError(
                                _('Please set the related user for Department Officer in Employee screen.'))

                    if holiday.user_id.id != self.env.uid:
                        # If the requester and the creator of the request are not same.
                        if holiday.employee_id.coach_id.user_id.id == self.env.uid:
                            # If the officer and the creator of the request are same update the status to confirm.
                            holiday.write({'state': 'confirm', 'first_approver_id': holiday.employee_id.coach_id.id,
                                           'next_approver_id': holiday.employee_id.parent_id.id})
                            # Sending the mail to manager.
                            self.send_leave_request_mail(holiday.employee_id.parent_id.user_id.partner_id.id,
                                                         holiday.employee_id.parent_id.name)
                        else:
                            # If the creator and the officer not same. Then the status update to submit.
                            holiday.write({'state': 'submit', 'first_approver_id': holiday.employee_id.id,
                                           'next_approver_id': holiday.employee_id.coach_id.id})
                            # Sending mail to officer.
                            self.send_leave_request_mail(holiday.employee_id.coach_id.user_id.partner_id.id,
                                                         holiday.employee_id.coach_id.name)
                    else:
                        holiday.write({'state': 'submit', 'first_approver_id': holiday.employee_id.id,
                                       'next_approver_id': holiday.employee_id.coach_id.id})
                        self.send_leave_request_mail(holiday.employee_id.coach_id.user_id.partner_id.id,
                                                     holiday.employee_id.coach_id.name)

                # Send mail to HR Assistant.
                self.first_leave_request_hr_assistant(hr_assistant_id.user_id.partner_id.id, hr_assistant_id.name)

                if holiday.delegate_to:
                    # select either user or private home address
                    partner = delegate_user.user_id.partner_id if delegate_user.user_id else delegate_user.address_home_id
                    if partner:
                        self.send_leave_delegate_mail(partner.id, holiday.delegate_to)

    #@api.multi
    def action_confirm(self):
        """Function for Officer approval."""
        for holiday in self:
            holiday.message_unsubscribe([holiday.employee_id.user_id.partner_id.id])
            approvals = self.get_main_approvals()
            hr_approve_id = approvals['hr']
            hr_assistant_id = approvals['hr_assistant']
            current_employee = self.env['hr.employee'].search([('id', '=', self.next_approver_id.id)], limit=1)
            next_approval_id = holiday.employee_id.parent_id.id

            # Check the HR manager is on leave.
            hr_next_approver = hr_approve_id.user_id.id
            if self.is_hr_manager_on_leave(hr_approve_id):
                hr_next_approver = hr_assistant_id.user_id.id
            if (current_employee.user_id.id == self.env.uid) or (self.env.uid == hr_next_approver):
                """the next approver and logged in user are same or the next approver not approve after 1 day the 
                request automatically goes to HR."""

                if holiday.employee_id.parent_id.user_id.id == holiday.create_uid.id:
                    """If manager is the creator means after officer approval the status update to 
                    validate2 and the mail send to HR"""
                    self.process_hr_notification(hr_approve_id)
                else:
                    holiday.write({'state': 'confirm', 'first_approver_id': current_employee.id,
                                   'next_approver_id': next_approval_id, 'last_approval_date': datetime.now()})
                    if holiday.employee_id.parent_id.user_id:
                        self.send_leave_request_mail(holiday.employee_id.parent_id.user_id.partner_id.id,
                                                     holiday.employee_id.parent_id.name)
                    else:
                        raise UserError(_('Please set the related user for Department Manager in Employee screen.'))

                self.approval_mail_to_user()
            else:
                raise UserError(_('You have no permission to approve this entry'))

    def approval_mail_to_user(self):
        """Sending th mail to the requester after each approval."""
        for holiday in self:
            if not holiday.employee_id.user_id:
                if holiday.employee_id.address_home_id:
                    requester_user_id = holiday.employee_id.address_home_id
                else:
                    requester_user_id = self.create_uid.partner_id
            else:
                requester_user_id = holiday.employee_id.user_id.partner_id
            if requester_user_id:
                self.leave_approval_mail_user(requester_user_id.id, self.env.user.name)

    def _check_state_access_right(self, vals):
        if vals.get('state') and vals['state'] not in ['draft', 'submit', 'confirm', 'cancel'] and \
                not self.env['res.users'].has_group('hr_holidays.group_hr_holidays_user'):
            return False
        return True

    #@api.multi
    def action_approve(self):
        """Function for Manager approval."""
        for holiday in self:
            holiday.message_unsubscribe(
                [holiday.employee_id.user_id.partner_id.id,
                 holiday.employee_id.coach_id.user_id.partner_id.id])
            current_employee = self.env['hr.employee'].search([('id', '=', holiday.next_approver_id.id)],
                                                              limit=1)
            approvals = self.get_main_approvals()
            hr_approve_id = approvals['hr']
            hr_assistant_id = approvals['hr_assistant']

            # Check the HR manager is on leave.
            hr_next_approver = hr_approve_id.user_id.id
            if self.is_hr_manager_on_leave(hr_approve_id):
                hr_next_approver = hr_assistant_id.user_id.id

            if (current_employee.user_id.id == self.env.uid) or (self.env.uid == hr_next_approver):
                self.process_hr_notification(hr_approve_id)
                # Sending mail to the requester.
                self.approval_mail_to_user()
            else:
                raise UserError(_('You have no permission to approve this entry'))

    #@api.multi
    def action_validate2(self):
        """Function for HR approval."""
        for holiday in self:
            holiday.message_unsubscribe([holiday.employee_id.user_id.partner_id.id,
                                         holiday.employee_id.coach_id.user_id.partner_id.id,
                                         holiday.employee_id.parent_id.user_id.partner_id.id])
            if holiday.state == 'validate2':
                current_employee = self.env['hr.employee'].search([('id', '=', holiday.next_approver_id.id)],
                                                                  limit=1)
                approvals = self.get_main_approvals()
                ceo_approve_id = approvals['ceo']
                hr_approve_id = approvals['hr']
                hr_assistant_id = approvals['hr_assistant']

                hr_next_approver = hr_approve_id.user_id.id
                # Check the HR manager is on leave.
                if self.is_hr_manager_on_leave(hr_approve_id):
                    hr_next_approver = hr_assistant_id.user_id.id

                if current_employee.user_id.id == self.env.uid or hr_next_approver == self.env.uid:
                    holiday.write({'state': 'validate1', 'next_approver_id': ceo_approve_id.id})
                    self.send_leave_request_mail(ceo_approve_id.user_id.partner_id.id, ceo_approve_id.name)
                    # Sending mail to the requester.
                    self.approval_mail_to_user()
                else:
                    raise UserError(_('You have no permission to approve this entry'))

    #@api.multi
    def action_validate(self):
        """Function for CEO approval."""
        for holiday in self:
            approvals = self.get_main_approvals()
            hr_approve_id = approvals['hr']

            holiday.message_unsubscribe([holiday.employee_id.user_id.partner_id.id,
                                         holiday.employee_id.coach_id.user_id.partner_id.id,
                                         holiday.employee_id.parent_id.user_id.partner_id.id,
                                         hr_approve_id.user_id.partner_id.id])
            if holiday.state == 'validate1':
                current_employee = self.env['hr.employee'].search([('id', '=', holiday.next_approver_id.id)], limit=1)
                if current_employee.user_id.id == self.env.uid:
                    holiday.write({'state': 'validate'})
                    if hr_approve_id.id != holiday.employee_id.id:
                        self.process_hr_notification(hr_approve_id)

                    if not holiday.employee_id.user_id:
                        if holiday.employee_id.address_home_id:
                            requester_user_id = holiday.employee_id.address_home_id
                        else:
                            requester_user_id = self.create_uid.partner_id

                            # at this point,the employee doesn't have partner id. Send manual email using employee email
                            if holiday.employee_id.work_email:
                                values = {"object": holiday,
                                          "email_to": holiday.employee_id.work_email,
                                          "next_approve": current_employee.name,
                                          "mail_to": 'requester',
                                          "requester": holiday.employee_id.name
                                          }
                                self.send_user_notification_no_partner(holiday, values=values)
                    else:
                        requester_user_id = holiday.employee_id.user_id.partner_id
                    if requester_user_id:
                        self.leave_approval_mail_user(requester_user_id.id, self.env.user.name)

                else:
                    raise UserError(_('You have no permission to approve this entry'))

    #@api.multi
    def action_refuse(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if any(holiday.state not in ['draft', 'submit', 'confirm', 'validate', 'validate1', 'validate2'] for holiday in
               self):
            raise UserError(_('Leave request must be confirmed or validated in order to refuse it...'))
        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id, 'next_approver_id': ''})
        (self - validated_holidays).write(
            {'state': 'refuse', 'second_approver_id': current_employee.id, 'next_approver_id': ''})

        emp = self.employee_id
        requester_user_id = emp.user_id.partner_id or emp.address_home_id or False

        # do not allow same user to refuse
        if emp.user_id and (emp.user_id.id == self.env.uid):
            raise ValidationError("Sorry! Your not allowed to refuse your own leave.")

        if requester_user_id and self.type == 'remove':
            self.leave_refuse_mail_user(requester_user_id.id, current_employee.name)
            approvals = self.get_main_approvals()
            hr_approve_id = approvals['hr']
            if self.employee_id != hr_approve_id:
                self.leave_refuse_mail_hr(hr_approve_id.user_id.partner_id.id, hr_approve_id.name)

        # Delete the meeting
        self.mapped('meeting_id').unlink()
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')

        # unsubscribe the employee if it is allocation so that no email will be sent during submit action
        if self.type == 'add':
            self.message_unsubscribe([self.employee_id.user_id.partner_id.id])

        if linked_requests:
            linked_requests.action_refuse()
        self._remove_resource_leave()
        self.update({'state': 'refuse'})
        return True

    #  New Changes on 05-02-2022   started
    #@api.multi
    def _get_number_of_days(self, date_from, date_to, employee_id):
        from_dt = fields.Datetime.from_string(date_from)
        to_dt = fields.Datetime.from_string(date_to)
        time_delta = to_dt - from_dt
        return math.ceil(time_delta.days) + 1

    #  New Changes on 05-02-2022   ended
    # Scheduler. Create the leave accrual entry for Annual leaves.
    #@api.multi
    def create_accruals(self):
        # get the current day and month
        # cur_day_month = (datetime.now().day, datetime.now().month)
        # last_day = calendar.monthrange(datetime.today().year, datetime.today().month)[1]
        cur_day = datetime.now().day
        cur_year = datetime.now().year
        date_from = datetime.now().replace(hour=4)
        date_to = datetime.now().replace(hour=13)

        # to be used in domain for checking if accrual is already processed2
        date_yesterday = date_from - relativedelta(days=1)
        date_tomorrow = date_to + relativedelta(days=1)
        date_yesterday_str = date_yesterday.strftime("%Y-%m-%d %H:%M:%S")
        date_tomorrow_str = date_tomorrow.strftime("%Y-%m-%d %H:%M:%S")

        # get leave types
        leave_type_obj = self.env['hr.holidays.status']
        annual_leave = leave_type_obj.search([('is_annual', '=', True)])

        holiday_obj = self.env['hr.holidays']

        # prepare data needed in sending emails
        approvals = self.get_main_approvals()
        hr = approvals['hr']
        has_record_added = False
        body_html = """<div style='font-family:Arial;font-size:10pt;'>
        <p>Dear %s,</p>
        <p>This is to notify you that new accrual leaves has been added for the following employees:</p>
        """ % hr.name

        body_html += """<table style="border-collapse:collapse; font-family:Arial;font-size:10pt;" 
        cellpadding="5" border="1"><tr><th style="background-color:#2c286c; color:white">Employee Name</th>
        <th style="background-color:#2c286c; color:white; text-align:center">No. of Days</th>
        <th style="background-color:#2c286c; color:white; text-align:center">Joining Date</th></tr>"""

        # get employee joining date
        employees = self.env['hr.employee'].search([])

        for emp in employees:
            joining_date_str = emp.joining_date

            # make sure to process only if there's joining date to avoid errors
            if joining_date_str:
                joining_date = datetime.strptime(joining_date_str, "%Y-%m-%d")
                join_day = joining_date.day
                # If joining date greater than 28 then need to process this accrual in feb like month set the day as 28.
                if join_day > 28:
                    join_day = 28

                # only run if joining day is the same to current day
                if cur_day == join_day:
                    # make sure not to add double entry. In some cases, double entry occurs when server was restarted
                    # check by employee, leave type, create date, processed leave, allocation, status
                    al_exist_domain = [('employee_id', '=', emp.id), ('state', '=', 'validate'),
                                       ('holiday_status_id', '=', annual_leave.id),
                                       ('date_from', '>', date_yesterday_str), ('date_to', '<', date_tomorrow_str),
                                       ('is_processed', '=', 1), ('type', '=', 'add'),
                                       ('number_of_days_temp', '=', annual_leave.days_per_month)]
                    annual_leave_processed_exist = holiday_obj.search(al_exist_domain)

                    if not annual_leave_processed_exist:
                        accrual_data = {
                            'name': 'Monthly Leave Allocation - %s %s' % (date_from.strftime('%B'), cur_year),
                            'state': 'validate',
                            'payslip_status': False,
                            'holiday_status_id': annual_leave.id,
                            'employee_id': emp.id,
                            'notes': 'Accrual Process Data',
                            'date_from': date_from,
                            'date_to': date_to,
                            'number_of_days_temp': annual_leave.days_per_month,
                            'requested_date': datetime.now(),
                            'meeting_id': '',
                            'type': 'add',
                            'holiday_type': 'employee',
                            'is_processed': 1
                        }

                        holiday_obj.create(accrual_data)
                        has_record_added = True
                        body_html += """<tr><td>%s</td><td align="center">%s</td><td align="center">%s</td></tr>""" % \
                                     (emp.name, annual_leave.days_per_month, joining_date.strftime("%B %d, %Y"))

        # close body html table
        body_html += '</table>'

        # send email to hr to notify for the newly added leave if there is
        if has_record_added:
            self.send_processed_leave(body_html, "New Annual Leaves Processed")

    #@api.multi
    def process_reset_leaves(self):
        # get the current day and month
        cur_day_month = (datetime.now().day, datetime.now().month)
        # get leave types
        leave_type_obj = self.env['hr.holidays.status']
        annual_leave = leave_type_obj.search([('is_annual', '=', True)])
        sick_leave = leave_type_obj.search([('leave_code', '=', 'SL')])
        unpaid_leave = leave_type_obj.search([('leave_code', '=', 'UL')])

        holiday_obj = self.env['hr.holidays']

        # prepare data needed in sending emails
        approvals = self.get_main_approvals()
        hr = approvals['hr']
        has_record_added = False
        body_html = """<div style='font-family:Arial;font-size:10pt;'>
                <p>Dear %s,</p>
                <p>This is to notify you that reset leaves has been processed for the following employees:</p>
                """ % hr.name

        body_html += """<table style="border-collapse:collapse; font-family:Arial;font-size:10pt;" 
                cellpadding="5" border="1"><tr><th style="background-color:#2c286c; color:white">Employee Name</th>
                <th style="background-color:#2c286c; color:white; text-align:center">No. of Days</th>
                <th style="background-color:#2c286c; color:white; text-align:center">Joining Date</th>
                <th style="background-color:#2c286c; color:white; text-align:center">Leave Type</th>
                <th style="background-color:#2c286c; color:white; text-align:center">Note</th></tr>"""

        # get employee joining date
        employees = self.env['hr.employee'].search([])
        for emp in employees:

            joining_date_str = emp.joining_date

            # make sure to process only if there's joining date to avoid errors
            if joining_date_str:
                joining_date = datetime.strptime(joining_date_str, "%Y-%m-%d")
                join_day = joining_date.day
                # If joining date greater than 28 then need to process this accrual in feb like month set the day as 28.
                if join_day > 28:
                    join_day = 28
                join_month = joining_date.month

                date_from = datetime.now().replace(day=join_day, month=join_month, hour=0) - relativedelta(days=1)
                date_to = date_from.replace(hour=18)

                date_from_str = date_from.strftime("%Y-%m-%d %H:%M:%S")

                if cur_day_month == (join_day, join_month):
                    # add date start filter for getting the particular year start from and to.
                    leaves_annual = holiday_obj.read_group([('employee_id', '=', emp.id), ('state', '=', 'validate'),
                                                            ('holiday_status_id', '=', annual_leave.id),
                                                            ('date_from', '<=', date_from_str)],
                                                           ['holiday_status_id', 'number_of_days'],
                                                           ['holiday_status_id'])
                    balance = leaves_annual[0]['number_of_days'] if leaves_annual else 0
                    carry_over = annual_leave.days_carry_over

                    # prepare common leave data
                    leave_common = {
                        'state': 'validate',
                        'payslip_status': False,
                        'employee_id': emp.id,
                        'date_from': date_from,
                        'date_to': date_to,
                        'meeting_id': '',
                        'holiday_type': 'employee',
                        'is_processed': 1,
                        'requested_date': datetime.now(),
                    }

                    # annual leave: only adjust leave if balance is greater than annual leave no. of days carried over
                    if float(balance) > annual_leave.days_carry_over:
                        deduct_days = balance - carry_over

                        # prepare the leaves to be deducted in annual
                        reason = 'Deduct unused annual leaves (%s days) every anniversary' % deduct_days
                        note_reason = '%s since only %d days will be carried over next year.' % (reason, carry_over)
                        annual_leave_data = {**leave_common,
                                             'type': 'remove',
                                             'name': reason,
                                             'holiday_status_id': annual_leave.id,
                                             'notes': note_reason,
                                             'number_of_days_temp': deduct_days,
                                             'number_of_days': deduct_days,
                                             'contact_no': emp.mobile_phone,
                                             'duty_date': date_to.replace(day=join_day),
                                             'is_unused_leave': True
                                             }

                        holiday_obj.create(annual_leave_data)

                        # mark that record has been added and add leave data in email
                        has_record_added = True
                        body_html += """<tr><td>%s</td><td align="center">%s</td><td align="center">%s</td><td align="center">%s</td><td>%s</td></tr>""" % \
                                     (emp.name, deduct_days, joining_date.strftime("%B %d, %Y"), annual_leave.name,
                                      reason)

                    # sick leave: reset any remaining leaves to zero then create new entry using days per year in config
                    leaves_sick = holiday_obj.read_group([('employee_id', '=', emp.id), ('state', '=', 'validate'),
                                                          ('holiday_status_id', '=', sick_leave.id),
                                                          ('date_from', '<=', date_from_str)],
                                                         ['holiday_status_id', 'number_of_days'],
                                                         ['holiday_status_id'])

                    sick_balance = float(leaves_sick[0]['number_of_days']) if leaves_sick else 0

                    # deduct unused leaves but only create deduction if there's a balance
                    if sick_balance:
                        desc = "Deduct unused sick leaves (%s days) every anniversary" % sick_balance
                        deduct_sick_leave = {**leave_common,
                                             'type': 'remove',
                                             'name': desc,
                                             'holiday_status_id': sick_leave.id,
                                             'notes': "Reset sick leave every anniversary",
                                             'number_of_days_temp': sick_balance,
                                             'contact_no': emp.mobile_phone,
                                             'duty_date': date_to.replace(day=join_day),
                                             'is_unused_leave': True,
                                             }

                        holiday_obj.create(deduct_sick_leave)

                        # mark that record has been added and add leave data in email
                        has_record_added = True
                        body_html += """<tr><td>%s</td><td align="center">%s</td><td align="center">%s</td><td align="center">%s</td><td>%s</td></tr>""" % \
                                     (emp.name, sick_balance, joining_date.strftime("%B %d, %Y"), sick_leave.name, desc)

                    # after resetting old balance, create a new balance based on days per year
                    date_from = datetime.now().replace(day=join_day, month=join_month, hour=4)
                    date_to = date_from.replace(hour=13)
                    date_to_str = date_to.strftime("%Y-%m-%d %H:%M:%S")

                    # make sure not to add double entry. In some cases, double entry occurs when server was restarted
                    # check by employee, leave type, create date, processed leave, allocation, status
                    sl_exist_domain = [('employee_id', '=', emp.id), ('state', '=', 'validate'),
                                       ('holiday_status_id', '=', sick_leave.id),
                                       ('date_from', '>', date_from_str), ('date_to', '<=', date_to_str),
                                       ('is_processed', '=', 1), ('type', '=', 'add'),
                                       ('number_of_days_temp', '=', sick_leave.days_per_year)]
                    sick_leave_processed_exist = holiday_obj.search(sl_exist_domain)

                    # only add new sick leave if nothing has been processed yet to avoid duplicate
                    if not sick_leave_processed_exist:
                        desc = "Add new %s sick leaves every anniversary" % sick_leave.days_per_year
                        new_sick_leave = {**leave_common,
                                          'type': 'add',
                                          'name': desc,
                                          'holiday_status_id': sick_leave.id,
                                          'notes': "Add sick leave every anniversary",
                                          'number_of_days_temp': sick_leave.days_per_year,
                                          'contact_no': emp.mobile_phone,
                                          'duty_date': date_to.replace(day=join_day),
                                          'date_from': date_from,
                                          'date_to': date_to,
                                          }

                        holiday_obj.create(new_sick_leave)

                        # mark that record has been added and add leave data in email
                        has_record_added = True
                        body_html += """<tr><td>%s</td><td align="center">%s</td><td align="center">%s</td><td align="center">%s</td><td>%s</td></tr>""" % \
                                     (emp.name, sick_leave.days_per_year, joining_date.strftime("%B %d, %Y"),
                                      sick_leave.name, desc)

                    # Unpaid leave:Reset any remaining leave to zero and create new entry using days per year in config.
                    leaves_unpaid = holiday_obj.read_group([('employee_id', '=', emp.id), ('state', '=', 'validate'),
                                                            ('holiday_status_id', '=', unpaid_leave.id),
                                                            ('date_from', '<=', date_from_str)],
                                                           ['holiday_status_id', 'number_of_days'],
                                                           ['holiday_status_id'])

                    unpaid_balance = float(leaves_unpaid[0]['number_of_days']) if leaves_unpaid else 0

                    # deduct unused leaves but only create deduction if there's a balance
                    if unpaid_balance > 0:
                        desc = "Deduct unused unpaid leaves (%s days) every anniversary" % unpaid_balance
                        deduct_unpaid_leave = {**leave_common,
                                               'type': 'remove',
                                               'name': desc,
                                               'holiday_status_id': unpaid_leave.id,
                                               'notes': "Reset sick leave every anniversary",
                                               'number_of_days_temp': unpaid_balance,
                                               'contact_no': emp.mobile_phone,
                                               'duty_date': date_to.replace(day=join_day),
                                               'is_unused_leave': True,
                                               }

                        holiday_obj.create(deduct_unpaid_leave)

                        # mark that record has been added and add leave data in email
                        has_record_added = True
                        body_html += """<tr><td>%s</td><td align="center">%s</td><td align="center">%s</td><td align="center">%s</td><td>%s</td></tr>""" % \
                                     (emp.name, unpaid_balance, joining_date.strftime("%B %d, %Y"), unpaid_leave.name,
                                      desc)

                    # after resetting old balance, create a new balance based on days per year
                    # make sure not to add double entry. In some cases, double entry occurs when server was restarted
                    # check by employee, leave type, create date, processed leave, allocation, status
                    ul_exist_domain = [('employee_id', '=', emp.id), ('state', '=', 'validate'),
                                       ('holiday_status_id', '=', unpaid_leave.id),
                                       ('date_from', '>', date_from_str), ('date_to', '<=', date_to_str),
                                       ('is_processed', '=', 1), ('type', '=', 'add'),
                                       ('number_of_days_temp', '=', unpaid_leave.days_per_year)]
                    unpaid_leave_processed_exist = holiday_obj.search(ul_exist_domain)

                    # only add new unpaid leave if nothing has been processed yet to avoid duplicate
                    if not unpaid_leave_processed_exist:
                        desc = "Add new %s unpaid leaves every anniversary" % unpaid_leave.days_per_year
                        new_unpaid_leave = {**leave_common,
                                            'type': 'add',
                                            'name': desc,
                                            'holiday_status_id': unpaid_leave.id,
                                            'notes': "Add unpaid leave every anniversary",
                                            'number_of_days_temp': unpaid_leave.days_per_year,
                                            'contact_no': emp.mobile_phone,
                                            'duty_date': date_to.replace(day=join_day),
                                            'date_from': date_from,
                                            'date_to': date_to,
                                            }

                        holiday_obj.create(new_unpaid_leave)

                        # mark that record has been added and add leave data in email
                        has_record_added = True
                        body_html += """<tr><td>%s</td><td align="center">%s</td><td align="center">%s</td><td align="center">%s</td><td>%s</td></tr>""" % \
                                     (emp.name, unpaid_leave.days_per_year, joining_date.strftime("%B %d, %Y"),
                                      unpaid_leave.name, desc)

        body_html += "</table>"
        if has_record_added:
            self.send_processed_leave(body_html, "New Reset Leaves Processed")

    def send_processed_leave(self, body, subject):
        """
        Send email to hr everytime an scheduler is done for Accrual Annual Leaves and Resetting Leaves
        """

        # prepare the variables needed
        user = self.env['res.users'].browse(self.env.uid)
        from_email = user.company_id.email
        approvals = self.get_main_approvals()
        hr = approvals['hr']
        hr_email = hr.user_id.partner_id.email

        # add footer
        body += """
                <br/><br/><p>Thank You,</p><p style="margin:0; color:#F05A29"><b>%s</b></p>
                <p style="color: #808080; margin:0;"><small>This is a system generated mail. No need of sending replies.</small></p>
                </div>""" % user.company_id.name

        # prepare email and send
        template_obj = self.env['mail.mail']
        template_data = {
            'subject': subject,
            'body_html': body,
            'email_from': from_email,
            'email_to': hr_email,
        }
        template_id = template_obj.create(template_data)
        template_id.send()

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for holiday in self:
            domain = [
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>=', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('type', '=', holiday.type),
                ('state', 'not in', ['cancel', 'refuse']),
                ('holiday_status_id', '=', holiday.holiday_status_id.id),
            ]
            nholidays = self.search_count(domain)
            if nholidays and self.is_processed != 1:
                raise ValidationError(_('You can not have 2 leaves that overlaps on same day!'))

    @api.constrains('state', 'number_of_days_temp', 'holiday_status_id')
    def _check_holidays(self):
        for holiday in self:
            if holiday.holiday_type != 'employee' or holiday.type != 'remove' \
                    or not holiday.employee_id or holiday.holiday_status_id.limit:
                continue

    #@api.multi
    def create_non_processed_leaves(self):
        """Function for sending the mail to hr or hr assistant if the next approver not approve the leave in one day."""
        approvals = self.get_main_approvals()
        hr_approve_id = approvals['hr']
        hr_holidays = self.env['hr.holidays'].search([('state', 'in', ('submit', 'confirm', 'validate2')),
                                                      ('type', '=', 'remove')])
        for holiday_id in hr_holidays:
            difference_days = self.get_date_diff(holiday_id.last_approval_date)
            if difference_days == 1:
                holiday_id.process_hr_notification(hr_approve_id, True)

    def is_hr_manager_on_leave(self, hr_approve_id):
        """ Check if the HR Manager is on leave"""
        now = datetime.now()
        current_date = datetime.strftime(now, "%Y-%m-%d %H:%M:%S")
        hr_vacation = self.env['hr.holidays'].search([('employee_id', '=', hr_approve_id.id),
                                                      ('state', '=', 'validate'),
                                                      ('date_from', '<=', current_date),
                                                      ('date_to', '>=', current_date)], limit=1)
        # Check in employee screen the employee is on leave.
        employee = self.env['hr.employee'].search([('id', '=', hr_approve_id.id), ('is_on_leave', '=', True)])

        return hr_vacation or employee.is_on_leave

    def process_hr_notification(self, hr_approve_id, cron_job=False):
        """Function to send the request to HR. If HR is on vacation then the request sent to HR Assistant"""
        for holiday in self:
            approvals = self.get_main_approvals()
            hr_assistant_id = approvals['hr_assistant']

            if self.is_hr_manager_on_leave(hr_approve_id):
                hr_next_approver = hr_assistant_id.id
                hr_partner_id = hr_assistant_id.user_id.partner_id.id
                hr_partner_name = hr_assistant_id.name
            else:
                hr_next_approver = hr_approve_id.id
                hr_partner_id = hr_approve_id.user_id.partner_id.id
                hr_partner_name = hr_approve_id.name

            if cron_job:
                self.send_hr_override_notification(hr_partner_id, hr_partner_name, holiday.id)
            elif holiday.state == 'validate':
                self.send_leave_approval_mail(hr_partner_id, hr_partner_name)
            else:
                holiday.write({'state': 'validate2', 'first_approver_id': holiday.employee_id.id,
                               'next_approver_id': hr_next_approver, 'last_approval_date': datetime.now()})
                self.send_leave_request_mail(hr_partner_id, hr_partner_name)

    def _get_main_approvals(self):
        # Getting the common approval ids.
        # raise errors if hr and ceo doesn't have related user
        hr_assistant = self.env['hr.employee'].search([('job_id.name', '=', 'HR Assistant')], limit=1)
        hr = self.env['hr.employee'].search([('job_id.name', '=', 'HR and Admin Manager')], limit=1)
        ceo = self.env['hr.employee'].search([('job_id.name', '=', 'CEO')], limit=1)

        # raise errors if no hr and ceo
        if not hr_assistant:
            raise UserError(_('There is no HR Assistant Position set to employee.'))
        if not hr:
            raise UserError(_('There is no HR and Admin Manager Position set to employee.'))
        if not ceo:
            raise UserError(_('There is no CEO position is set.'))

        if not hr_assistant.user_id:
            raise UserError(_('Please set the related user for HR Assistant in Employee screen.'))
        if not hr.user_id:
            raise UserError(_('Please set the related user for HR in Employee screen.'))
        if not ceo.user_id:
            raise UserError(_('Please set the related user for CEO in Employee screen.'))

        return {"hr": hr, "ceo": ceo, "hr_assistant": hr_assistant}
