# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api


class HrHolidaysReport(models.Model):
    _name = "hr.holidays.report"
    _description = "HR Holidays Report"
    _auto = False
    _rec_name = 'holiday_id'
    _order = "request_date desc"

    holiday_id = fields.Many2one("hr.holidays")
    leave_type_id = fields.Many2one("hr.holidays.status")
    reason = fields.Char()
    employee_id = fields.Many2one("hr.employee")
    employee_name = fields.Char()
    job_id = fields.Many2one("hr.job")
    office_location_id = fields.Many2one("hr.working.branch")
    joining_date = fields.Date()
    request_date = fields.Datetime()
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    number_of_days = fields.Float()
    type = fields.Selection([('remove', 'Leave Request'), ('add', 'Allocation Request')], string='Request Type')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Officer Approval'),
        ('validate2', 'Manager Approval'),
        ('validate1', 'HR Approval'),
        ('refuse', 'Refused'),
        ('validate', 'Approved by CEO'),
    ], string='Status')

    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    line.holiday_id,
                    line.leave_type_id,
                    line.reason,
                    line.employee_id,
                    line.employee_name,
                    line.job_id,
                    line.office_location_id,
                    line.joining_date,
                    line.request_date,
                    line.date_from,
                    line.date_to,
                    line.type,
                    line.state,
                    line.number_of_days
                FROM (
                    SELECT
                        hl.id as holiday_id,
                        hl.holiday_status_id as leave_type_id,
                        hl.name as reason,
                        hl.employee_id,
                        emp.name as employee_name,
                        emp.job_id,
                        emp.working_branch as office_location_id,
                        emp.joining_date,
                        hl.requested_date as request_date,
                        hl.date_from,
                        hl.date_to,
                        hl.type,
                        hl.state,
                        hl.number_of_days
                    FROM hr_holidays hl
                    LEFT JOIN hr_employee emp on hl.employee_id = emp.id
                    LEFT JOIN hr_job job on job.id = emp.job_id
                    LEFT JOIN hr_working_branch br on br.id = emp.working_branch
                ) AS line
            )
            """ % self._table)

    # @api.model
    # def init(self):
    #     tools.drop_view_if_exists(self.env.cr, 'hr_holidays_report')
    #     self.env.cr.execute("""
    #         CREATE OR REPLACE VIEW hr_holidays_report AS (
    #             SELECT
    #                 row_number() OVER () AS id,
    #                 line.holiday_id,
    #                 line.leave_type_id,
    #                 line.reason,
    #                 line.employee_id,
    #                 line.employee_name,
    #                 line.job_id,
    #                 line.office_location_id,
    #                 line.joining_date,
    #                 line.request_date,
    #                 line.date_from,
    #                 line.date_to,
    #                 line.type,
    #                 line.state,
    #                 line.number_of_days
    #             FROM (
    #                 SELECT
    #                     hl.id as holiday_id,
    #                     hl.holiday_status_id as leave_type_id,
    #                     hl.name as reason,
    #                     hl.employee_id,
    #                     emp.name as employee_name,
    #                     emp.job_id,
    #                     emp.working_branch as office_location_id,
    #                     emp.joining_date,
    #                     hl.requested_date as request_date,
    #                     hl.date_from,
    #                     hl.date_to,
    #                     hl.type,
    #                     hl.state,
    #                     hl.number_of_days
    #                 FROM hr_holidays hl
    #                 LEFT JOIN hr_employee emp on hl.employee_id = emp.id
    #                 LEFT JOIN hr_job job on job.id = emp.job_id
    #                 LEFT JOIN hr_working_branch br on br.id = emp.working_branch
    #             ) as line
    #         )""")
