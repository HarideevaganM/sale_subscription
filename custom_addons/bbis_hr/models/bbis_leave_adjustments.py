from odoo import fields, models, api, _
from odoo import tools
from datetime import datetime


class bbisleave_adjustments(models.Model):
    _name = "process.leave.adjustments"
    _description = "Process Leave Adjustments"
    _order = "name desc"
    _auto = False
    _rec_name = 'name'

    emp_id = fields.Integer(string="Employee_ID")
    name = fields.Char(string="Employee Name")
    code = fields.Char(string="Employee Code")
    joining_date = fields.Date(string="Joining Date")
    holiday_status_id = fields.Integer(string="Holiday Status ID")
    holiday_type = fields.Char(string="Leave Type")
    remaining_leaves = fields.Float(string="Remaining Leaves")

    @api.model
    def process_adjustments(self):
        selected_records = self.env['process.leave.adjustments'].browse(self._context.get('active_ids'))
        for emp in selected_records:
            leave_value = -1 * emp.remaining_leaves
            self.env['hr.holidays'].create({
                'name': 'Yearly Adjustment',
                'state': 'validate',
                'payslip_status': 'False',
                'holiday_status_id': emp.holiday_status_id,
                'employee_id': emp.emp_id,
                'notes': 'Yearly Adjustment',
                'number_of_days_temp': emp.remaining_leaves,
                'number_of_days': leave_value,
                'report_note': datetime(datetime.today().year, datetime.today().month, 1),
                # 'date_from': datetime(datetime.today().year, datetime.today().month, 1),
                # 'date_to': datetime(datetime.today().year, datetime.today().month, last_day),
                'requested_date': datetime(datetime.today().year, datetime.today().month, 1),
                'meeting_id': '',
                'type': 'remove',
                'holiday_type': 'employee',
                'is_processed': 1
            })

            self.env['hr.holidays'].create({
                'name': 'Yearly Adjustment',
                'state': 'validate',
                'payslip_status': 'False',
                'holiday_status_id': emp.holiday_status_id,
                'employee_id': emp.emp_id,
                'notes': 'Yearly Adjustment',
                'number_of_days_temp': 15,
                'number_of_days': 15,
                'report_note': datetime(datetime.today().year, datetime.today().month, 1),
                # 'date_from': datetime(datetime.today().year, datetime.today().month, 1),
                # 'date_to': datetime(datetime.today().year, datetime.today().month, last_day),
                'requested_date': datetime(datetime.today().year, datetime.today().month, 1),
                'meeting_id': '',
                'type': 'add',
                'holiday_type': 'employee',
                'is_processed': 1
            })

            self.env['hr.employee'].browse(emp.emp_id).update({'reset_leave': False})

    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'process_leave_adjustments')
        self.env.cr.execute("""
            Create or Replace view process_leave_adjustments As (
                Select row_number() over (order by hr_employee.name) as id,
                hr_employee.id as emp_id, 
                hr_employee.name as name,
                hr_employee.employee_id as code, 
                hr_employee.joining_date as joining_date,
                hr_holidays_status.id as holiday_status_id,
                hr_holidays_status.name as holiday_type,
                sum(hr_holidays.number_of_days) as remaining_leaves  from hr_employee 
                Inner Join hr_holidays on hr_employee.id = hr_holidays.employee_id 
                Inner Join hr_holidays_status on hr_holidays.holiday_status_id = hr_holidays_status.id
                where hr_employee.active = True and hr_employee.reset_leave = True
                and hr_holidays_status.id = 2
                group by hr_employee.id,hr_employee.employee_id, hr_employee.name, hr_employee.joining_date,
                hr_holidays.holiday_status_id,hr_holidays_status.name,hr_holidays_status.id
                ) """)


