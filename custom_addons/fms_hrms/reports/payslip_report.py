from odoo import api, fields,models,_
from datetime import datetime
from odoo.exceptions import UserError


class PayslipReportInherited(models.AbstractModel):
    _name = 'report.fms_hrms.report_payslip'

    def get_loan(self,data):
        line_val = []
        amount = 0
        balance = 0
        payslip_id = self.env['hr.payslip'].search([('id','=',data.id)])
        contract = payslip_id.contract_id.id
        contract_id = self.env['hr.contract'].browse(contract)
        if contract_id.balance_amount and contract_id.total_amount:
            amount = (contract_id.total_amount / contract_id.installment)
            balance = (contract_id.balance_amount / amount)
        else:
            balance = 0.0
        if contract_id:
            line_val.append({
                    'total_amount' : contract_id.total_amount,
                    'balance_amount' : contract_id.balance_amount,                      
                    'remaining_installment' : balance,                       
                    'loan_type' : contract_id.loan_type,                       
                    })
        return line_val

    # @api.multi
    def render_html(self, ids, data=None):
        report_obj = self.env['hr.payslip'].browse(ids)
        vals = self.env['hr.employee'].search([('id', '=', report_obj.id)])
        vals1 = self.env['hr.contract'].search([('id', '=', vals.contact_id.id)])
        for status in report_obj:
            if status.state != 'done':  
               raise UserError(_("Report is not in 'Done' State ...!! "))

            self.env['hr.payslip']._parent_store_compute()
            self.env.cr.commit()  #

        docargs = {
            'doc_ids': ids,
            'doc_model': 'hr.payslip',
            'docs': report_obj,
            'data': data,
            'get_loan': self.get_loan,
            'docs_new': vals,
            'docs_new1': vals1,


        }

        return self.env['report'].render('fms_hrms.report_employee_payslip', docargs)
