from odoo import api, exceptions, fields, models, _

class CompanyDetails(models.Model):
    _inherit = 'res.company'
    
    account_number = fields.Char("Account Number")
    bank_name = fields.Char("Bank Name")
    shift_code = fields.Char("Shift Code")
    acc_name = fields.Char("Account Name")
    branch_name = fields.Char("Branch Name")
    fax_new = fields.Char(string="Fax")
    logo1 = fields.Char(string="OPAL IVMS Logo")
    logo2 = fields.Char(string="Company Logo")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_id = fields.Char(string="Customer / Supplier Code")
    subscription_customer = fields.Selection([('reseller_customer', 'Reseller Customer'), ('normal_customer', 'Normal Customer')], string="Customer Category")
    is_reseller = fields.Boolean(string="Is Reseller", default=False)

