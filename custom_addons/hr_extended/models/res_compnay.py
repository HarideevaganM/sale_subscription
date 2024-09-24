
import calendar
from datetime import date, datetime, timedelta
from odoo import models,fields,api, _
from odoo.exceptions import ValidationError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        date = datetime.now()
        actual_net_amount = 0.0
        days = calendar.monthrange(date.year, date.month)[1]
        if days < 1:
            return res
        for rec in self:
            all_line_ids = rec.line_ids.filtered(lambda x: x.code == 'NET' and x.amount > 0)
            if len(all_line_ids) > 1:
                raise ValidationError('You can not have two net salary rules')
            for line in all_line_ids:
                net_amount = round((line.amount / days) * rec.lop_days, 2)
                actual_net_amount = line.amount - net_amount
                line.update({'amount': actual_net_amount})
        return res

class SalaryAdvancePayment(models.Model):
    _inherit = "salary.advance"

    def _get_credit_account(self):
        compnay_id = self.env.user.company_id
        if compnay_id and not compnay_id.credit_account:
            return False
        return compnay_id.credit_account 

    def _get_debit_account(self):
        compnay_id = self.env.user.company_id
        if compnay_id and not compnay_id.debit_account:
            return False
        return compnay_id.debit_account

    def _get_journal(self):
        compnay_id = self.env.user.company_id
        if compnay_id and not compnay_id.journal_id:
            return False
        return compnay_id.journal_id

    credit = fields.Many2one('account.account', string="Credit", default=_get_credit_account)
    debit = fields.Many2one('account.account', string="Debit", default=_get_credit_account)
    journal = fields.Many2one('account.journal', string='Journal', default=_get_journal)
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submit'),
                              ('waiting_approval', 'HR Approval'),
                              ('approve', 'CEO Approval'),
                              ('cancel', 'Cancelled'),
                              ('reject', 'Rejected')], string='Status', default='draft', track_visibility='onchange')
    
    def send_mail_advance_salary(self):
        group_id_list = []
        ir_model_data = self.env['ir.model.data']
        user_id = self.env.user
        ceo_group = self.env['res.groups'].browse(ir_model_data.get_object_reference('hr_work_from_home', 'group_fms_ceo')[1]).users.filtered(lambda x: x.id == user_id.id)
        group_id_list.append(ir_model_data.get_object_reference('account', 'group_account_manager')[1])
        users_email = ",".join([user.email for user in self.env['res.groups'].browse(group_id_list).users if user.email])
        template_id = ir_model_data.get_object_reference('hr_extended', 'email_salary_advance')[1]
        template = self.env['mail.template'].browse(template_id)
        template.write({
            'email_to': users_email or '',
            'body_html':
                'Hello, Employee advance salary request is approved by CEO and draft journal entry is created. Please check for further process </br> %s </br></br>Thank You,</p>'% ceo_group.name if ceo_group else ''
        })
        template.send_mail(self.id, force_send=True)
        return True

    #@api.one
    def approve_request_acc_dept(self):
        res_id = super(SalaryAdvancePayment, self).approve_request_acc_dept()
        self.send_mail_advance_salary()
        return res_id

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res_id = super(SalaryAdvancePayment, self).onchange_employee_id()
        if self.employee_id and self.employee_id.contract_ids:
            self.employee_contract_id = self.employee_id.contract_ids.ids[0]
        return res_id

class ResCompnay(models.Model):
    _inherit = 'res.company'

    credit_account = fields.Many2one('account.account', string="Credit")
    debit_account = fields.Many2one('account.account', string="Debit")
    journal_id = fields.Many2one('account.journal', string='Journal')