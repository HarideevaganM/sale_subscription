# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from datetime import time as datetime_time
#~ from cStringIO import StringIO
import xlsxwriter
import base64
import calendar
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta as rdelta
#~ import cStringIO
#~ import StringIO

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class HrPayslipInherited(models.Model):
    _inherit = 'hr.payslip'

    date = fields.Date('Date Account', states={'draft': [('readonly', False)]}, readonly=True, help="Keep empty to use the period of the validation(Payslip) date.")
    journal_id = fields.Many2one('account.journal', 'Salary Journal')
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False)
    total_no_of_days = fields.Integer('Total No. Of Days', store=True)

    @api.model
    @api.onchange('date_from', 'date_to')
    def onchange_date_from(self):
        if self.date_from:
            for contract in self.filtered(lambda contract: self.contract_id.resource_calendar_id):
                from_date = datetime.combine(fields.Date.from_string(self.date_from), datetime_time.min)
                day_from = from_date.date()
                first_day = str(day_from.replace(day=1))
                day_from1 = datetime.combine(fields.Date.from_string(first_day), datetime_time.min)
                day_from2 = datetime.strptime(str(day_from1), "%Y-%m-%d %H:%M:%S")
                day_to2 = datetime.strptime(str(self.date_to), "%Y-%m-%d")
                total_days = self.employee_id.with_context(no_tz_convert=True).get_work_days_data(
                    day_from2, day_to2, calendar=self.contract_id.resource_calendar_id)
                self.total_no_of_days = total_days['days']

    # Loan compute total paid amount #
    # @api.one
    def compute_total_paid(self):
        for rec in self:
            """This compute the total paid amount of Loan.
                """
            total = 0.0
            for line in rec.loan_ids:
                if line.paid:
                    total += line.amount
            rec.total_paid = total

    # Loan fields #
    loan_ids = fields.One2many('hr.loan.line', 'payslip_id', string="Loans")
    total_paid = fields.Float(string="Total Loan Amount", compute='compute_total_paid')
    lop_days = fields.Integer("No. of LOP")

    # Get loan details #
    # @api.multi
    def get_loan(self):
        """This gives the installment lines of an employee where the state is not in paid.
            """
        loan_list = []
        loan_ids = self.env['hr.loan.line'].search([('employee_id', '=', self.employee_id.id), ('paid', '=', False)])
        for loan in loan_ids:
            loan_list.append(loan.id)
        self.loan_ids = loan_list
        return loan_list

    # Get loan details in Payslip #
    # @api.multi
    def action_payslip_done(self):
        loan_list = []
        mon_pay = datetime.strptime(str(self.date_from),'%Y-%m-%d').month
        self.get_loan()
        for line in self.loan_ids:
            mon_loan = datetime.strptime(str(line.date),'%Y-%m-%d').month
            if mon_pay == mon_loan:
                line.paid = True
            if line.paid:
                loan_list.append(line.id)
            else:
                line.payslip_id = False
        self.loan_ids = loan_list
        return super(HrPayslipInherited, self).action_payslip_done()

    def get_inputs(self, contract_ids, date_from, date_to):
        """This Compute the other inputs to employee payslip."""
        amount = 0.0
        salary_arrears = []
        contract_obj = self.env['hr.contract']
        res = super(HrPayslipInherited, self).get_inputs(contract_ids, date_from, date_to)
        emp_id = contract_obj.browse(contract_ids.id).employee_id
        if emp_id:
            salary_arrears = self.env['employee.line'].search([('employee_id', '=', emp_id.id)])
        for line in salary_arrears:
            current_date = datetime.strptime(str(date_from), '%Y-%m-%d').date().month
            existing_date = datetime.strptime(str(line.arrear_id.from_date), '%Y-%m-%d').date().month
            if current_date == existing_date:
                amount = line.arrears
            for result in res:
                if line.arrear_id.state == 'done' and amount != 0 and result.get('code') == 'SARR':
                    result['amount'] = amount
        return res


