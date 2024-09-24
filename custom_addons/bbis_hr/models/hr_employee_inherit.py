# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BbisHrEmployee(models.Model):
    _inherit = 'hr.employee'

    working_branch = fields.Many2one('hr.working.branch')
    reset_leave = fields.Boolean(string="Leave Reset", store=True, default=False)
    current_leave_state = fields.Selection(
        selection_add=[
            ('submit', 'Submitted'),
            ('validate2', 'Manager Approval')
        ],
        ondelete={
            'submit': 'set default',
            'validate2': 'set default'
        }
    )
    is_on_leave = fields.Boolean(store=True, default=False)

    # we need to inherit below field and add accounts group for them to be able to post expense entry
    address_home_id = fields.Many2one(
        'res.partner', 'Private Address',
        help='Enter here the private address of the employee, not the one linked to your company.',
        groups="hr.group_hr_user,base.group_user")

    # we will use this field to not allow employee to see employee screen
    hr_private_id = fields.Many2one("hr.employee.private", compute="_compute_hr_private_id")

    # using compute method, this will always run, hence, will not allow employee to see employee screen
    def _compute_hr_private_id(self):
        id = self.env['hr.employee.private'].search([], limit=1).id
        return id

    #@api.multi
    def attendance_action_change(self):
        attendance = super(BbisHrEmployee, self).attendance_action_change()
        # we need to know if attendance is coming from online attendance
        attendance.is_online_attendance = True
        return attendance

    @api.onchange('user_id')
    def set_home_address_id(self):
        self.ensure_one()
        self.address_home_id = self.user_id.partner_id
