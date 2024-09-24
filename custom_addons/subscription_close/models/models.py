from odoo import models, fields, api, _
from datetime import timedelta, date
from odoo.exceptions import Warning,UserError,ValidationError



class SaleSubscription(models.Model):
    _inherit = 'sale.order'

    def _compute_counts(self):
        for rec in self:
            rec.closure_count = len(self.env['subscription.close'].search([('subscription_id', '=', rec.id)]))
            rec.work_order_count = len(
                self.env['fms.customer.support'].search(
                    [('subscription_id', '=', rec.id), ('request_type', '=', 'activate')]))

    # state = fields.Selection([('draft', 'New'), ('open', 'In Progress'), ('pending', 'Quotation'),
    #                           ('close', 'Closed'), ('hold', 'Hold'), ('cancel', 'Cancelled')],
    #                          string='Status', required=True, track_visibility='onchange', copy=False, default='draft')
    closure_count = fields.Integer(string="Closure for Count", compute='_compute_counts')
    work_order_count = fields.Integer(string="WorkOrder Count", compute='_compute_counts')

    def action_open_closure(self):
        rec = self.env['subscription.close'].search([('subscription_id', '=', self.id)])
        return {
            'name': _('Closure of Subscription'),
            # 'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'subscription.close',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', rec.ids)],
            'context': {'create': False}
        }

    def create_work_order(self):
        orders = self.env['fms.customer.support'].search(
            [('subscription_id', '=', self.id), ('request_type', '=', 'activate')])
        for order in orders:
            if order.state not in ['done', 'cancel']:
                raise UserError(_("Please close all the work order to create a new one."))
        order = self.env['fms.customer.support']
        order.create({
            'subject': "Reactivation of %s" % (self.display_name),
            'user_id': self.env.user.id,
            'service_type': 'reactive_device',
            'service_sub_type': 'sub_reactive_device',
            'partner_id': self.partner_id.id,
            'no_of_vehicles': 1,
            'request_type': 'activate',
            'billing_method': 'no_chargeable',
            'subscription_id': self.id,
        })

    def action_open_work_order(self):
        rec = self.env['fms.customer.support'].search(
            [('subscription_id', '=', self.id), ('request_type', '=', 'activate')])
        return {
            'name': _('Work Orders'),
            # 'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'fms.customer.support',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', rec.ids)],
            'context': {'create': False}
        }


