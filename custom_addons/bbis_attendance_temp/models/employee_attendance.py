from odoo import fields, models, api
from odoo import tools


class employee_attendance(models.Model):
    _name = 'employee.attendance'
    _description = 'Employee Attendance'
    _order = "check_in asc"
    _auto = False
    _rec_name = 'date'

    name = fields.Many2one('hr.employee', string="Employee Name")
    date = fields.Datetime(string="Date")
    check_in = fields.Datetime(string="Check In/ Leave From")
    check_out = fields.Datetime(string="Check Out/ Leave To")
    remarks = fields.Char(string="Remarks")
    type = fields.Char(string="Type")
    day = fields.Char(string='Day')
    short_name = fields.Char(string='Type')
    status = fields.Integer(string='Status')
    month = fields.Char(string='Month')

    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'employee_attendance')
        self.env.cr.execute("""
                   CREATE OR REPLACE VIEW employee_attendance AS (
                       Select 
                       row_number() over (order by employee.name) as id,
                       employee.name,
                       employee.date,
                       employee.check_in,
                       employee.check_out,
                       employee.remarks,
                       employee.type,
                       employee.day,
                       employee.short_name,
                       employee.status,
                       employee.month
                   From
                   (SELECT
                       attendance.employee_id as name,
                       attendance.check_in AS date,
                       attendance.check_in as check_in,
                       attendance.check_out as check_out,
                       attendance.remarks as remarks,
                       'Attendance'::text AS type,
                       date_part('month', attendance.check_in) as day,
                       'A' as short_name,
                       1 as status,
                       TO_CHAR(attendance.check_in, 'Month') as month
                   FROM hr_attendance attendance
                        JOIN hr_employee employee ON attendance.employee_id = employee.id
                   UNION ALL
                   SELECT
                           holidays.employee_id as name,
                           holidays.date_from AS date,
                           (generate_series(holidays.date_from,holidays.date_to , '1 day'::interval))::date AS check_in,
                           (generate_series(holidays.date_from,holidays.date_to , '1 day'::interval))::date AS check_out,
                           employee.notes AS remarks,
                           'Leave'::text AS type,
                           date_part('month',holidays.date_from) as day,
                           'L' as short_name,
                           1 as status,
                           TO_CHAR(holidays.date_from, 'Month') as month
                   FROM hr_holidays holidays
                        JOIN hr_employee employee ON holidays.employee_id = employee.id) employee
                   )""")