class HrContractInherited(models.Model):
    _inherit = 'hr.contract'

    # @api.one
    @api.depends('hra','wage')
    def _gross_compute(self):
        self.gross=self.wage+self.hra
    # Loan amount computation #

    # @api.one
    @api.depends('loan_amount', 'loan_lines', 'loan_lines.amount', 'loan_lines.paid')
    def _compute_loan_amount(self):
        for rec in self:
            total_paid = 0.0
            ded = 0.0
            loan_amt = rec.loan_amount
            instmt = rec.installment
            if loan_amt > 0:
                ded = (loan_amt / instmt if instmt > 0 else 1)
                for line in rec.loan_lines:
                    if line.paid:
                        total_paid += line.amount
                        loan_amt -= ded
                        instmt -= 1
                        if loan_amt == 0:
                            ded = 0.0
                balance_amount = rec.loan_amount - total_paid
                rec.total_amount = rec.loan_amount
                rec.balance_amount = balance_amount
                rec.total_paid_amount = total_paid
            rec.loan_deduction = ded

    loan_deduction = fields.Float('Loan Deduction', compute='_compute_loan_amount', store=True)
    loan_amt = fields.Integer("Loan Amount")
    loan_amt_emp = fields.Many2one("hr.loans", "Employee Loan")
    loan_lines = fields.One2many('hr.loan.line', 'contract_id', string="Loan Line", index=True)
    loan_amount = fields.Float(string="Loan Amount", required=True, related='employee_id.loan_amt')
    installment = fields.Integer(string="No Of Installments", default=1)
    total_amount = fields.Float(string="Total Amount", readonly=True, compute='_compute_loan_amount', store=True)
    balance_amount = fields.Float(string="Balance Amount", compute='_compute_loan_amount', store=True)
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_loan_amount', store=True)
    payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today())
    history_line = fields.One2many('salary.history.line','contract_id','Salary History')
    salary_arrear = fields.Float('Salary Arrear', digits=(16, 3),readonly=False)
    is_arrear = fields.Boolean('Is salary Revised',default=False)
    gross = fields.Float('Gross', compute='_gross_compute')

    #~ # Loan installment details #
    # @api.multi
    def compute_installment(self):
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self.loan:
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': amount,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                date_start = date_start + relativedelta(months=1)
        return True


#~ # Loan one2many class #
class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    amount = fields.Float(string="Amount", required=True)
    paid = fields.Boolean(string="Paid")
    contract_id = fields.Many2one('hr.contract', string="Contract Ref. ")
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.")


class SalaryHistoryLine(models.Model):
    _name = 'salary.history.line'

    old_basic = fields.Char('Basic Percentage')
    old_wage = fields.Float('Wages', digits=(16, 5))
    old_stucture_id = fields.Many2one('hr.payroll.structure','Payroll Structure')
    contract_id = fields.Many2one('hr.contract','Contract')
    fuel_allowance = fields.Float('Travel Allowance')
    mobile_allowance = fields.Float('EA Allowance')
    allowance1 = fields.Float('Data Card Allowance')
    allowance2 = fields.Float('Overtime Allowance')
    allowance3 = fields.Float('PT')
    allowance4 = fields.Float('HRA')
    deduction1 = fields.Float('Bonus')
    deduction2 = fields.Float('Medical')
    deduction3 = fields.Float('Conveyance ')
    deduction4 = fields.Float('Other Allowance ')
    deduction5 = fields.Float('TDS')
    deduction6 = fields.Float('Mobile Deduction')
    deduction7 = fields.Float('PASI')


