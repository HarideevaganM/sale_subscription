from odoo import fields, models, api


class hr_holidays_statusinherit(models.Model):
    _inherit = 'hr.holidays.status'
    # Add the limit days in leave type. This is the maximum limit of leaves for an employee in the anniversary.
    days_per_year = fields.Float(string="Days Balance Yearly")
    is_annual = fields.Boolean(string="Is Annual Leave")
    is_allocation_per_year = fields.Boolean(string="Is Allocation Yearly")
    days_per_month = fields.Float(string="Days Balance Monthly")
    days_carry_over = fields.Float(string="Days Unused Leave Carry Over", help="Days carried over for unused leave.")


