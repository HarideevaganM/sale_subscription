# -*- coding: utf-8 -*-
from odoo import models
import csv

class ProductXlsx(models.AbstractModel):
    _name = 'report.emp_summary_report_xls.emp_summary_template_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def find_leaves(self, employee, start_date, end_date):
        leaves_ids = self.env['hr.holidays'].search([('date_from', '>=', start_date), ('date_to', '<=', end_date), ('employee_id', '=', employee.id)])
        return leaves_ids

    def find_disciplinary(self, employee):
        leaves_ids = self.env['disciplinary.action'].search([('employee_name', '=', employee.id)])
        return leaves_ids

    def find_from_home_ids(self, employee):
        work_home_ids = self.env['hr.work.home'].search([('employee_id', '=', employee.id)])
        return work_home_ids

    def find_over_time_ids(self, employee):
        over_time_ids = self.env['hr.overtime'].search([('employee_id', '=', employee.id)])
        return over_time_ids

    def generate_xlsx_report(self, workbook, data, products):
        employee_ids = self.env['hr.employee'].browse(data.get('employee_ids'))
        sheet = workbook.add_worksheet("Employee Summary")
        sheet.set_column('A6:A7',20)
        sheet.set_column('B17:B18',20)
        sheet.set_column('C19:C20',20)
        sheet.set_column('D21:D22',20)
        sheet.set_column('E23:E24',20)
        format1 = workbook.add_format({'font_size': 22, 'bg_color': '#D3D3D3', 'align': 'center','border': 1})
        format2 = workbook.add_format({'font_size': 10, 'bold': True, 'bg_color': '#D3D3D3'})
        format6 = workbook.add_format({'font_size': 10, 'bold': True, 'bg_color': '#60a4af'})
        format5 = workbook.add_format({'font_size': 10, 'bold': True, 'bg_color': '#D3D3D3' , 'align': 'center'})
        format3 = workbook.add_format({'font_size': 10})
        format4 = workbook.add_format({'font_size': 10, 'bold': True})
        sheet.merge_range(2, 1, 3, 7, 'Employee Summary Report', format1)
        line_row = 5
        i = 1
        for emp in employee_ids:
            sheet.write(line_row,2, emp.name, format5)
            sheet.write(line_row,3, 'Current - Salary : ' + str(emp.salary),format5)
            line_row+=1
            sheet.write(line_row, 1, 'All Leaves', format6)
            line_row+=1
            sheet.write(line_row, 1, "From Date", format2)
            sheet.write(line_row, 2, "End Date", format2)
            sheet.write(line_row, 3, "Leaves Tyoe", format2)
            sheet.write(line_row, 4, "Duration", format2)
            line_row += 1
            leaves_ids = self.find_leaves(emp, data.get('start_date'), data.get('end_date'))
            for leaves in leaves_ids:
                sheet.write(line_row, 1,  str(leaves.date_from), format3)
                sheet.write(line_row, 2,  str(leaves.date_to), format3)
                sheet.write(line_row, 3 , str(leaves.holiday_status_id.name), format3)
                sheet.write(line_row, 4,  str(leaves.number_of_days_temp), format3)
                line_row+=1
            disciplinary_ids = self.find_disciplinary(emp)
            sheet.write(line_row, 1, 'Disciplinaries', format6)
            line_row+=1
            sheet.write(line_row, 1, "Reason", format2)
            sheet.write(line_row, 2, "Action", format2)
            sheet.write(line_row, 3, "Action Details", format2)
            sheet.write(line_row, 4, "Charge From Action", format2)
            line_row += 1
            for disciplinary in disciplinary_ids:
                sheet.write(line_row, 1,  str(disciplinary.action and disciplinary.action.name or ''), format3)
                sheet.write(line_row, 2,  str(disciplinary.action and disciplinary.action.name or  ''), format3)
                sheet.write(line_row, 3 , str(disciplinary.action and disciplinary.action.description or  ''), format3)
                sheet.write(line_row, 4,  str(disciplinary.action and disciplinary.action.charges or  ''), format3)
                line_row+=1
            over_time_ids = self.find_over_time_ids(emp)
            sheet.write(line_row, 1, 'Over Times', format6)
            line_row+=1
            sheet.write(line_row, 1, "To", format2)
            sheet.write(line_row, 2, "From", format2)
            sheet.write(line_row, 3, "Duration", format2)
            sheet.write(line_row, 4, "Duration Type", format2)
            line_row += 1
            for over in over_time_ids:
                sheet.write(line_row, 1,  str(over.date_from), format3)
                sheet.write(line_row, 2,  str(over.date_to), format3)
                sheet.write(line_row, 3 , str(over.days_no_tmp), format3)
                sheet.write(line_row, 4 , str(over.duration_type), format3)
                line_row+=1
            work_from_home_ids = self.find_from_home_ids(emp)
            sheet.write(line_row, 1, 'Work From Home', format6)
            line_row+=1
            sheet.write(line_row, 1, "From", format2)
            sheet.write(line_row, 2, "To", format2)
            sheet.write(line_row, 3, "No of Days", format2)
            sheet.write(line_row, 4, "Leave Type", format2)
            line_row += 1
            for work in work_from_home_ids:
                sheet.write(line_row, 1,  str(work.from_date), format3)
                sheet.write(line_row, 2,  str(work.to_date), format3)
                sheet.write(line_row, 3, str(work.no_of_days), format3)
                sheet.write(line_row, 4,  str(work.leave_type), format3)
                line_row+=1
            sheet.write(line_row, 1, 'Insurance Policy', format6)
            line_row+=1
            sheet.write(line_row, 1, "Coverage", format2)
            sheet.write(line_row, 2, "Sum Amount", format2)
            sheet.write(line_row, 3, "Policy Amount", format2)
            sheet.write(line_row, 4, "Policy", format2)
            line_row += 1
            for insur in emp.insurance:
                sheet.write(line_row, 1,  str(insur.policy_coverage), format3)
                sheet.write(line_row, 2,  str(insur.sum_insured), format3)
                sheet.write(line_row, 3 , str(insur.amount), format3)
                sheet.write(line_row, 4,  str(insur.policy_id and insur.policy_id.name), format3)
                line_row+=1
            line_row+=1