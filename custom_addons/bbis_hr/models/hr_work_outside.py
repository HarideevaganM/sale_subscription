from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import math
from datetime import datetime
from datetime import timedelta


class HRWorkOutside(models.Model):
    _name = 'hr.work.outside'
    _description = "Work Outside"
    _inherit = ['mail.thread']
    _rec_name = 'employee_id'
    _order = 'create_date desc'

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.uid)], limit=1)

    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, readonly=True,
                                  states={'draft': [('readonly', False)], 'submit': [('readonly', False)]},
                                  default=_default_employee, track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', related_sudo=True,
                              compute_sudo=True, store=True, default=lambda self: self.env.uid, readonly=True)
    from_date = fields.Datetime(string="From Date", default=fields.Datetime.now)
    to_date = fields.Datetime(string="To Date", default=fields.Datetime.now)
    no_of_days = fields.Integer(string="No of Days", compute="_get_day")
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    add_zip = fields.Char('Zip', change_default=True)
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char(string="Phone")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('approve', 'Approved'),
    ], string='State', default="draft")
    reason_work_from_home = fields.Text()
    count_expense = fields.Integer(compute="_count_expenses", string="Expenses")
    expense_ids = fields.Many2one('hr.expense', string="Expenses")

    def _count_expenses(self):
        for rec in self:
            rec.count_expense = self.env['hr.expense'].search_count([('work_outside_id', '=', rec.id)])

    def action_submit(self):
        if self.no_of_days <= 0:
            raise ValidationError("You can not submit request with 0 number of days.")

        hr_approve_id = self.env['hr.employee'].sudo().search([('job_id', '=', 'HR and Admin Manager')], limit=1)
        self.write({'state': 'submit'})

        # Do not send if it's already HR Manager
        if not self.employee_id.job_id.name.strip() == 'HR and Admin Manager':
            self.send_work_from_outside_request(hr_approve_id.user_id.partner_id.id, hr_approve_id.name)

    def action_approve(self):
        if self.no_of_days <= 0:
            raise ValidationError("You can not approve request with 0 number of days.")

        hr_approve_id = self.env['hr.employee'].sudo().search([('job_id', '=', 'HR and Admin Manager')], limit=1)
        hr_user_id = self.env['hr.employee'].search([('job_id', '=', 'HR Assistant')], limit=1)

        if hr_approve_id.user_id.id == self.env.uid:
            self.write({'state': 'approve'})
            self.send_work_from_outside_request(self.employee_id.user_id.partner_id.id, self.employee_id.name)

            # send email to hr assistant
            if hr_user_id:
                self.with_context({"send_hr_assistant": True}).send_work_from_outside_request(hr_user_id.user_id.partner_id.id, hr_user_id.name)
        else:
            raise UserError(_('You have no permission to approve this entry'))

    # Mail to HR for the approval of work request from outside.
    def send_work_from_outside_request(self, next_id, next_approve):
        for r in self:
            r.message_post_with_view('bbis_hr.message_outside_work', composition_mode='mass_mail',
                                     partner_ids=[(4, next_id)], auto_delete=True, auto_delete_message=True,
                                     parent_id=False, values={'next_approve': next_approve},
                                     subtype_id=self.env.ref('mail.mt_note').id)

    @api.depends('from_date', 'to_date')
    def _get_day(self):
        for rec in self:
            diff = 0.0
            from_date = fields.Datetime.from_string(rec.from_date)
            to_date = fields.Datetime.from_string(rec.to_date)
            if from_date and to_date:
                diff = to_date - from_date
            rec.no_of_days = math.ceil(diff.days + float(diff.seconds) / 86400)

    #@api.multi
    def action_expense(self):
        if self.count_expense:
            return {
                'name': "Add Expenses",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.expense',
                'context': {'default_work_outside_id': self.id, 'default_employee_id': self.sudo().employee_id.id},
                'domain': [('work_outside_id', '=', self.id)],
            }
        else:
            return {
                'name': "Add Expenses",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'hr.expense',
                'context': {'default_work_outside_id': self.id, 'default_employee_id': self.sudo().employee_id.id},
                'domain': [('work_outside_id', '=', self.id)],
            }

    #@api.multi
    def action_expenses_entries(self):
        expense_ids = self.env['hr.expense'].sudo().search([('work_outside_id', '=', self.id)])
        return {
            'name': 'Expenses',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.expense',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {'default_work_outside_id': self.id, 'default_employee_id': self.sudo().employee_id.id},
            'domain': [('id', 'in', expense_ids.ids)],
        }

    def unlink(self):
        for req in self:
            if req.state == 'approve':
                raise ValidationError(_('You can not delete work requests which are in approved state'))
        return super(HRWorkOutside, self).unlink()


