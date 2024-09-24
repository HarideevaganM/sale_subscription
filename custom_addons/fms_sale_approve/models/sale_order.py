# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Company(models.Model):
    _inherit = 'res.company'

    so_order_approval = fields.Boolean("Order Approval")
    so_min_validation_amount = fields.Monetary(string='Sale Minimum Amount', default=5000,
        help="Minimum amount for which a double validation is required")
    so_max_validation_amount = fields.Monetary(string='Sale Maximum Amount', default=15000,
        help="Maximum amount for which a double validation is required")

class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    state = fields.Selection(
        selection_add=[
            ('approval', 'Approval')
        ],
        ondelete={
            'approval': 'set default'
        }
    )

    def action_approved(self):
        so_min_validation_amount = self.company_id.so_min_validation_amount
        so_max_validation_amount = self.company_id.so_max_validation_amount
        # user
        sale_salesman = self.env.user.has_group('sales_team.group_sale_salesman')
        sale_salesman_all = self.env.user.has_group('sales_team.group_sale_salesman_all_leads')
        sale_manager = self.env.user.has_group('sales_team.group_sale_manager')
        sale_super_user = self.env.user.has_group('fms_sale_approve.group_sale_super_user')
        # condition
        condition_1 = (float(so_min_validation_amount) <= self.amount_total) and (float(so_max_validation_amount) >= self.amount_total)
        # logic
        if (not sale_super_user and sale_salesman and not sale_salesman_all and not sale_manager) and float(so_min_validation_amount) <= self.amount_total:
            raise UserError(_('You can not approve this sale order'))
        if (not sale_super_user and sale_salesman_all and not sale_manager) and float(so_min_validation_amount) <= self.amount_total:
            raise UserError(_('You can not approve this sale order'))
        if not sale_super_user and sale_manager and self.amount_total >= float(so_max_validation_amount):
            raise UserError(_('You can not approve this sale order'))
        if not sale_super_user and sale_manager and condition_1:
            self.action_confirm()
        if sale_manager and sale_super_user and self.amount_total >= float(so_min_validation_amount):
            self.action_confirm()
        return True

    #@api.multi
    def action_submit(self):
        res = super(SaleOrderInherit, self).action_submit()
        # amount
        so_min_validation_amount = self.company_id.so_min_validation_amount
        so_max_validation_amount = self.company_id.so_max_validation_amount
        # user
        condition_1 = (float(so_min_validation_amount) <= self.amount_total) and (float(so_max_validation_amount) >= self.amount_total)
        condition_2 = self.amount_total >= float(so_min_validation_amount)
        # check
        if (float(so_min_validation_amount) <= self.amount_total):
            self.write({'state': 'approval'})
        else:
            self.write({'state': 'submit'})
        return res

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    so_order_approval = fields.Boolean(related='company_id.so_order_approval' , string='Order Approval')
    so_min_validation_amount =  fields.Monetary(related='company_id.so_min_validation_amount', string="Minimum Amount", currency_field='company_currency_id')
    so_max_validation_amount =  fields.Monetary(related='company_id.so_max_validation_amount', string="Maximum Amount", currency_field='company_currency_id')

    def _get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            so_order_approval=self.env['ir.config_parameter'].sudo().get_param('so_order_approval'),    
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('so_order_approval', self.so_order_approval)
