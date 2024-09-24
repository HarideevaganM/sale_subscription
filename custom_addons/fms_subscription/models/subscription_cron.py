from odoo import api, fields, models, _
from datetime import date


# class SaleSubscriptionStage(models.Model):
#     _inherit = 'sale.subscription.stage'
#
#     category = fields.Selection(selection_add=[('hold', 'Hold'), ('cancel',)], ondelete={'hold': 'cascade'})

class SubscriptionStatus(models.Model):
    _inherit = 'sale.order'

    # @api.multi
    def subscription_invoice_status(self):
        subscription_list = self.env['sale.order'].search([('sale_type', '=', 'lease'),('stage_id.category', '=', 'progress'), ('template_id.code', '=', 'MON'), ('is_subscription', '=', True)])
        for status in subscription_list:
            status.invoice_status = "not_invoiced"


# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     def action_post(self):
#         res = super(AccountMove, self).action_post()
#         sale_order = self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
#         subscription = sale_order.order_line.mapped('subscription_id')
#         print("--------", sale_order,"----sale_order---\n")
#         print("--------", subscription,"----subscription---\n")
#         for sub in subscription:
#             progress_stage = self.env['sale.subscription.stage'].search([('category', '=', 'progress')], limit=1)
#             sub.write({'stage_id': progress_stage.id})
#         return res


