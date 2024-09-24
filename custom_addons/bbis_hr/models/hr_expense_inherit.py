from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class HRExpenseInherit(models.Model):
    _inherit = 'hr.expense'

    work_outside_id = fields.Many2one('hr.work.outside')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', related_sudo=True,
                              compute_sudo=True, store=True, default=lambda self: self.env.uid, readonly=True)
    submitted_to_hr = fields.Integer(string='Submit To HR')

    @api.model
    def create(self, vals):
        res = super(HRExpenseInherit, self).create(vals)

        # Immediately submit to accounting if it's HR Manager
        if res.employee_id.job_id.name.strip() == 'HR and Admin Manager':
            res.submitted_to_hr = 1

        if res.employee_id.job_id.name.strip() == 'Accountant':
            res.submitted_to_hr = 2

        return res

    #@api.multi
    def refuse_expense(self, reason):
        res = super(HRExpenseInherit, self).refuse_expense(reason)
        hr_approve_id = self.env['hr.employee'].sudo().search([('job_id', '=', 'HR and Admin Manager')], limit=1)
        # send mail to employee except accountant
        if not self.employee_id.job_id.name.strip() == 'Accountant':
            self.send_mail_refused(self.employee_id.user_id.partner_id.id, self.employee_id.name, reason)

        # If the requester is not HR then send the refuse mail to HR.
        if self.employee_id != hr_approve_id:
            self.expense_refuse_mail_hr(hr_approve_id.user_id.partner_id.id, hr_approve_id.name, reason)

        return res

    def action_view_work_request(self):
        return {
            'name': 'Outside Work Request',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'hr.work.outside',
            'target': 'current',
            'domain': [('id', '=', self.work_outside_id.id)]
        }

    #@api.multi
    def submit_to_hr(self):
        hr_approve_id = self.env['hr.employee'].sudo().search([('job_id', '=', 'HR and Admin Manager')], limit=1)
        self.outside_work_expense_request(hr_approve_id.user_id.partner_id.id, hr_approve_id.name)
        self.write({'submitted_to_hr': 1})

    #@api.multi
    def submit_to_accounting(self):
        hr_approve_id = self.env['hr.employee'].search([('job_id', '=', 'HR and Admin Manager')], limit=1)
        if hr_approve_id.user_id.id != self.env.uid:
            raise UserError(_('You have no permission to approve this entry'))
        accounts_approve_id = self.env['hr.employee'].search([('job_id', '=', 'Accountant')], limit=1)
        if not accounts_approve_id.user_id.partner_id.id:
            raise UserError(_('Please set a Related User from Employee for the next approve.'))
        self.write({'submitted_to_hr': 2})
        self.outside_work_expense_request(accounts_approve_id.user_id.partner_id.id, accounts_approve_id.name)

    #@api.multi
    def submit_expenses_sudo(self):
        if not self.account_id.id:
            raise UserError(_('Please set a valuable account for the expense posting.'))

        if any(expense.state != 'draft' for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report!"))

        self.env['hr.expense.sheet'].create({
            'name': self.name,
            'state': 'submit',
            'employee_id': self.employee_id.id,
            'address_id': '',
            'responsible_id': self.env.user.id,
            'total_amount': self.total_amount,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'expense_line_ids': [(4, line.id) for line in self]
        })
        self.write({'submitted_to_hr': 3})

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'res_id': self.sheet_id.id
        }

    # Mail to HR for the approval of outside work expense request.
    def outside_work_expense_request(self, next_id, next_approve):
        for r in self:
            r.message_post_with_view('bbis_hr.message_outside_expense', composition_mode='mass_mail',
                                     partner_ids=[(4, next_id)], auto_delete=True, auto_delete_message=True,
                                     parent_id=False, values={'next_approve': next_approve},
                                     subtype_id=self.env.ref('mail.mt_note').id)

    # Mail to HR for the approval of outside work expense request.
    def send_mail_refused(self, next_id, next_approve, reason):
        for r in self:
            r.message_post_with_view('bbis_hr.mail_expense_refused', composition_mode='mass_mail',
                                     partner_ids=[(4, next_id)], auto_delete=True, auto_delete_message=True,
                                     parent_id=False, values={'next_approve': next_approve, 'reason': reason},
                                     subtype_id=self.env.ref('mail.mt_note').id)

    # Expense refuse mail to HR
    def expense_refuse_mail_hr(self, next_id, next_approve, reason):
        mail_to = 'hr'
        for r in self:
            r.message_post_with_view('bbis_hr.mail_expense_refused', composition_mode='mass_mail',
                                     partner_ids=[(4, next_id)], auto_delete=True, auto_delete_message=True,
                                     parent_id=False,
                                     values={'next_approve': next_approve, 'reason': reason, 'mail_to': mail_to},
                                     subtype_id=self.env.ref('mail.mt_note').id)