class SubscriptionClose(models.Model):
    _name = "subscription.close"

    def _get_status_all(self):
        for rec in self:
            orders = self.env['fms.customer.support'].search([('subscription_close_id', '=', rec.id)])
            rec.device_status = 'active'
            if orders:
                rec.order_status = orders[0].state
                repair = self.env['repair.order'].search([('customer_support_id', '=', orders[0].id)])
                if repair:
                    rec.device_status = 'in_active' if repair[0].state == 'done' else 'active'
                    rec.engineer_id = repair[0].user_id.id
            else:
                rec.order_status = False
                rec.device_status = False
                rec.engineer_id = False


    def _compute_work_order(self):
        for rec in self:
            rec.work_order_count = len(
                self.env['fms.customer.support'].search([('subscription_close_id', '=', rec.id)]))

    subscription_id = fields.Many2one('sale.order', string="Subscription", copy=False, required=1,  domain=[('is_subscription', '=', True)])
    partner_id = fields.Many2one('res.partner', string="Customer", related='subscription_id.partner_id', store=True)
    name = fields.Char(string='Name', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]},
                       index=True, default=lambda self: _('New'))
    state = fields.Selection([('draft', 'Draft'), ('hold', 'Hold'), ('termination', 'Termination'), ('close', 'Closed'),('release', 'Released')
                              ], string="Closure Status", default='draft')
    date_from = fields.Date('From Date', default=fields.Date.today(), required=1)
    days = fields.Integer('No of days hold', default=7)
    date_to = fields.Date('To Date', store=1)
    user_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user)
    hold_by_id = fields.Many2one('res.users', string="Hold by", store=1)
    hold_date = fields.Date('Hold Date', store=1)
    approved_by_id = fields.Many2one('res.users', string="Approved by")
    approved_date = fields.Date('Approved Date', store=1)
    device_id = fields.Many2one('product.product', string='Device')
    device_status = fields.Selection([('active', 'Active'), ('in_active', 'InActive')], string="Device Status",
                                     compute='_get_status_all',
                                     help="The status will automatically updated once the ticket is closed.")
    vehicle_id = fields.Many2one('vehicle.master', string="Vehicle")
    engineer_id = fields.Many2one('res.users', string="Engineer", compute='_get_status_all', store=True)
    sim_no = fields.Char('SIM Number')
    sim_status = fields.Selection([('active', 'Active'), ('in_progress', 'In Progress'), ('in_active', 'InActive')],
                                  string="SIM Status", default='active')
    portal_status = fields.Selection([('active', 'Active'), ('in_active', 'InActive')], string="Portal Status",
                                     default='active')
    reason_id = fields.Many2one('sale.subscription.close.reason', string="Close/Hold Reason")
    lot_id = fields.Many2one('stock.lot', string="Device Serial No", )
    # ticket_id = fields.Many2one('website.support.ticket', string="Ticket")
    sale_type = fields.Selection([('cash', 'Retail Sales'),
                                  ('purchase', 'Corporate Sales'),
                                  ('lease', 'Lease (To Own) Sale'),
                                  ('rental', 'Lease (Rental) Sale'),
                                  ('pilot', 'Renewal Sale'),
                                  ('pilot_sale', 'Pilot Testing'),
                                  ], string="Sale Type", required=1)
    # last_state = fields.Many2one('sale.subscription.stage', string='Status')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    release_reason_id = fields.Many2one('sale.subscription.close.reason', string="Release/Reactivate Reason")
    released_by_id = fields.Many2one('res.users', string="Released by", store=1)
    released_date = fields.Date('Released Date', store=1)
    work_order_count = fields.Integer(string="WorkOrder Count", compute='_compute_work_order')
    order_status = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Open'), ('quote', 'Quotation'), ('ticket', 'In progress'), ('done', 'Closed'),
         ('cancel', 'Cancel')], string="WorkOrder Status", compute='_get_status_all')
    sim_approved_by_id = fields.Many2one('res.users', string="Approved by")
    sim_approved_date = fields.Date('Approved Date')
    mobile_no = fields.Char('Mobile Number')
    portal_approved_by_id = fields.Many2one('res.users', string="Approved by")
    portal_approved_date = fields.Date('Approved Date')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'subscription.close') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.close') or _('New')
        result = super(SubscriptionClose, self).create(vals)
        return result

    # @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_("Please restart the subscription before delete the Closure."))
        return super(SubscriptionClose, self).unlink()

    @api.model
    def default_get(self, fields):
        res = super(SubscriptionClose, self).default_get(fields)
        subscription = self.env['sale.order'].search([
            ('id', '=', self._context.get('default_subscription_id')),
            ('is_subscription', '=', True)
        ], limit=1)
        if subscription:
            res.update({
                'lot_id': subscription.serial_no.id,
                'device_id': subscription.serial_no.product_id.id,
                'vehicle_id': subscription.vehicle_number.id,
                'engineer_id': subscription.engineer_id.id,
                'reason_id': subscription.close_reason_id.id,
                'sale_type': subscription.sale_type,
                'device_status': subscription.subscription_status,
                'sim_no': subscription.gsm_number,
                'last_state': subscription.stage_id.id,
            })
        return res

    @api.onchange('date_from', 'days')
    def onchange_from_date(self):
        if self.date_from and self.days:
            self.date_to = fields.Date.from_string(self.date_from) + timedelta(days=self.days)

    def close(self):
        if self.device_status != 'in_active' or self.sim_status != 'in_active' or self.portal_status != 'in_active':
            raise UserError(_("Please deactivate the device,SIM and portal status."))
        order = self.env['fms.customer.support'].search([('subscription_close_id', '=', self.id)])
        if not order:
            raise UserError(_("Please create work order do close the subscription."))
        if order[0].state != 'done':
            raise UserError(_("Please close the work order to complete the closure of subscription."))
        # close_stage = self.env['sale.subscription.stage'].search([('category', '=', 'closed')], limit=1)
        # self.subscription_id.update({
        #     'stage_id': close_stage.id,
        #     'subscription_status': 'in_active',
        # })
        self.write({'state': 'close'})

    def submit(self):
        # hold_stage = self.env['sale.subscription.stage'].search([('category', '=', 'hold')], limit=1)
        # self.subscription_id.write({'stage_id': hold_stage.id})
        self.write({
            'state': 'hold',
            'hold_by_id': self.env.user.id,
            'hold_date': fields.Date.today()
        })

    def terminate(self):
        if not self.device_id or not self.vehicle_id or not self.sim_no:
            raise UserError(_("Please provide the Device, Vehicle, and Sim No."))
        # if not self.approved_by_id or not self.approved_date:
        #     raise UserError(_("Please provide approval details in Hold tab...!"))
        self.write({'state': 'termination'})

    def restart(self):
        if not self.release_reason_id:
            raise UserError(_("Please enter release reason."))
        orders = self.env['fms.customer.support'].search([('subscription_close_id', '=', self.id)])
        if orders:
            if orders[0].state not in ['draft', 'cancel']:
                raise UserError(_("Please cancel or delete the work order to release the closure of subscription."))
            else:
                orders[0].unlink()
        self.subscription_id.write({'stage_id': self.last_state.id})
        self.write({
            'state': 'release',
            'released_by_id': self.env.user.id,
            'released_date': fields.Date.today()
        })

    def action_open_work_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Order',
            'view_mode': 'tree,form',
            'res_model': 'fms.customer.support',
            'domain': [('subscription_close_id', '=', self.id)],
            'context': {'create': False}
        }
        # rec = self.env['fms.customer.support'].search([('subscription_close_id', '=', self.id)])
        # action = {'type': 'ir.actions.act_window',
        #           'name': _("Work Order"),
        #           'res_model': 'fms.customer.support',
        #           'views': [[False, 'form']],
        #           'target': 'current',
        #           'context': {'create': False}
        #           }
        # if len(rec) == 1:
        #     action.update({'res_id': rec.id})
        # else:
        #     action.update({'domain': [('ids', 'in', rec.ids)]})
        # return action

    def create_work_order(self):
        """Create work order but make sure only in termination state are allowed and that
        no work orders are not closed or cancelled."""

        if self.state != 'termination':
            raise UserError(_("Sorry! You are not allowed to create work orders if any of the selected records are not in Termination status."))

        if self.work_order_count > 0:
            existing_work_orders = self.env['fms.customer.support'].search([('subscription_close_id', '=', self.id),
                                                                            ('state', '!=', 'cancel')])
            if existing_work_orders:
                raise UserError(_("Sorry! You have existing work orders of %s. Cancel it before proceeding.") % self.name)

        order = self.env['fms.customer.support']
        service_type = 'deactive_device' if self.sale_type != 'pilot_sale' else False
        service_sub_type = 'sub_deactive_device' if self.sale_type != 'pilot_sale' else 'remove_return'

        work_order = order.create({
            'subject': _("Work order for %s") % (self.name),
            'request_type': 'deactivate',
            'user_id': self.env.user.id,
            'service_type': service_type,
            'service_sub_type': service_sub_type,
            'partner_id': self.partner_id.id,
            'no_of_vehicles': 1,
            'billing_method': 'no_chargeable',
            'subscription_close_id': self.id,
            'subscription_id': self.subscription_id.id,
        })

        if work_order:
            work_order.onchange_partner_id()
            work_order.create_ticket()

    # @api.multi
    def action_view_work_order_multi(self, records):
        """Redirect to newly created work orders"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Order',
            'view_mode': 'tree,form',
            'res_model': 'fms.customer.support',
            'domain': [('subscription_close_id', 'in', records.ids)],
            'context': {'create': False}
        }


class FmsCustomerSupport(models.Model):
    _inherit = 'fms.customer.support'

    subscription_close_id = fields.Many2one('subscription.close', string="Closure of Subscription")
    subscription_id = fields.Many2one('sale.order', string="Subscription", domain=[('is_subscription', '=', True)])
    request_type = fields.Selection([('activate', 'Activation'), ('deactivate', 'Deactivation')], string="Request for",
                                    default='deactivate')

    def create_ticket(self):
        res = super(FmsCustomerSupport, self).create_ticket()
        for rec in self:
            ticket = self.env['website.support.ticket'].search([('customer_support_id', '=', rec.id)])
            if rec.subscription_id and ticket:
                ticket[0].write({
                    'vehicle_id': rec.subscription_id.vehicle_number.id,
                    'vehicle_name': rec.subscription_id.vehicle_number.vehicle_name,
                    'installated_city': rec.subscription_id.vehicle_number.installation_location_id.id,
                    'installation_date': rec.subscription_id.vehicle_number.installation_date,
                    'activation_date': rec.subscription_id.vehicle_number.activation_date,
                    'chassis_no': rec.subscription_id.vehicle_number.chassis_no,
                    'gsm_no': rec.subscription_id.vehicle_number.gsm_no,
                })
        return res


class SaleSubscriptionCloseReasonWizard(models.TransientModel):
    _inherit = "sale.subscription.close.reason.wizard"

    sim_status = fields.Selection([('active', 'Active'), ('in_progress', 'In Progress'), ('in_active', 'InActive')], default='in_active')
    portal_status = fields.Selection([('active', 'Active'), ('in_active', 'InActive')], default='in_active')
    date_from = fields.Date(default=fields.Date.today)
    days = fields.Integer(default=7)

    # @api.multi
    def set_close_cancel(self):
        active_ids = self.env.context.get('active_ids')  # allow multiple closure of subscription
        for rec in self.env['subscription.close'].search([('subscription_id', 'in', active_ids)]):
            if rec.state == 'draft':
                raise UserError(_("Please de_compute_closurelete or use %s closure inorder to close the subscription." % (
                    rec.name)))

        subscriptions = self.env['sale.order'].search([
            ('id', 'in', self._context.get('active_ids', [])),
            ('is_subscription', '=', True)
        ])
        sub_close_obj = self.env['subscription.close']
        sub_close_new_ids = []

        # do not allow creation if any subscription not in open state
        if subscriptions and any(s.stage_id.category != 'progress' for s in subscriptions):
            raise UserError("Sorry! You can't close subscription if any of the selected records are not in In-Progress"
                          " status.")

        for subscription in subscriptions:
            subscription.close_reason_id = self.close_reason_id

            # Prepare the data needed
            sub_close_data = {
                'subscription_id': subscription.id,
                'lot_id': subscription.serial_no.id,
                'device_id': subscription.serial_no.product_id.id,
                'vehicle_id': subscription.vehicle_number.id,
                'engineer_id': subscription.engineer_id.id,
                'reason_id': subscription.close_reason_id.id,
                'sale_type': subscription.sale_type,
                'sim_no': subscription.gsm_number,
                'last_state': subscription.stage_id.id,
                'sim_status': self.sim_status,
                'portal_status': self.portal_status,
                'date_from': self.date_from,
                'days': self.days,
                'date_to': fields.Date.from_string(self.date_from) + timedelta(days=self.days),
            }

            # create and update the statuses
            sub_close = sub_close_obj.create(sub_close_data)
            sub_close_new_ids.append(sub_close.id)

        # redirect to newly created records
        return {
            'name': 'Closure of Subscription',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'subscription.close',
            'domain': [('id', 'in', sub_close_new_ids)]
        }

        # if self.env.context.get('cancel'):
        #     subscription.set_cancel()
        # else:
        #     return {
        #         'name': ('Closure of Subscription'),
        #         'view_type': 'form',
        #         'view_mode': 'form',
        #         'res_model': 'subscription.close',
        #         'view_id': False,
        #         'type': 'ir.actions.act_window',
        #         'context': {'default_subscription_id': subscription.id, 'create': False}
        #     }
