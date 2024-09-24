from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError,ValidationError
from dateutil.relativedelta import relativedelta

class GenerateSubscriptionWizard(models.TransientModel):
    _name = "generate.subscription.wizard"

    partner_id = fields.Many2one("res.partner", string="Customer")
    subscription_ids = fields.Many2many("sale.subscription", string="Subscriptions")

    # @api.model
    # def default_get(self, fields):
    #     res = super(GenerateSubscriptionWizard, self).default_get(fields)
    #     active_ids = self.env.context.get('active_ids', False)
    #     if active_ids:
    #         subscription_ids = self.env['sale.subscription'].browse(active_ids)
    #         partner = subscription_ids.mapped('partner_id')
    #         if len(partner.ids) > 1:
    #             raise UserError(_('Partner must be same for generate of quote'))
    #         res.update({'partner_id': subscription_ids.mapped('partner_id').id, 'subscription_ids': subscription_ids.ids})
    #     return res

    # @api.multi
    def create_quotation(self):
        sale_order_obj = self.env['sale.order']
        sub_vals = []
        vehicle_vals = []
        # set vehicle
        for line in self.subscription_ids.filtered(lambda x: x.vehicle_number):
            sub_start_date = fields.Date.from_string(line.end_date)
            if not sub_start_date:
                raise UserError(_('Please define period end date "%s".') % (line.display_name,))
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            subscription_period = relativedelta(**{periods[line.recurring_rule_type]: line.recurring_interval})
            period_start_date = sub_start_date + relativedelta(days=1)
            sub_end_date = period_start_date + subscription_period
            period_end_date = sub_end_date - relativedelta(days=1)
            veh_vals = {
                            'serial_no_id': line.vehicle_number.device_serial_number_id and line.vehicle_number.device_serial_number_id.id,
                            'device_id': line.vehicle_number.device_id and line.vehicle_number.device_id.id,
                            'vehicle_id': line.vehicle_number.id,
                            'partner_id': line.partner_id and line.partner_id.id,
                            'installation_date': line.vehicle_number.installation_date,
                            'start_date': period_start_date,
                            'end_date': period_end_date,
                            'status': line.subscription_status if line.subscription_status else 'active',
                    }
            vehicle_vals.append((0, 0, veh_vals))
        # set lines
        for line in self.subscription_ids.mapped('recurring_invoice_line_ids').filtered(lambda x: x.analytic_account_id.vehicle_number):
            vec_name = line.analytic_account_id.vehicle_number.name
            dev_name = line.analytic_account_id.vehicle_number.device_serial_number_id and line.analytic_account_id.vehicle_number.device_serial_number_id.name
            line_vals = {
                            'product_id': line.product_id.id,
                            'name': "%s -- %s -- %s" %(line.product_id.display_name, vec_name, dev_name),
                            'product_uom_qty':line.quantity,
                            'product_uom': line.uom_id and line.uom_id.id,
                            'price_unit': line.price_unit,
                            'subscription_id': line.analytic_account_id and line.analytic_account_id.id,
                    }
            sub_vals.append((0, 0, line_vals))
        # sale order
        sale_order = sale_order_obj.create({
                'partner_id': self.partner_id and self.partner_id.id,
                'user_id': self.partner_id.user_id and self.partner_id.user_id.id or self.env.user and self.env.user.id,
                'sale_type' : 'pilot',
                'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id,
                'order_line': sub_vals,
                'vehicle_number_ids': vehicle_vals,
            })
        # return
        return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order (%s)' % sale_order.name,
                'res_id': sale_order.id,
                'views': [[False, 'form']],
                'res_model': 'sale.order',
                'view_mode': 'tree,form',
            }


class JobCardWizard(models.TransientModel):
    _name = "job.card.wizard"

    name = fields.Many2one("res.users", string="Engineer")
    supervisor_id = fields.Many2one("res.users", string="Supervisor")
    no_of_devices = fields.Integer(string="No of Devices")
    scheduled_date = fields.Date("Scheduled Date")

    # @api.multi
    def create_job_card(self):
        job_card_obj = self.env['job.card']
        product = False
        order_id = self.env.context.get('active_id')
        if order_id:
            sale_order_id = self.env['sale.order'].search([('id', '=', order_id)],limit=1)
            if not sale_order_id:
                raise UserError(_('Sale order not found'))
            order_line = sale_order_id.order_line
            stockable_products = order_line.filtered(lambda x: x.product_id.type == 'product')
            for line in stockable_products:
                product = line.product_id.id
            if not stockable_products:
                raise UserError(_('There is no stockable product (device) to create job'))
            for count in range(self.no_of_devices):
                job_card_obj.create({
                    'sale_order_id': sale_order_id.id,
                    'job_card_type': 'sale',
                    'device_id': product,
                    'engineer_id': self.name and self.name.id,
                    'supervisor_id': self.supervisor_id and self.supervisor_id.id,
                    'company_id': sale_order_id.partner_id and sale_order_id.partner_id.id,
                    'sale_type': sale_order_id.sale_type,
                    'scheduled_date': self.scheduled_date,
                })
