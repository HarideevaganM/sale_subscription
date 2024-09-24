from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# Generating the employee wise leave balance in a chosen criteria.
class EmployeeWise_LeaveReport(models.AbstractModel):
    _name = 'report.bbis_hr.employee_wise_leave_report1'
    _description = 'Employee Wise Leave Report'

    def _get_employee_wise_leaves_summary(self, data):
        self.env.cr.execute(
            """
            Select Employee_Name as Employee_Name,Join_Date as Join_Date,Department as Department,
            Job_Position as Job_Position, Leave_Type as Leave_Type, Maximum_Available as Maximum_Available, 
            COALESCE(sum(Leaves_Accrued),0) as Leaves_Accrued,
            COALESCE(sum(Leaves_Taken),0) as Leaves_Taken,
            COALESCE(sum(Leaves_Accrued),0) -  COALESCE(sum(Leaves_Taken),0) as Leave_Balance
            from (  Select employee.name as Employee_Name, joining_date as Join_Date, 
                    department.name as Department, job.name as Job_Position,
                    holidays_status.name as Leave_Type,
                    holidays_status.limit_days as Maximum_Available,
                    case when number_of_days>0 then number_of_days end as Leaves_Accrued,
                    case when number_of_days<0 then number_of_days_temp end as Leaves_Taken
                    from hr_employee as employee
                    left outer join hr_department as department on
                    employee.department_id = department.id left outer join hr_job as job
                    on employee.job_id = job.id
                    left outer join hr_holidays_status as holidays_status on
                    holidays_status.company_id = employee.company_id 
                    left outer join  hr_holidays as holidays on
                    holidays.holiday_status_id = holidays_status.id 
                    and holidays.employee_id = employee.id
            where holidays.requested_date between '%s' and '%s' and employee.id = '%s'
            order by employee.name ) hoidays
            group by Employee_Name,Leave_Type,Join_Date,Maximum_Available,Department,Job_Position
          """ % (data['start_date'], data['end_date'], data['employee_id'])
        )

        yearly_leaves = self.env.cr.dictfetchall()
        return yearly_leaves

    @api.model
    def _get_report_values(self, docids, data=None):

        form_data = data['form']

        date_now_str = datetime.now().strftime('%d/%m/%Y')
        date_now = datetime.strptime(date_now_str, '%d/%m/%Y')

        if form_data['date_filter'] == 'this_year':
            this_year = datetime.now()
            start_date = datetime.strftime(this_year, '%Y-01-01')
            end_date = datetime.strftime(this_year, '%Y-12-31')
            date_range = date_now.month
        elif form_data['date_filter'] == 'last_year':
            last_year = datetime.now() - relativedelta(years=1)
            start_date = datetime.strftime(last_year, '%Y-01-01')
            end_date = datetime.strftime(last_year, '%Y-12-31')
            date_range = 12
        else:
            start_date = datetime.strptime(form_data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(form_data['end_date'], '%Y-%m-%d')
            date_range = (end_date.month - start_date.month) + 1

        final_data = {
            'start_date': start_date,
            'end_date': end_date,
            'date': form_data['date_filter'],
            'date_range': date_range,
            'employee_id': data['employee_id']
        }

        return {
            'doc_model': 'leave.report.wizard',
            'date_range': date_range,
            'date': form_data['date_filter'],
            'start_date': start_date,
            'end_date': end_date,
            'data': self.get_employee_wise_leaves_summary(final_data),
        }
