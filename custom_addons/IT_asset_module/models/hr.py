from odoo import models, fields, api, _, exceptions


class Employee(models.Model):
    _inherit = "hr.employee"

    branch = fields.Many2one('asset.branch', string="Branch")

    stock_location = fields.Many2one('stock.location', string="Stock Location", related='branch.stock_location')

    identification_id = fields.Char(string="Staff ID")

    _sql_constraints = [
        ('identification_id_unique',
         'UNIQUE(identification_id)',
         "Staff ID must be unique"),

        ('work_email_unique',
         'UNIQUE(work_email)',
         "Work Email must be unique"),

    ]
