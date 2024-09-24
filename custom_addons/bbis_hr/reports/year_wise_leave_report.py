from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# Generating the year wise/ anniversary wise leave balance of every employee.
class YearWise_Leave_Report(models.AbstractModel):
    _name = 'report.bbis_hr.year_wise_leave_report1'
    _description = 'Year Wise Leave Report'

    def _get_year_wise_leaves_summary(self, data):
        self.env.cr.execute(
            """
            Select Employee_Name, Leave_Type, Available_Days, Sum(Leaves_Accrued) as Leaves_Accrued,
            Sum(COALESCE(Leaves_Taken,0)) as Leaves_Taken,Leave_Balance-Sum(COALESCE(Leaves_Taken,0)) as Leave_Balance 
            from (
            select employee.name as Employee_Name,
            holidays_status.name as Leave_Type,
            holidays_status.limit_days as Available_Days,
            case when holidays.type='add' then COALESCE(sum(number_of_days),0) end as Leaves_Accrued,
            case when holidays.type='remove' then sum(COALESCE(number_of_days_temp,0)) end as Leaves_Taken,
            case when holidays.type='add' then  COALESCE(sum(number_of_days),0) -
            case when holidays.type='remove' then sum(COALESCE(number_of_days_temp,0)) end end as Leave_Balance
            from hr_employee as employee
            left outer join hr_holidays_status as holidays_status on
            holidays_status.company_id = employee.company_id 
            left outer join  hr_holidays as holidays on
            holidays.holiday_status_id = holidays_status.id 
            and holidays.employee_id = employee.id
            where holidays.requested_date between '%s' and '%s'
            group by employee.name,holidays_status.name,holidays_status.limit_days,holidays.type
            order by employee.name ) as Leaves
            group by 
            Employee_Name, Leave_Type, Available_Days, Leave_Balance
            order by Employee_Name
          """ % (data['start_date'], data['end_date'])
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
        }

        return {
            'doc_model': 'leave.report.wizard',
            'date_range': date_range,
            'date': form_data['date_filter'],
            'start_date': start_date,
            'end_date': end_date,
            'data': self.get_year_wise_leaves_summary(final_data),
        }
