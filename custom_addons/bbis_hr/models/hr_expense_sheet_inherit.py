from odoo import fields, models, api, _


class HRExpenseSheetInherit(models.Model):
    _inherit = 'hr.expense.sheet'

    #@api.multi
    def approve_expense_sheets(self):
        self.write({'state': 'approve', 'responsible_id': self.env.user.id})

    #@api.multi
    def refuse_sheet(self, reason):
        res = super(HRExpenseSheetInherit, self).refuse_sheet(reason)
        hr_approve_id = self.env['hr.employee'].sudo().search([('job_id', '=', 'HR and Admin Manager')], limit=1)
        # send email to employee if it has been refused
        for r in self.expense_line_ids:
            # do not send if it's already accountant
            if not r.employee_id.job_id.name.strip() == 'Accountant':
                r.send_mail_refused(r.employee_id.user_id.partner_id.id, r.employee_id.name, reason)

            # If the requester is not HR then send the refuse mail to HR.
            if r.employee_id != hr_approve_id:
                r.expense_refuse_mail_hr(hr_approve_id.user_id.partner_id.id, hr_approve_id.name, reason)
        return res

    @api.model
    def _create_set_followers(self, values):
        # Add the followers at creation, so they can be notified
        employee_id = values.get('employee_id')
        if not employee_id:
            return
