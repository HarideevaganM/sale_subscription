from odoo import models, api, fields, _
from datetime import datetime
from dateutil import relativedelta
import xlsxwriter
import decimal
import base64
import string


class PayslipSummaryReport(models.TransientModel):
    _name = 'payslip.summary.report.wizard'
    _description = 'payslip Summary Report'

    date_start = fields.Date(string="Start Date", default=datetime.now().strftime('%Y-%m-01'))
    end_date = fields.Date(string='End Date', default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    filedata = fields.Binary('Download file', readonly=True)
    filename = fields.Char('Filename', size=64, readonly=True)

    # @api.multi
    def _get_report_order(self):

        payslips = self.env["hr.payslip"].search(
            [('date_from', '>=', self.date_start), ('date_to', '<=', self.end_date)])
        url = '/tmp/'

        workbook = xlsxwriter.Workbook(url + 'Payslip Summary Report.xlsx')
        worksheet = workbook.add_worksheet()

        merge_format3 = workbook.add_format({
            'align': 'center',
            'bold': 1,
            'valign': 'vcenter',
            'font_size': 14,
           })
        bold = workbook.add_format({'bold': True})
        bold_1 = workbook.add_format({
                            'bold': True,
                            'align': 'center',
                            'valign': 'vcenter',
        })
        currency_format = workbook.add_format({'num_format': '##0.000'})
        currency_format2 = workbook.add_format({'num_format': '##0.000',
                                               'bold': True,
                                                })

        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 15)
        worksheet.set_column('I:I', 15)
        worksheet.set_column('J:J', 15)
        worksheet.set_column('K:K', 15)
        worksheet.set_column('L:L', 15)
        worksheet.set_column('M:M', 15)
        worksheet.set_column('N:N', 15)
        worksheet.set_column('O:O', 15)
        worksheet.set_column('P:P', 15)
        worksheet.set_column('Q:Q', 15)
        worksheet.set_column('R:R', 15)
        worksheet.set_column('S:S', 15)
        worksheet.set_column('T:T', 15)
        worksheet.set_column('U:U', 15)
        worksheet.set_column('V:V', 15)
        worksheet.set_column('W:W', 15)
        worksheet.set_column('X:X', 15)
        worksheet.set_column('Y:Y', 15)
        worksheet.set_column('Z:Z', 15)

        month = datetime.strptime(str(self.date_start), '%Y-%m-%d').strftime("%B,%Y")
        company = self.env.user.company_id

        worksheet.merge_range('B3:E3', 'PAYSLIP SUMMARY REPORT -' + month, merge_format3)
        worksheet.merge_range('B1:E1', company.name, merge_format3)
        worksheet.merge_range('B2:E2', (company.street or '') + ' ' + (company.street2 or '') + ' ' + (company.city or '') + ' ' + (company.state_id.name if company.state_id else '') + ' ' + (company.country_id.name if company.country_id else '') + ' ' + (company.zip or ''), bold_1)

        alp = string.ascii_uppercase
        headers = [
            {'header': 'S.No'},
            {'header': 'Name'},
            {'header': 'Category'},
            {'header': 'Nationality'},
            ]

        codes = []
        allowances = []
        deductions = []
        others = []
        for line in payslips.mapped('line_ids'):
            if line.category_id.code in ['ALW', 'ADD']:
                allowances.append(line.code)
            elif line.category_id.code == 'DED':
                deductions.append(line.code)
            elif line.category_id.code not in ['BASIC', 'GROSS', 'NET', 'ALW', 'ADD', 'DED']:
                others.append(line.code)

        if payslips.mapped('line_ids').filtered(lambda x: x.code == 'BASIC'):
            codes.append('BASIC')
        if payslips.mapped('line_ids').filtered(lambda x: x.code == 'HRA'):
            codes.append('HRA')
        for alw in sorted(set(allowances)):
            if alw != 'HRA':
                codes.append(alw)

        if payslips.mapped('line_ids').filtered(lambda x: x.code == 'GROSS'):
            codes.append('GROSS')
        for ded in sorted(set(deductions)):
            codes.append(ded)
        for oth in sorted(set(others)):
            codes.append(oth)
        if payslips.mapped('line_ids').filtered(lambda x: x.code == 'NET'):
            codes.append('NET')

        name = []

        for code in codes:
            rule = self.env['hr.salary.rule'].search([('code', '=', code)], limit=1)
            if rule and rule.name in name:
                headers.append({'header': rule.name + '(' + rule.code + ')' if rule else code, 'format': currency_format})
            else:
                headers.append({'header': rule.name if rule else code, 'format': currency_format})
            name.append(rule.name if rule else code)

        datas = []
        s_no = 1
        for payslip in payslips:
            data = []
            data.append(s_no)
            data.append(payslip.employee_id.name)
            data.append(payslip.contract_id.type_id.name if payslip.contract_id and payslip.contract_id.type_id else '')
            data.append(payslip.employee_id.country_id.name if payslip.employee_id.country_id else '')
            for code in codes:
                val = payslip.line_ids.filtered(lambda x: x.code == code)
                data.append(val.total if val else 0.000)
            datas.append(data)
            s_no += 1

        cols = 'A5:'+alp[(len(codes)+3)]+str(5+len(datas))
        worksheet.add_table(cols, {
                                    'data': datas,
                                    'columns': headers,
                                    'autofilter': False
                                    })
        worksheet.write('D'+str(6+len(datas)), 'Totals', bold_1)

        i = 0
        while i < (len(headers)+1):
            if i > 4:
                formula = '=SUM('+alp[i-1]+'6'+':'+alp[i-1]+str(5+len(datas))+')'
                worksheet.write_formula(5+len(datas), i-1, formula, currency_format2)
            i += 1

        workbook.close()
        fo = open(url + 'Payslip Summary Report.xlsx', "rb+")
        data = fo.read()
        out = base64.encodestring(data)
        self.write({'filedata': out, 'filename': 'Payslip Summary Report.xlsx'})

        return {
            'name': 'Payslip Summary Report',
            'res_model': 'payslip.summary.report.wizard',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'no destroy': True,
            'res_id': self.id,
        }







