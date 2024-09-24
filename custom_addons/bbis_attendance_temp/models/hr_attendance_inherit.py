from odoo import fields, models, api


class customize_attendancemodule(models.Model):
    _inherit = 'hr.attendance'
    # add remarks and office location in main attendance module
    remarks = fields.Char(string="Remarks")
    office_location = fields.Many2one(related="employee_id.working_branch", store=True, readonly=True)
    is_online_attendance = fields.Boolean()
