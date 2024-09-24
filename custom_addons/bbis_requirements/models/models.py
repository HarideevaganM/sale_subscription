# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    sale_type = fields.Selection([('cash', 'Retail Sales'),
                                  ('purchase', 'Corporate Sales'),
                                  ('lease', 'Lease (To Own) Sales'),
                                  ('rental', 'Lease (Rental) Sales'),
                                  ('pilot', 'Renewal Sales'),
                                  ('pilot_sale', 'Pilot Testing'),
                                  ('service', 'Services Sales')
                                  ], string='Sale Type')


class ProductCategory(models.Model):
    _inherit = 'product.category'

    enable_total = fields.Boolean("Enable Total Amount",
                                  help="Enable to calculate total amount for all the period in Quotation.")


class SaleSubscriptionTemplate(models.Model):
    _inherit = 'sale.order.template'

    set_default = fields.Boolean('Set as Default',
                                 help="To enable default the current record will be automatically picked in new forms.")

    #@api.multi
    def write(self, vals):
        record = super(SaleSubscriptionTemplate, self).write(vals)
        if 'set_default' in vals and vals.get('set_default') == True:
            templs = self.env['sale.order.template'].search([('id', '!=', self.id), ('set_default', '=', True)])
            for rec in templs:
                rec.update({'set_default': False})
        return record

    @api.model
    def create(self, vals):
        record = super(SaleSubscriptionTemplate, self).create(vals)
        if record.set_default == True:
            templs = self.env['sale.order.template'].search(
                [('id', '!=', record.id), ('set_default', '=', True)])
            for rec in templs:
                rec.update({'set_default': False})
        return record


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    subscription_template_id = fields.Many2one('sale.order.template', 'Billing Cycle',
                                               default=lambda self: self.env['sale.order.template'].search(
                                                   [('set_default', '=', True)]).id)
    period_amount_total = fields.Monetary(string='Period Total', store=True, readonly=True, compute='_amount_all',
                                          track_visibility='always')
    state = fields.Selection(
        selection_add=[
            ('cancel_req', 'Cancel Request Sent')
        ],
        ondelete={
            'cancel_req': 'set default'
        }
    )

    previous_state = fields.Char("Previous State")
    sale_type = fields.Selection([('cash', 'Retail Sales'),
                                  ('purchase', 'Corporate Sales'),
                                  ('lease', 'Lease (To Own) Sales'),
                                  ('rental', 'Lease (Rental) Sales'),
                                  ('pilot', 'Renewal Sales'),
                                  ('pilot_sale', 'Pilot Testing'),
                                  ('service', 'Services Sales')
                                  ], string='Sale Type', required=True)

    def request_cancel(self):
        for picking in self.picking_ids:
            if picking.state == 'done':
                raise UserError(_("Delivery already Done!"))
        for invoice in self.invoice_ids:
            if invoice.state in ['open', 'paid']:
                raise UserError(_("Invoice already Done!"))
        self.write({
            'state': 'cancel_req',
            'previous_state': self.state
        })

    def approve_cancel_request(self):
        self.action_cancel()

    def reject_cancel_request(self):
        self.write({
            'state': self.previous_state or 'draft'
        })

    #@api.multi
    def action_cancel(self):
        for picking in self.picking_ids:
            if picking.state == 'done':
                raise UserError(_("Delivery already Done!"))
        for invoice in self.invoice_ids:
            if invoice.state in ['open', 'paid']:
                raise UserError(_("Invoice already Done!"))
        return super(SaleOrder, self).action_cancel()

    #@api.multi
    def action_confirm(self):
        if self.partner_id.state != 'confirm':
            raise UserError(_("Customer not yet confirmed!."))
        res = super(SaleOrder, self).action_confirm()
        for vehicle in self.vehicle_number_ids:
            subs = self.order_line.mapped('subscription_id').filtered(
                lambda x: x.vehicle_number.id == vehicle.vehicle_id.id)
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            start_date = fields.Date.from_string(vehicle.start_date)
            bill_template = subs[0].template_id if subs else self.subscription_template_id
            bill_period = relativedelta(
                **{periods[bill_template.recurring_rule_type]: bill_template.recurring_interval})
            bill_end_period = (start_date + bill_period) - relativedelta(days=1)
            if subs:
                subs.update({
                    'date_start': vehicle.start_date,
                    'date': vehicle.end_date,
                    'subscription_period': vehicle.num_of_period,
                    'start_date': vehicle.start_date,
                    'end_date': bill_end_period,
                    'renewal_date': fields.Date.from_string(vehicle.end_date) + relativedelta(days=1),
                    'recurring_next_date': vehicle.start_date,
                    'po_number': self.purchase_order_no,
                    'po_date': self.purchase_order_date,
                    'sale_type': self.sale_type,
                })
        return res

    def _prepare_subscription_data(self, template):
        res = super(SaleOrder, self)._prepare_subscription_data(template)
        res['po_number'] = self.purchase_order_number
        res['po_date'] = self.purchase_order_date
        return res

    @api.depends('order_line.price_total', 'contract_period')
    def _amount_all(self):
        res = super(SaleOrder, self)._amount_all()
        for order in self:
            period_amount_total = 0.0
            for line in order.order_line:
                if line.product_id.categ_id.enable_total:
                    period_amount_total += ((line.price_subtotal + line.price_tax) * int(order.contract_period or 1))
                else:
                    period_amount_total += line.price_tax + line.price_subtotal
            order.update({
                'period_amount_total': period_amount_total,
            })
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.subscription_id and self.subscription_id.date and self.order_id.subscription_management != 'upsell':
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            subscription_period = relativedelta(
                **{periods[self.subscription_id.recurring_rule_type]: self.subscription_id.recurring_interval})
            start_date = fields.Date.from_string(self.subscription_id.start_date)
            end_date = (start_date + subscription_period) - relativedelta(days=1)
            period_msg = _("Invoicing Period: %s - %s") % (start_date, end_date)
            res.update({'name': self.product_id.name + '\n' + period_msg})
        return res

    #@api.multi
    def _get_delivered_qty(self):
        self.ensure_one()
        super(SaleOrderLine, self)._get_delivered_qty()
        qty = 0.0
        for move in self.move_ids.filtered(lambda r: r.state == 'done' and not r.scrapped):
            if move.location_dest_id.usage in ['customer', 'internal'] and move.picking_type_id.code == 'outgoing':
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom)
            # elif move.location_dest_id.usage not in ['customer', 'internal'] and move.to_refund:
            else:
                if move.to_refund:
                    qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom)
        return qty


