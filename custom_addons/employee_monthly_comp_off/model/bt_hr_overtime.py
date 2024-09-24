# -*- coding: utf-8 -*-

from odoo import fields, api, models, _
from datetime import date,datetime
import datetime
import calendar
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta


class BtHrOvertime(models.Model):   
    _name = "bt.hr.overtime"
    _description = "Bt Hr Overtime" 
    _rec_name = 'employee_id'
    _order = 'id desc'
    
    employee_id = fields.Many2one('hr.employee', string="Employee")
    manager_id = fields.Many2one('hr.employee', string='Manager')
    start_date = fields.Datetime('Date')
    overtime_hours = fields.Float('Incentives Hours', default=0.0)
    notes = fields.Text(string='Notes')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('refuse', 'Refused'),
           ('validate', 'Paid'), ('cancel', 'Cancelled')], default='draft', copy=False)
    attendance_id = fields.Many2one('hr.attendance', string='Attendance')
    overtime_type=fields.Selection([
        ('dayswise','Dayswise'),
        ('hourwise','Hourwise')
    ], string='Overtime Type', default='dayswise')
    overtime_days= fields.Float('Payable Days', default=0.0)
    total_overtime_days= fields.Float('Payable Days for Current Month', default=0.0)
    previous_month_allocated_days= fields.Float('Previous Month allocated Days', default=0.0)
    bal_leave_cf= fields.Float('Balance C/F in Next Month', default=0.0)
    adjusted_leave=fields.Float('Adjusted Comp Off Against Leaves', default=0.0)
    total_days= fields.Float('Total Days', default=0.0)
    overtime_amount=fields.Float('Incentive Salary', compute='calculate_ot')
    overtime_amount_day=fields.Float('Incentive Salary', compute='calculate_ot')
    per_day_sal=fields.Float('Per Day Salary', compute='get_salary_details')
    per_hour_sal=fields.Float('Per Hour Salary', compute='get_salary_details')
    gross_sal=fields.Float('Gross Salary', default=0.0)
    select_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string="Month")

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.manager_id=self.employee_id.parent_id.id

    # to update no of days in leaves master
    @api.onchange('overtime_days')
    def onchange_overtime_days(self):
        if self.overtime_days:
            current_date=datetime.datetime.now()
            previous_allocated_leave_id = self.env['hr.holidays'].search(
                [('type', '=', 'add'), ('employee_id', '=', self.employee_id.id),
                 ('select_month', '=', str(current_date.month - 2))], limit=1)
            current_allocated_leave_id = self.env['hr.holidays'].search(
                [('type', '=', 'add'), ('employee_id', '=', self.employee_id.id),
                 ('select_month', '=', str(current_date.month - 1))], limit=1)
            if previous_allocated_leave_id:
                if previous_allocated_leave_id.number_of_days_temp >= self.overtime_days:
                    previous_allocated_leave_id.write({'number_of_days_temp': previous_allocated_leave_id.number_of_days_temp-self.overtime_days})
                elif previous_allocated_leave_id.number_of_days_temp < self.overtime_days:
                    pending_days= self.overtime_days - previous_allocated_leave_id.number_of_days_temp
                    previous_allocated_leave_id.write(
                        {'number_of_days_temp': previous_allocated_leave_id.number_of_days_temp - (self.overtime_days-pending_days)})
                    current_allocated_leave_id.write(
                        {'number_of_days_temp': current_allocated_leave_id.number_of_days_temp - pending_days})
                    self.bal_leave_cf= current_allocated_leave_id.number_of_days_temp

    # to get per day and per hour salary
    #@api.multi
    def _get_salary_details(self):
        for incentive in self:
            per_day_salary, per_hour_sal = 0.0, 0.0
            payslip_id = self.env['hr.payslip'].search([('employee_id', '=', incentive.employee_id.id)], limit=1)
            contract_id = self.env['hr.contract'].search(
                [('employee_id', '=', incentive.employee_id.id), ('state', '=', 'open')])
            if payslip_id:
                gross_sal = payslip_id.line_ids.filtered(lambda l: l.category_id.name == 'GROSS')
                incentive.gross_sal=gross_sal.total
                if payslip_id.no_of_days:
                    per_day_salary = gross_sal.total / payslip_id.no_of_days
                    incentive.per_day_sal = per_day_salary
            if contract_id.work_hours:
                incentive.per_hour_sal = per_day_salary / contract_id.work_hours

    # to calculate salary dayswise or hourwise
    @api.depends('overtime_type','overtime_hours','overtime_days','total_overtime_days','total_days')
    def calculate_ot(self):
        for incentive in self:
            per_day_salary, per_hour_sal=0.0, 0.0
            payslip_id=self.env['hr.payslip'].search([('employee_id','=',incentive.employee_id.id)],limit=1)
            contract_id=self.env['hr.contract'].search([('employee_id','=',incentive.employee_id.id),('state','=','open')])
            if payslip_id:
                gross_sal=payslip_id.line_ids.filtered(lambda l:l.category_id.name=='GROSS')
                if payslip_id.no_of_days:
                    per_day_salary=gross_sal.total/payslip_id.no_of_days
            if incentive.overtime_type=='dayswise':
                incentive.overtime_amount_day=per_day_salary*incentive.overtime_days
            else:
                if contract_id.work_hours:
                    per_hour_sal=per_day_salary/contract_id.work_hours
                    incentive.overtime_amount=per_hour_sal*incentive.overtime_hours

    # to get last day of month
    def last_day_of_month(self,year,month):
        last_days = [31, 30, 29, 28, 27]
        for i in last_days:
            try:
                end = datetime.datetime(year, month, i)
            except ValueError:
                continue
            else:
                return end.date()
        return None

    # to get first day of month
    def first_day_of_month(self, select_date):
        first_day= select_date + relativedelta(day=1)
        first_date= datetime.datetime.strftime(first_day, '%Y-%m-%d %H:%M:%S')
        return first_date

    @api.model
    def run_overtime_scheduler(self):
        """ This Function is called by scheduler. """
        employee_keys, incentive_keys, overtime_keys,  = {}, {}, {}
        emp_dict, incentive_dict,  = {}, {}
        current_date = datetime.datetime.now()
        previous_month_last_date=self.last_day_of_month(current_date.year, current_date.month-1)
        last_date= datetime.datetime.strftime(previous_month_last_date, '%Y-%m-%d %H:%M:%S')
        first_date=self.first_day_of_month(previous_month_last_date)
        attend_signin_ids = self.env['hr.attendance'].search([('employee_id.overtime','=', True),('check_in','>=',first_date), ('check_in','<=',last_date)])
        comp_off_id = self.env['hr.holidays.status'].search([('name', '=', 'Comp Off')])
        print("comp_off_idcomp_off_idcomp_off_idcomp_off_id", comp_off_id)
        if attend_signin_ids:
            for attendance in attend_signin_ids:
                attendance_date = datetime.datetime.strptime(attendance.check_in, '%Y-%m-%d %H:%M:%S').date()
                day_attend = attendance_date.weekday()
                week_day = calendar.day_name[day_attend]
                month=datetime.datetime.strftime(attendance_date, '%m')
                if week_day == 'Sunday':
                    if attendance.employee_id.id not in employee_keys:
                        emp_dict={
                                'name': 'Compensatory Leave',
                                'holiday_status_id': comp_off_id.id,
                                'department_id':attendance.employee_id.department_id.id,
                                'number_of_days_temp': 1.00,
                                'type': 'add',
                                'select_month':month,
                                'employee_id': attendance.employee_id.id
                            }
                        employee_keys[attendance.employee_id.id] = emp_dict
                    else:
                        if (attendance.employee_id.id) in employee_keys:
                            emp_data_dict=employee_keys.get(attendance.employee_id.id)
                            emp_data_dict['number_of_days_temp']=emp_data_dict['number_of_days_temp']+1.00

            # to create allocated leave request
            for emp_id_key, value in employee_keys.items():
                leave_id = self.env['hr.holidays'].create(value)
                if leave_id:
                    leave_id.action_approve()
                    # to create incentive record
                    previous_allocated_leave_id = self.env['hr.holidays'].search(
                        [('type', '=', 'add'), ('employee_id', '=', emp_id_key),
                         ('select_month', '=', str(current_date.month - 2)),('holiday_status_id.name','=','Comp Off')],limit=1)
                    values={
                            'employee_id': leave_id.employee_id.id or False,
                            'manager_id': leave_id.employee_id.id and leave_id.employee_id.parent_id.id and leave_id.employee_id.parent_id.id or False,
                            'previous_month_allocated_days': previous_allocated_leave_id.number_of_days_temp,
                            'overtime_type': 'dayswise',
                            'select_month': leave_id.select_month,
                            # 'attendance_id': attendance.id,
                            'total_days': leave_id.number_of_days_temp+previous_allocated_leave_id.number_of_days_temp,
                            'total_overtime_days':leave_id.number_of_days_temp
                        }
                    incentive_id = self.env['bt.hr.overtime'].create(values)
            # to create individual leave request
            for attendance in attend_signin_ids:
                attendance_date = datetime.datetime.strptime(attendance.check_in, '%Y-%m-%d %H:%M:%S').date()
                day_attend = attendance_date.weekday()
                week_day = calendar.day_name[day_attend]
                month = datetime.datetime.strftime(attendance_date, '%m')
                if week_day == 'Sunday':
                    vals = {
                        'name': 'Compensatory Leave',
                        'holiday_status_id': comp_off_id.id,
                        'date_from': attendance.check_in,
                        'date_to': attendance.check_out,
                        'select_month': month,
                        'number_of_days_temp': 1.00,
                        'type': 'remove',
                        'employee_id': attendance.employee_id.id,
                        'department_id':attendance.employee_id.department_id.id,
                    }
                    request_leave_id = self.env['hr.holidays'].create(vals)
                    # if request_leave_id:
                    #     request_leave_id.action_approve()
        # to create incentive according to employee check in , check out time and working schedule
        attend_ids = self.env['hr.attendance'].search([('check_in','>=',first_date), ('check_in','<=',last_date)])
        if attend_ids:
            for obj in attend_signin_ids:
                start_date = datetime.datetime.strptime(obj.check_in, DEFAULT_SERVER_DATETIME_FORMAT)
                if obj.check_out:
                    attend_date=start_date.date()
                    month = datetime.datetime.strftime(attend_date, '%m')
                    end_date = datetime.datetime.strptime(obj.check_out, DEFAULT_SERVER_DATETIME_FORMAT)
                    difference = end_date - start_date
                    hour_diff = str(difference).split(':')[0]
                    min_diff = str(difference).split(':')[1]
                    tot_diff = hour_diff + '.' + min_diff
                    actual_working_hours = float(tot_diff)
                    contract_obj = self.env['hr.contract'].search([('employee_id', '=', obj.employee_id.id),('work_hours','!=',0)])
                    for contract in contract_obj:
                        working_hours = contract.work_hours
                        if actual_working_hours > working_hours:
                            overtime_hours = actual_working_hours - working_hours
                            if obj.employee_id.id not in incentive_keys:
                                incentive_dict=({
                                        'employee_id':obj.employee_id and obj.employee_id.id or False,
                                        'manager_id' : obj.employee_id and obj.employee_id.parent_id and obj.employee_id.parent_id.id or False,
                                        'start_date' : obj.check_in,
                                        'overtime_type':'hourwise',
                                        'select_month': month,
                                        'overtime_hours': round(overtime_hours,2),
                                        'attendance_id': obj.id,
                                })
                                incentive_keys[obj.employee_id.id] = incentive_dict
                            else:
                                if (obj.employee_id.id) in incentive_keys:
                                    incentive_data_dict = incentive_keys.get(obj.employee_id.id)
                                    incentive_data_dict['overtime_hours'] = incentive_data_dict['overtime_hours'] + round(overtime_hours,2)
            for incentive_data_key, value in incentive_keys.items():
                self.env['bt.hr.overtime'].create(value)

                    
    #@api.multi
    def action_submit(self):
        return self.write({'state':'confirm'})
        
    #@api.multi
    def action_cancel(self):
        return self.write({'state':'cancel'})
        
    #@api.multi
    def action_approve(self):
        return self.write({'state':'validate'})
    
    #@api.multi
    def action_refuse(self):
        return self.write({'state':'refuse'})
        
    #@api.multi
    def action_view_attendance(self):
        attendances = self.mapped('attendance_id')
        action = self.env.ref('hr_attendance.hr_attendance_action').read()[0]
        if len(attendances) > 1:
            action['domain'] = [('id', 'in', attendances.ids)]
        elif len(attendances) == 1:
            action['views'] = [(self.env.ref('hr_attendance.hr_attendance_view_form').id, 'form')]
            action['res_id'] = self.attendance_id.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
        

class Contract(models.Model):
    _inherit = 'hr.contract'
    
    work_hours = fields.Float(string='Working Hours', default=0.0, related='resource_calendar_id.total_working_hrs', store=True)
    
    
class HrAttendance(models.Model):
    _inherit = "hr.attendance" 
    
    overtime_created = fields.Boolean(string='Overtime Created', default=False, copy=False)
