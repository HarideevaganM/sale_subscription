from odoo import api, fields, models, _
from datetime import datetime
from dateutil import relativedelta


class ReportBankAdvice(models.AbstractModel):
    _name = 'report.bank_advice_report.bank_advice_report_form_id'
    _description = "Bank Advice Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        return {
            'data': data.get('form'),
        }


class BankAdviceReport(models.TransientModel):
    _name = "bank.advice.report"
    _description = "Bank Advice Report Wizard"

    # ~ date_start = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    # ~ date_end = fields.Date(string='End Date', required=True, default=fields.Date.today)
    date_start = fields.Date(string='Start Date', required=True,default=datetime.now().strftime('%Y-%m-01'))
    date_end = fields.Date(string='End Date',required=True, default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    reference_code = fields.Char(string='Reference Code', store=True)

    #@api.multi
    def print_report(self):
        domain = []
        datas = []
        amt = 0.0
        net = 0.0
        payslip = self.env["hr.payslip"].search(
                [('date_from', '>=', self.date_start), ('date_to', '<=', self.date_end),('contract_id.type_id.name', '=', 'Employee')])
        total_amount = 0.0   
        for slips in payslip:
            net = slips.line_ids.filtered(lambda x: x.code == 'NET').total
            net_sal = net
            datas.append({
                    'name':slips.employee_id.name,
                    'bank_name':slips.employee_id.bank_name,
                    'branch_name':slips.employee_id.branch_name,
                    'bank_number_id':slips.employee_id.bank_number_id.acc_number,                    
                    'amount': net_sal
                    
                })
                
            total_amount += net_sal
            test = []
            # net = slips.line_ids.filtered(lambda x: x.code == 'NET').total
            # ~ print(net.total)
            # ~ for line in slips.line_ids:
                # ~ test.append({
                # ~ 'emp': line.slip_id.employee_id.name,
                # ~ 'code': line.code,
                # ~ 'amount': line.amount,
                # ~ 'total': line.total
                # ~ })
                
            # ~ print('\n--', test, '-test--\n')
            

        res = {
            'payslip':datas,
            'date_from': self.date_start,
            'date_end': self.date_end,                     
            'total_amount':total_amount,
            'reference_code':self.reference_code            
        }
        data = {
            'form': res,
        }
        return self.env.ref('bank_advice_report.report_bank_advice_id').report_action([],data=data) 



   
