from odoo import models, api, fields, _
from datetime import datetime, date
from dateutil import relativedelta
from odoo.exceptions import UserError
import xlsxwriter
from io import StringIO
import base64
import os


class PayslipSummaryReport(models.TransientModel):
    _name = 'payslip.summary.report.wizard'

    date_start = fields.Date(string="Start Date",default=datetime.now().strftime('%Y-%m-01'))
    end_date = fields.Date(string='End Date', default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    filedata = fields.Binary('Download file', readonly=True)
    filename = fields.Char('Filename', size=64, readonly=True)



    # @api.multi
    def get_report_order(self):
        vals = []
        payslip_summary = self.env['hr.payslip'].search([])




        output = StringIO()
        url = '/home/ubuntu/odoo-11'

        workbook = xlsxwriter.Workbook(url + 'Payslip Summary Report.xlsx')
        worksheet = workbook.add_worksheet()
        merge_format1 = workbook.add_format({
            'bold': 1,
            'border':1,
            'align': 'center',

            'valign': 'vcenter'})

        merge_format5 = workbook.add_format({


            'align': 'center',

            'valign': 'vcenter'})

        merge_format2 = workbook.add_format({
            'align': 'right',
            'font_size': 11,
            'valign': 'vcenter',
            'num_format': '#,##0,0.000', })

        merge_format3 = workbook.add_format({
            'align': 'center',
            'bold': 1,
            'valign': 'vcenter',
            
            'font_size': 14,
           })
        merge_format4 = workbook.add_format({
            'align': 'left',
            'font_size': 11,
            'valign': 'vcenter',
             })

        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 20)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 20)
        worksheet.set_column('H:H', 20)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:J', 20)
        worksheet.set_column('K:K', 20)
        worksheet.set_column('L:L', 20)
        worksheet.set_column('M:M', 20)
        worksheet.set_column('N:N', 20)
        worksheet.set_column('O:O', 20)
        worksheet.set_column('P:P', 20)
        worksheet.set_column('Q:Q', 20)
        worksheet.set_column('R:R', 20)
        worksheet.set_column('S:S', 20)
        worksheet.set_column('T:T', 20)
        worksheet.set_column('U:U', 20)
        worksheet.set_column('V:V', 20)
        worksheet.set_column('W:W', 20)
        worksheet.set_column('X:X', 20)
        worksheet.set_column('Y:Y', 20)
        worksheet.set_column('Z:Z', 20)
        worksheet.set_column('AA:AA', 20)
        worksheet.set_column('AB:AB', 20)
        worksheet.set_column('AC:AC', 20)
        worksheet.set_column('AD:AD', 20)
        worksheet.set_column('AE:AE', 20)
        worksheet.set_column('AF:AF', 20)
        worksheet.set_column('AG:AG', 20)
        worksheet.set_column('AH:AH', 20)

        month = datetime.strptime(str(self.date_start), '%Y-%m-%d').strftime("%B,%Y")

        worksheet.merge_range('D2:G2', 'PAYSLIP SUMMARY REPORT -' + month, merge_format3)

        worksheet.write('A4', 'S.No', merge_format1)
        worksheet.write('B4',  'Name', merge_format1)


        worksheet.write('C4', "Employee Category", merge_format1)
        worksheet.write('D4', "Payroll Nationality", merge_format1)
        worksheet.write('E4', "Basic Salary", merge_format1)
        worksheet.write('F4', "HRA", merge_format1)
        worksheet.write('G4', "Mobile Allowance", merge_format1)
        worksheet.write('H4', "Fuel Allowance", merge_format1)
        worksheet.write('I4', "Car Allowance", merge_format1)
        worksheet.write('J4', "End Services Benefits", merge_format1)
        worksheet.write('K4', "Overtime Weekends", merge_format1)
        worksheet.write('L4', "Overtime Weekdays", merge_format1)
        worksheet.write('M4', "Salary Arrears", merge_format1)
        worksheet.write('N4', "Total Salary", merge_format1)
        worksheet.write('O4', "Loss Of Pay", merge_format1)
        worksheet.write('P4', "Loan Deduction ", merge_format1)
        worksheet.write('Q4', "Advance Salary", merge_format1)
        #~ worksheet.write('R4', "Insurance Amount", merge_format1)
        worksheet.write('R4', "Net Salary Payable", merge_format1)
        worksheet.write('S4', "Remarks", merge_format1)




        payslip = self.env["hr.payslip"].search(
            [('date_from', '>=', self.date_start), ('date_to', '<=', self.end_date)])

        n = 5
        serial_count = 1
        # value = 0
        # new = 0
        value1 = 0
        new1 = 0

        for line in payslip:
            worksheet.write('A' + str(n), str(serial_count), merge_format5)
            worksheet.write('B' + str(n), line.employee_id.name, merge_format4)

            worksheet.write('C' + str(n), line.employee_id.contract_id.type_id.name, merge_format4)
            worksheet.write('D' + str(n), line.employee_id.country_id.name, merge_format4)
            worksheet.write('E' + str(n), line.employee_id.contract_id.wage, merge_format2)
            worksheet.write('F' + str(n), line.line_ids.filtered(lambda x: x.code == 'HRA').total, merge_format2)

            worksheet.write('G' + str(n), line.line_ids.filtered(lambda x: x.code == 'MBL').total, merge_format2)
            worksheet.write('H' + str(n), line.line_ids.filtered(lambda x: x.code == 'FUEL').total, merge_format2)
            worksheet.write('I' + str(n), line.line_ids.filtered(lambda x: x.code == 'CAR').total, merge_format2)
            worksheet.write('J' + str(n), line.line_ids.filtered(lambda x: x.code == 'ESB').total, merge_format2)
            worksheet.write('K' + str(n), line.line_ids.filtered(lambda x: x.code == 'OTE').total, merge_format2)
            worksheet.write('L' + str(n), line.line_ids.filtered(lambda x: x.code == 'OTD').total, merge_format2)
            worksheet.write('M' + str(n), line.line_ids.filtered(lambda x: x.code == 'SA').total, merge_format2)
            worksheet.write('N' + str(n), line.line_ids.filtered(lambda x: x.code == 'GROSS').total, merge_format2)
            worksheet.write('O' + str(n), line.line_ids.filtered(lambda x: x.code == 'LOP').total, merge_format2)
            worksheet.write('P' + str(n), line.line_ids.filtered(lambda x: x.code == 'LOAN').total, merge_format2)
            worksheet.write('Q' + str(n), line.line_ids.filtered(lambda x: x.code == 'SAR').total, merge_format2)
            #~ worksheet.write('R' + str(n), line.line_ids.filtered(lambda x: x.code == 'INSUR').total, merge_format2)
            worksheet.write('R' + str(n), line.line_ids.filtered(lambda x: x.code == 'NET').total, merge_format2)
            # worksheet.write('T' + str(n), line.employee_id.contract_id.fuel_allowance, merge_format4)


            n += 1
            serial_count += 1
            # value += new
            # new = line.line_ids.filtered(lambda x: x.code == 'GROSS').total
            #
            # worksheet.write('L' + str(n), "Total", merge_format3)
            # worksheet.write('M' + str(n), value, merge_format2)

            value1 += new1
            new1 = line.line_ids.filtered(lambda x: x.code == 'NET').total

            worksheet.write('R' + str(n), "Total", merge_format3)
            worksheet.write('S' + str(n), value1, merge_format2)

        workbook.close()
        fo = open(url + 'Payslip Summary Report.xlsx', "rb+")
        data = fo.read()
        out = base64.encodestring(data)
        self.write({'filedata': out, 'filename': 'Payslip Summary Report.xlsx'})

        return {
            'name': 'Payslip Summary Report',
            'res_model': 'payslip.summary.report.wizard',
            'type': 'ir.actions.act_window',
            # 'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'no destroy': True,
            'res_id': self.id,
        }