class SalaryRevision(models.Model):
    _name = 'salary.revision'

    #~ basic=fields.Char('Basic Percentage')
    wage = fields.Float('Wages', digits=(16, 3))
    effective_date = fields.Date('Effective Date')
    stucture_id = fields.Many2one('hr.payroll.structure','Payroll Structure')
    contract_id = fields.Many2one('hr.contract','Contract')
    fuel_allowance = fields.Float('Fuel Allowance',digits=(16, 3))
    mobile_allowance = fields.Float('Mobile Allowance',digits=(16, 3))
    allowance1= fields.Float('Allowance 1',digits=(16, 3))
    allowance2 = fields.Float('Allowance 2',diits=(16, 3))
    #~ pt=fields.Float('PT',digits=(16, 5))
    #~ hra=fields.Float('HRA',digits=(16, 5))
    allowance3 = fields.Float('Allowance 3',digits=(16, 3))
    allowance4 = fields.Float('Allowance 4',digits=(16, 3))
    deduction1 = fields.Float('Deduction 1',digits=(16, 3))
    deduction2 = fields.Float('Deduction 2',digits=(16, 3))
    deduction3 = fields.Float('Deduction 3',digits=(16, 3))
    deduction4 = fields.Float('Deduction 4',digits=(16, 3))
    deduction5 = fields.Float('Deduction 5',digits=(16, 3))
    deduction6 = fields.Float('Deduction 6',digits=(16, 3))
    deduction7 = fields.Float('Deduction 7',digits=(16, 3))

    @api.model
    def default_get(self, fields):
        rec = super(SalaryRevision, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        # Checks on context parameters
        if not active_model or not active_ids:
            raise UserError(_("Programmation error: wizard action executed without active_model or active_ids in context."))

        # Checks on received invoice records
        contract = self.env[active_model].browse(active_ids)
        rec.update({
            #~ 'basic': contract.basic_percentage,
            'wage': contract.wage,
            'effective_date': '',
            'stucture_id': contract.struct_id.id,
            'contract_id': contract.id,
        })
        return rec

    # @api.multi
    def update_salary(self):
        lines=[]
        lines.append((0,0,{
                        #~ 'old_basic':self.contract_id.basic_percentage,
                        'old_wage':self.contract_id.wage,
                        'contract_id':self.contract_id.id,
                        'old_stucture_id':self.contract_id.struct_id.id,
                        'mobile_allowance':self.contract_id.mobile_allowance,
                        'allowance1':self.contract_id.allowance1,
                        'allowance2':self.contract_id.allowance2,
                        'allowance3':self.contract_id.allowance3,
                        'allowance4':self.contract_id.allowance4,
                        'deduction1':self.contract_id.deduction1,
                        'deduction2':self.contract_id.deduction2,
                        'deduction3':self.contract_id.deduction3,
                        'deduction4':self.contract_id.deduction4,
                        'deduction5':self.contract_id.deduction5,
                        'deduction6':self.contract_id.deduction6,
                        'deduction7':self.contract_id.deduction7,

                        'fuel_allowance':self.contract_id.fuel_allowance,
                           }))
        vals={
              'history_line':lines,
              }
        self.contract_id.write(vals)
        #~ self.contract_id.basic_percentage=self.basic
        self.contract_id.wage=self.wage
        self.contract_id.struct_id=self.stucture_id.id
        self.contract_id.effective_date=self.effective_date
        self.contract_id.mobile_allowance = self.mobile_allowance
        self.contract_id.fuel_allowance = self.fuel_allowance
        self.contract_id.allowance1 = self.allowance1
        self.contract_id.allowance2 = self.allowance2
        self.contract_id.allowance3= self.allowance3
        self.contract_id.allowance4 = self.allowance4
        self.contract_id.deduction1 = self.deduction1
        self.contract_id.deduction2 = self.deduction2
        self.contract_id.deduction3 = self.deduction3
        self.contract_id.deduction4 = self.deduction4
        self.contract_id.deduction5 = self.deduction5
        self.contract_id.deduction6 = self.deduction6
        self.contract_id.deduction7 = self.deduction7


class SalaryArrears(models.Model):
    _name = 'salary.arrear'
    _rec_name = 'company_id'

    state = fields.Selection([('draft', 'Draft'), ('arrear_cal', 'Arrear Calculation'), ('done', 'Done'),], default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self:self.env.user.company_id.id, readonly=True)
    from_date = fields.Date('Arrear Calculation from date')
    to_date = fields.Date('Arrear Calculation to date')
    check = fields.Boolean(string='Check the box before updating',help='set the field to True after submit button is clicked')
    employee_line_ids = fields.One2many('employee.line', 'arrear_id', string='Employees Details')
    filedata = fields.Binary('Download file', readonly=True)
    filename = fields.Char('Filename', size=64, readonly=True)

    # @api.multi
    def update_arrears(self):
        for line in self.employee_line_ids:
            line.contract_id.write({'is_arrear':True,'salary_arrear': line.arrears})
        self.write({'state':'done'})

    # @api.multi
    def compute_arrears_payslip(self, line, wage, payslip, diff_date):
        net = 0.0
        val = 0.0
        basic = 0.0
        wage = 0.0
        prev_basic = 0.0
        current_basic = 0.0
        prev_wage = 0.0
        current_wage = 0.0
        component_value={}
        #BASIC
        if line.contract_id.struct_id.code in ('BASE'):
            basic=line.contract_id.basic
            current_basic=basic
            for slip in payslip.line_ids:
                if slip.code == 'BASIC':
                    prev_basic = slip.amount
            #~ arr_basic = current_basic - prev_basic
            arr_basic = current_basic - prev_basic
            component_value.update({'basic': arr_basic,'prev_basic': prev_basic,'current_basic': current_basic})
        #HRA
        hra = 0.0
        prev_hra = 0.0
        current_hra = 0.0
        if line.contract_id.struct_id.code =='BASE':
            hra=line.contract_id.hra
            current_hra=hra
            for slip in payslip.line_ids:
                if slip.code == 'HRA':
                    prev_hra = slip.amount
            hra = current_hra - prev_hra
            component_value.update({'hra':hra,'prev_hra':prev_hra,'current_hra':current_hra})
        else:
            component_value.update({'hra': 0.0,'prev_hra': 0.0,'current_hra': 0.0,})

        #GROSS
        gross = 0.0
        current_gross = 0.0
        prev_gross = 0.0
        arr = 0.0
        for slip in payslip.line_ids:
            if slip.code == 'ARR':
                arr=slip.amount
        if line.contract_id.struct_id.code == 'BASE':
            gross = (line.contract_id.gross)
            current_gross = (current_basic + current_hra)
            for slip in payslip.line_ids:
                if slip.code == 'GROSS':
                    prev_gross = slip.amount
            current_gross = gross - prev_gross
            component_value.update({'current_gross': current_gross,'prev_gross':prev_gross,'gross':gross})
        else:
            component_value.update({'current_gross': 0.0,'prev_gross': 0.0,'gross': 0.0,})

        #ALLOWANCE
        allowance = 0.0
        current_allowance = 0.0
        prev_allowance = 0.0
        arr = 0.0
        for slip in payslip.line_ids:
            if line.contract_id.struct_id.code == 'BASE':
                current_allowance = line.contract_id.total_allowance
                for slip in payslip.line_ids:
                    if slip.code == 'TA':
                        prev_allowance = slip.amount
                allowance = current_allowance - prev_allowance
                component_value.update({'current_allowance': current_allowance,'prev_allowance':prev_allowance,'allowance':allowance})
            else:
                component_value.update({'current_allowance': 0.0,'prev_allowance': 0.0,'allowance': 0.0,})

        if line.contract_id.struct_id.code  == 'BASE':
            net = round((current_gross))
        test = ((net*12)/365)
        net = test * diff_date
        return net,component_value

    # @api.multi
    def compute_arrears(self):
        from_month = datetime.strptime(str(self.from_date), '%Y-%m-%d').month
        from_year = datetime.strptime(str(self.from_date), '%Y-%m-%d').year
        to_month = datetime.strptime(str(self.to_date), '%Y-%m-%d').month
        to_year = datetime.strptime(str(self.to_date), '%Y-%m-%d').year
        date = []
        obj_add = datetime.strptime(str(self.from_date), "%Y-%m-%d") + rdelta.relativedelta(days=-1)
        #~ from_day=datetime.strftime(obj_add,'%Y-%m-%d')'
        to_day=datetime.strptime(str(self.to_date),'%Y-%m-%d')
        join_diff = to_day - obj_add
        diff_date = join_diff.days
        output = StringIO()
        url="/home/ubuntu/odoo-11.0.post20180823/odoo/"
        workbook = xlsxwriter.Workbook(url + 'salary_arrears.xlsx')
        worksheet = workbook.add_worksheet()
        # creation of header
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'font_size': 12,
            'font_name': 'Liberation Serif',
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': 'white'})
        merge_format1 = workbook.add_format({
            'align': 'left',
            'font_name': 'Liberation Serif',
            'valign': 'vcenter', })
        merge_format2 = workbook.add_format({
            'bold': 1, 'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Liberation Serif',
            'underline': 'underline', })
        merge_format3 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'font_name': 'Liberation Serif',
            'valign': 'vcenter',
            'fg_color': 'gray'})

        merge_format4 = workbook.add_format({
            'align': 'right',
            'num_format': '#,##0.00',
            'font_name': 'Liberation Serif',
            'valign': 'vcenter', })
        merge_format5 = workbook.add_format({
            'align': 'right',
            'font_name': 'Liberation Serif',
            'bold': 1,
            'valign': 'vcenter',
        })

        money_format = workbook.add_format({
            'align': 'right',
            'font_name': 'Liberation Serif',
            'bold': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00'})
        worksheet.set_column('A:A', 8)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 25)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 25)
        worksheet.set_column('I:I', 15)
        worksheet.set_column('J:J', 20)
        worksheet.set_column('K:K', 20)
        worksheet.set_column('L:L', 15)
        worksheet.set_column('M:M', 20)
        worksheet.set_column('N:N', 20)
        worksheet.set_column('O:O', 15)
        worksheet.set_column('P:P', 20)
        worksheet.set_column('Q:Q', 20)
        worksheet.set_column('R:R', 15)
        worksheet.set_column('S:S', 20)
        worksheet.set_column('T:T', 20)
        worksheet.set_column('U:U', 15)
        worksheet.set_column('V:V', 20)
        worksheet.set_column('W:W', 20)
        worksheet.set_column('X:X', 15)
        worksheet.set_column('Y:Y', 20)
        worksheet.set_column('Z:Z', 20)
        worksheet.set_column('AA:AA', 15)
        worksheet.set_column('AB:AB', 20)
        worksheet.set_column('AC:AC', 20)
        worksheet.set_column('AD:AD', 15)
        worksheet.set_column('AE:AE', 20)
        worksheet.set_column('AF:AF', 20)
        worksheet.set_column('AG:AG', 15)
        worksheet.set_column('AH:AH', 15)

        #import datetime
        from_date = datetime.strptime(str(self.from_date), '%Y-%m-%d').strftime('%d-%m-%Y')
        to_date = datetime.strptime(str(self.to_date), '%Y-%m-%d').strftime('%d-%m-%Y')
        date_filter = ' Date from ' + from_date + ' To ' + to_date
        worksheet.merge_range('A2:E3', "Employee Arrear Sheet", merge_format2)
        worksheet.merge_range('A4:E4', date_filter, merge_format2)
        worksheet.write('A6', "S.No", merge_format3)
        worksheet.write('B6', "Employee Number", merge_format3)
        worksheet.write('C6', "Employee Name", merge_format3)
        worksheet.write('D6', "Contract", merge_format3)
        worksheet.write('E6', "Current", merge_format3)
        worksheet.write('F6', "Revised", merge_format3)
        worksheet.write('G6', "Difference", merge_format3)
        worksheet.write('D8', "Basic", merge_format3)
        worksheet.write('D9', "HRA", merge_format3)
        worksheet.write('D10', "Gross or Wage", merge_format3)


        for val in range(from_month, int(to_month)+1):
            date.append(str(datetime.strptime(str(self.from_date), '%Y-%m-%d').year) + '-0' + str(val) + '-' + '01')
        n=7
        c=1
        for line in self.employee_line_ids:
            employee_id=line.employee_id.id
            new_wage=line.contract_id.wage
            arrears = 0

            from_mn = from_month
            to_mn = to_month
            testing=0
            for wage in line.contract_id.history_line:
                if (line.contract_id.gross) == wage.old_wage:
                    testing +=1

            basic = 0
            wage = 0
            hra = 0 
            gross = 0
            epf = 0
            esi = 0
            net = 0
            if testing == 0:
                payslip_date = str(from_year)+'-'+str(from_mn)+'-'+'01'
                #pa
                payslip_id = self.env['hr.payslip'].search([('employee_id','=',line.employee_id.id),('date_from','=',payslip_date)], limit=1)
                #~ print 'payslipppppppppppppppp', payslip_id, payslip_id.date_from,payslip_date
                lop_day = payslip_id.lop_days
                #new_wage=round((30 - payslip_id.lop_days) * (line.contract_id.wage / 30))
                if payslip_id:
                    arrears_net, component_value = self.compute_arrears_payslip(line, new_wage, payslip_id, diff_date)
                    if component_value.get('basic'):
                        basic += component_value.get('basic')
                    arrears += arrears_net
                    from_mn += 1
                line.write({'arrears':abs(round(arrears)),
                })
                worksheet.write('A7', str(c), merge_format1)
                worksheet.write('B7' , line.employee_id.identification_id, merge_format1)
                worksheet.write('C7' , line.employee_id.name, merge_format1)
                worksheet.write('D7' , line.contract_id.name, merge_format1)
                worksheet.write('E8' , round(component_value['prev_basic']) if round(component_value['prev_basic']) else 0, merge_format4)
                worksheet.write('F8' , round(component_value['current_basic']) if round(component_value['current_basic']) else 0, merge_format4)
                worksheet.write('G8' , abs(round(component_value['basic'])) if round(component_value['basic']) else 0, merge_format4)
                worksheet.write('E9', round(component_value['prev_hra']) if round(component_value['prev_hra']) else 0, merge_format4)
                worksheet.write('F9' , round(component_value['current_hra']) if round(component_value['current_hra']) else 0, merge_format4)
                worksheet.write('G9' , abs(round(component_value['hra'])) if round(component_value['hra']) else 0, merge_format4)
                worksheet.write('E10' , round(component_value['prev_gross']) if round(component_value['prev_gross']) else 0, merge_format4)
                worksheet.write('F10' , round(component_value['gross']) if round(component_value['gross']) else 0, merge_format4)
                worksheet.write('G10' , abs(round(component_value['current_gross'])) if round(component_value['current_gross']) else 0, merge_format4)
                c += 1
                n += 1
        workbook.close()
        fo = open(url + 'salary_arrears.xlsx', "rb+")
        data = fo.read()
        out = base64.encodestring(data)
        self.write({'filedata': out, 'filename': 'salary_arrears.xlsx', 'state':'arrear_cal'})

    def get_salary(self,line,date):
        self.env.cr.execute('''SELECT l.code,l.total
                                FROM hr_payslip_line l
                                JOIN hr_payslip p ON l.slip_id = p.id
                                WHERE p.employee_id=%s AND p.date_from in %s
                                and l.code not in ('Wages','RCTC','FNGROSS') and l.total >0 '''%(line.employee_id.id,tuple(date)))
        salary = self.env.cr.dictfetchall()
        return salary

class EmployeeDetails(models.Model):
    _name = 'employee.line'

    arrear_id = fields.Many2one('salary.arrear', string="Salary Arrear")
    employee_id = fields.Many2one('hr.employee', 'Employee')
    contract_id = fields.Many2one('hr.contract', 'Contract')
    arrears = fields.Float(string="Amount", digits=(16, 3), readonly=True)
