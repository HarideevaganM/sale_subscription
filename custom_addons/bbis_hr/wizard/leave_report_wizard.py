from odoo import models, fields, api
from odoo.exceptions import ValidationError


# Leave report selection wizard.
class LeaveReportWizard(models.TransientModel):
    _name = 'leave.report.wizard'
    _description = 'Leave Reports'

    report_name = fields.Selection([('leaves_summary', "Leaves Summary"),
                                    ('schedule_leave_balances', "Schedule Of Employees Leave Balances")])

    employee_id = fields.Many2one('hr.employee', string="Employee Name")

    date_filter = fields.Selection([('this_year', 'This Year'),
                                    ('last_year', 'Last Year'),
                                    ('joining_date', 'Joining Date'),
                                    ('custom', 'Custom')], string="Date Filter", default='this_year')
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    leave_type_id = fields.Many2one("hr.holidays.status")

    @api.onchange('report_name')
    def set_leave_type_id(self):
        self.ensure_one()

        # make sure to add annual leave type if they selected schedule leave balances
        if self.report_name == 'schedule_leave_balances':
            l_type = self.env['hr.holidays.status'].search([('is_annual', '=', True)], limit=1)
            self.leave_type_id = l_type.id

    #@api.multi
    def print_reports(self):
        data = {
            'model': 'leave.report.wizard',
            'form': self.read()[0],
            'employee_id': self.employee_id.id
        }

        template = ''

        for reports in self:
            if reports.report_name == 'all_employees':
                template = 'bbis_hr.year_wise_leave_report'
            elif reports.report_name == 'employee_wise':
                template = 'bbis_hr.employee_wise_leave_report'

        if template == '':
            raise ValidationError('Please Select One Report')
        return self.env.ref(template).report_action(self, data=data)

    #@api.multi
    def print_xlsx_report(self):
        data = {
            'employee_id': self.employee_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'form': self.read()[0]
        }

        # throw error if they select filter date by joining date and no employee has been selected
        if self.date_filter == 'joining_date' and not self.employee_id:
            raise ValidationError("You can only filter date by Joining date for single Employee.")

        if self.report_name == 'employee_wise':
            return self.env.ref('bbis_hr.leave_report_xlsx').report_action(self, data=data)

        if self.report_name == 'leaves_summary':
            return self.env.ref('bbis_hr.schedule_leave_summary_xlsx').report_action(self, data=[])

        if self.report_name == 'schedule_leave_balances':
            # show an error if they selected leave type that is not annual
            if not self.leave_type_id.is_annual:
                raise ValidationError("Sorry! This report is only for Annual Leave Type.")

            return self.env.ref('bbis_hr.schedule_leave_report_xlsx').report_action(self, data=[])
