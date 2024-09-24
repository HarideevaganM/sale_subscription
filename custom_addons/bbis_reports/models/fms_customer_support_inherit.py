# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BbisFmsCustomerSupportInherit(models.Model):
    _inherit = 'fms.customer.support'

    customer_class = fields.Selection(related='partner_id.customer_class', string='Customer Class', readonly=True)
    approve_customer_x = fields.Boolean(default=False, copy=False)

    def action_approve_customer_x(self):
        self.write({'approve_customer_x': True})

    @api.onchange('customer_class', 'partner_id')
    def reset_approve_customer_class(self):
        self.write({'approve_customer_x': False})

    #@api.multi
    def button_confirm(self):
        if self.customer_class == 'class_x' and not self.approve_customer_x:
            raise ValidationError("Sorry! Customers with Class X needs approval before you can create this order.")

        return super(BbisFmsCustomerSupportInherit, self).button_confirm()

    # inherit this method and include default payment term
    def prepair_sale_order(self):
        res = super(BbisFmsCustomerSupportInherit, self).prepair_sale_order()
        payment_term = self.partner_id.property_payment_term_id
        res['payment_term_id'] = payment_term.id if payment_term else False
        return res

    # Inherited the Date field for displaying the current date in Customer Support Screen.
    date = fields.Datetime(string="Create Date", default=fields.Datetime.now)