class SaleSubscription(models.Model):
    _inherit = 'sale.order'

    po_number = fields.Char("PO Number")
    po_date = fields.Date("PO Date")

    def _prepare_renewal_order_values(self):
        res = super(SaleSubscription, self)._prepare_renewal_order_values()
        for subscription in self:
            res[subscription.id]['purchase_order_no'] = subscription.po_number
            res[subscription.id]['purchase_order_date'] = subscription.po_date
        return res


class JobCard(models.Model):
    _inherit = "job.card"

    #@api.multi
    def close_job_card(self):
        res = super(JobCard, self).close_job_card()
        if self.sale_order_id:
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            subscription_period = relativedelta(
                **{periods[
                       self.sale_order_id.subscription_template_id.recurring_rule_type]: self.sale_order_id.subscription_template_id.recurring_interval})
            start_date = fields.Date.from_string(self.activation_date)
            end_date = (start_date + subscription_period) - relativedelta(days=1)
            num_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

            # # BBIS - Checking whether the job card device type available in the sales order.
            # picking_id = self.env['stock.picking'].search([('sale_id', '=', self.sale_order_id.id)])
            # move_line_ids = self.env['stock.move.line'].search([('picking_id', '=', picking_id.id),
            #                                                     ('product_id', '=', self.device_id.id)])
            # if not move_line_ids:
            #     raise UserError(_("Device Type in Job Card does not have any available delivery. Please ensure it "
            #                       "is included in the order lines of the Sales Order"))

            if num_months == 11:
                num_months += 1
            vehicle_vals = {
                'serial_no_id': self.device_serial_number_new_id.id,
                'device_id': self.device_id.id,
                'vehicle_id': self.vehicle_number.id,
                'vehicle_name': self.vehicle_number.vehicle_name,
                'partner_id': self.company_id.id,
                'installation_date': self.installation_date,
                'start_date': self.activation_date,
                'num_of_period': num_months,
                'end_date': end_date,
                'status': self.device_status,
                'sale_id': self.sale_order_id.id

            }
            self.sale_order_id.vehicle_number_ids.create(vehicle_vals)
        return res

    @api.onchange('vehicle_number', 'device_id')
    def onchange_device_number(self):
        if self.vehicle_number:
            self.device_serial_number_new_id = self.vehicle_number.device_serial_number_id.id if self.vehicle_number.device_serial_number_id else ''
            # self.installation_date = self.vehicle_number.installation_date
            # self.activation_date = self.vehicle_number.activation_date
            # self.installation_location_id = self.vehicle_number.installation_location_id and self.vehicle_number.installation_location_id.id
        if self.device_id:
            lots = self.env['stock.lot'].search([('product_id', '=', self.device_id.id)])
            quants = self.env['stock.quant'].search(
                [('lot_id', 'in', lots.ids), ('quantity', '>', 0), ('location_id.restrict_location', '!=', True)])
            return {'domain': {'device_serial_number_new_id': [('id', 'in', quants.mapped('lot_id').ids)]}}


class StockLocation(models.Model):
    _inherit = 'stock.location'

    restrict_location = fields.Boolean("Restrict Location", help="Restrict the stock being selected from job card")
