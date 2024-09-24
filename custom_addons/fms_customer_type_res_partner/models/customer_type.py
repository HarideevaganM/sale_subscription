from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_types = fields.Selection([
        ('opal customer', 'OPAL Customer'),
        ('non opal customer', 'NON OPAL Customer')
        ], string='Customer Type')
    industry_id1 = fields.Many2one("industry.name", string="Industry")


class IndustryName(models.Model):
    _name = "industry.name"

    name = fields.Char("Name")
