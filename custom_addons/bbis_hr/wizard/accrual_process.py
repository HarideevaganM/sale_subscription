from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class AccrualProcess(models.TransientModel):
    """
    Manual accrual process for annual leaves in month wise. Or use for bulk update.
    """
    _name = 'accrual.process'
    _description = 'Accrual Process'

    name = fields.Text(string='Description', required=True)
    date = fields.Datetime(string='Date')

    month = fields.Char(string='Processing Month')
    employee_ids = fields.Many2many('hr.employee', 'accrual_process_emp_rel', 'accrual_process_id', 'employee_id', string='Employee Name', required=True)
    value = fields.Float(string='No Of Days')
    state = fields.Selection([('P', 'Processed'),
                              ('A', 'Approved')],
                             string='Status')
    all_employees = fields.Boolean(string='All Employees')
    leave_type = fields.Many2one('hr.holidays.status', string='Leave Type', required=True)
    date_from = fields.Date(default=fields.Date.today)
    # date_to = fields.Date()
    is_allocation_per_year = fields.Boolean(related="leave_type.is_allocation_per_year")
    year = fields.Integer(default=datetime.now().year)
    emp_len = fields.Integer(compute='_compute_emp_len')

    @api.depends('employee_ids')
    def _compute_emp_len(self):
        for r in self:
            r.emp_len = len(self.employee_ids)

    @api.onchange('leave_type')
    def set_value(self):
        per_month, per_year = self.leave_type.days_per_month, self.leave_type.days_per_year
        is_per_year = self.leave_type.is_allocation_per_year
        self.value = per_month if not is_per_year else per_year

    # Processing the leaves for employees. Wizard View.
    #@api.multi
    def create_accrual_process(self):
        # init needed variables
        date_from, date_to = False, False

        # we need to replace date from and date to time since we hr might not noticed that the time are the same
        if self.date_from:
            date_from = datetime.strptime(self.date_from, "%Y-%m-%d").replace(hour=4)
            date_to = date_from.replace(hour=13)

        if not self.value:
            raise ValidationError("Please make sure to add No of Days.")

        if self.all_employees:
            employees_list = self.env['hr.employee'].search([])
        else:
            # Do not process if there's no selected employees
            if not self.employee_ids:
                raise ValidationError("Please make sure to add employee.")

            employees_list = self.employee_ids

        # before actually adding leaves, check first if all employees has joining date
        for emp_id in employees_list:
            # Check first if leave type selected leave allocation is per year.
            if self.leave_type.is_allocation_per_year:
                # get the employee joining date and use that to compute date_from and date_to
                if not emp_id.joining_date:
                    raise ValidationError("You need to add Joining Date of %s." % emp_id.name)

        for emp_id in employees_list:
            # Check first if leave type selected leave allocation is per year.
            if self.leave_type.is_allocation_per_year and (self.emp_len > 1 or self.all_employees):
                # get the employee joining date and use that to compute date_from and date_to
                joining_date_str = emp_id.joining_date
                joining_date = datetime.strptime(joining_date_str, "%Y-%m-%d")

                # get month and year
                day, month = joining_date.day, joining_date.month

                # get current date to get current year and replace the month and day of employee joining date
                date_from = datetime.now().replace(day=day, month=month, year=self.year, hour=4)
                date_to = date_from.replace(hour=13)

            if self.value < 0:
                entry_type = 'remove'
                number_of_days = self.value * -1
            else:
                entry_type = 'add'
                number_of_days = self.value
            leave = self.env['hr.holidays'].create({
                'name': self.name,
                'state': 'validate',
                'payslip_status': False,
                'employee_id': emp_id.id,
                'notes': 'Process Leaves',
                'number_of_days_temp': number_of_days,
                'report_note': self.month,
                'meeting_id': '',
                'type': entry_type,
                'holiday_type': 'employee',
                'holiday_status_id': self.leave_type.id,
                'date_from': date_from,
                'date_to': date_to,
                'requested_date': datetime.now(),
                'is_processed': 1
            })

            leave.message_post("Manual Leave Allocation Process")
