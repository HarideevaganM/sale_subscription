from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from itertools import groupby
from operator import itemgetter
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class GenerateSubscriptionWizard(models.TransientModel):
	_inherit = "generate.subscription.wizard"

	is_reseller = fields.Boolean(string="Use Reseller")
	reseller_id = fields.Many2one("res.partner", string="Reseller")

	@api.model
	def default_get(self, fields):
		res = super(GenerateSubscriptionWizard, self).default_get(fields)
		active_ids = self.env.context.get('active_ids', False)
		if active_ids:
			subscription_ids = self.env['sale.subscription'].browse(active_ids)
			partner = subscription_ids.mapped('partner_id')
			reseller_id = partner.mapped('reseller_id')
			if len(partner.ids) == 1:
				res.update({'partner_id': partner and partner.id})
			else:
				if len(reseller_id.ids) == 1:
					res.update({'reseller_id': reseller_id and reseller_id.id, 'is_reseller': True })
			res.update({'subscription_ids': subscription_ids.ids})
		return res

	@api.multi
	def create_quotation(self):
		sub_vals = []
		vehicle_vals = []
		sale_order_obj = self.env['sale.order']
		# set vehicle
		partner_id = self.subscription_ids.mapped('partner_id')
		if self.is_reseller:
			partner_id = partner_id.mapped('reseller_id')
			if len(partner_id.ids) > 1:
				raise UserError(_('Reseller must be same for generate of quote'))
			if self.reseller_id != partner_id:
				raise UserError(_('Reseller must be one of subscription'))
		else:
			if len(partner_id.ids) > 1:
				raise UserError(_('Partner must be same for generate of quote'))
			if self.partner_id != partner_id:
				raise UserError(_('Partner must be same in subscription'))
		if not self.partner_id and not self.reseller_id:
			raise UserError(_('Partner or reseller not define'))
		#subscribtion
		for line in self.subscription_ids.filtered(lambda x: x.vehicle_number):
			sub_start_date = fields.Date.from_string(line.end_date)
			if not sub_start_date:
				raise UserError(_('Please define period end date "%s".') % (line.display_name,))
			periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
			subscription_period = relativedelta(**{periods['monthly']: line.subscription_period})
			start_date = fields.Date.from_string(line.date)
			start_period = start_date + relativedelta(days=1)
			sub_end_period = start_period + subscription_period
			end_period = sub_end_period - relativedelta(days=1)
			veh_vals = {
							'serial_no_id': line.vehicle_number.device_serial_number_id and line.vehicle_number.device_serial_number_id.id,
							'device_id': line.vehicle_number.device_id and line.vehicle_number.device_id.id,
							'vehicle_id': line.vehicle_number.id,
							'partner_id': line.partner_id and line.partner_id.id,
							'installation_date': line.vehicle_number.installation_date,
							'start_date': start_period,
							'num_of_period': line.subscription_period,
							'end_date': end_period,
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
				'partner_id': partner_id and partner_id.id,
				'user_id': partner_id.user_id and partner_id.user_id.id or self.env.user and self.env.user.id,
				'sale_type' : 'pilot',
				'pricelist_id': partner_id.property_product_pricelist and partner_id.property_product_pricelist.id,
				'payment_term_id': partner_id.property_payment_term_id and partner_id.property_payment_term_id.id,
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

class ResPartner(models.Model):
	_inherit = 'res.partner'

	state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], default='draft')
	supplier = fields.Boolean(string='Is a Vendor')
	customer = fields.Boolean(string='Is a Customer', help="Check this box if this contact is a customer.")

	def action_confirm(self):
		self.write({'state': 'confirm'})

	def action_set_draft(self):
		self.write({'state': 'draft'})


class AccountMove(models.Model):
	_inherit = 'account.move'

	@api.model
	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		res = super(AccountMove, self).fields_view_get(
			view_id=view_id, view_type=view_type, toolbar=toolbar,
			submenu=submenu,
		)
		if view_type == 'form':
			doc = etree.XML(res['arch'])
			if self.move_type == 'out_invoice':
				for node in doc.xpath("//field[@name='partner_id']"):
					node.set("domain", "[('customer', '=', True), ('state','=', 'confirm')]")
					modifiers = json.loads(node.get("modifiers"))
					modifiers['domain'] = [('customer', '=', True), ('state','=', 'confirm')]
					node.set("modifiers", json.dumps(modifiers))
				res['arch'] = etree.tostring(doc)
			elif self.move_type == 'in_invoice':
				for node in doc.xpath("//field[@name='partner_id']"):
					node.set("domain", "[('supplier', '=',True), ('state','=', 'confirm')]")
					modifiers = json.loads(node.get("modifiers"))
					modifiers['domain'] = [('supplier', '=',True), ('state','=', 'confirm')]
					node.set("modifiers", json.dumps(modifiers))
				res['arch'] = etree.tostring(doc)
		return res

	@api.onchange('sale_type')
	def onchange_sale_type(self):
		immediate_paymnet_id = self.env.ref('account.account_payment_term_immediate')
		if self.sale_type == 'cash':
			self.payment_term_id = immediate_paymnet_id
		if self.sale_type == 'pilot' and self.partner_id.property_payment_term_id:
			self.payment_term_id = self.partner_id.property_payment_term_id.id
		not_pilot = self.sale_type and self.sale_type == 'pilot_sale' and not self.is_pilot
		if not_pilot:
			raise UserError(_('You can not change or select pilot sale type from this menu. Please remove it'))

	@api.multi
	def action_confirm(self):
		lines = []
		order_lines = self.order_line.filtered(lambda x: x.product_id and x.product_id.tracking == 'serial')
		for sale in self.filtered(lambda x: x.sale_type in ('purchase', 'lease', 'rental')):
			po_data = sale.purchase_order_no and sale.purchase_order_date
			if not po_data:
				raise UserError(_('Please assign purchase date and number in this order'))
		for line in order_lines:
			for count in range(int(line.product_uom_qty)):
				self.env['job.card'].create({
					'sale_order_id': line.order_id.id,
					'job_card_type': 'sale',
					'scheduled_date': line.scheduled_date,
					'device_id': line.product_id.id,
					'company_id': line.order_id.partner_id and line.order_id.partner_id.id,
					'sale_type': line.order_id.sale_type,
					'reseller_id': line.order_id.reseller_id and line.order_id.reseller_id.id,
					'installation_category': line.order_id.partner_id and line.order_id.partner_id.subscription_customer,
				})
		return super(SaleOrder, self).action_confirm()

	@api.multi
	def _prepare_invoice(self):
		invoice_vals = super(SaleOrder, self)._prepare_invoice()
		picking_ids = self.mapped('picking_ids').filtered(lambda x: not x.is_invoiced and x.job_card_id and x.state == 'done')
		job_ids = picking_ids.mapped("job_card_id")
		job_name = ",".join([job.name for job in job_ids])
		invoice_vals.update({'job_invoice_ref': job_name})
		picking_ids.write({'is_invoiced' : True})
		return invoice_vals

class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	scheduled_date = fields.Date("Job Scheduled Date")

class InstallationCertificate(models.Model):
	_inherit = "installation.certificate"

	subscription_id = fields.Many2one('sale.subscription', "Subscription")

class SaleSubscription(models.Model):
	_inherit = "sale.subscription"

	is_fls = fields.Boolean('Auto FLS')
	project_name = fields.Char('Project Name')
	certy_count = fields.Integer(string='Certificates', compute='_compute_certy_count')
	customer_types = fields.Selection([('adnoc','ADNOC'),('non_adnoc','NON ADNOC')], string='Customer Type', default='non_adnoc')

	@api.multi
	def installation_certificate(self):
		certificate_obj = self.env["installation.certificate"]
		if not self.start_date or not self.end_date or not self.serial_no or not self.vehicle_number:
			raise UserError(_('Please select subscription billing dates and serial no and vehicle number'))
		certificate_id = self.env['certificate.subject'].create({'name': 'IVMS Installation Certificate-Renewal- %s' % self.code})
		vals = {
			'from_date': self.date_start,
			'to_date': self.date,
			'serial_no': self.serial_no and self.serial_no.id,
			'vehicle_number': self.vehicle_number.id,
			'fleet_description': self.vehicle_number.vehicle_name,
			'device_id': self.vehicle_number.device_id and self.vehicle_number.device_id.id,
			'vin_no': self.vehicle_number.chassis_no,
			'company_id': self.env.user.company_id and self.env.user.company_id.id,
			'partner_id': self.partner_id.id,
			'installation_date': self.installation_date,
			'subscription_id': self.id,
			'certificate_subject': certificate_id and certificate_id.id or False,
		}
		certificate = certificate_obj.create(vals)
		if certificate:
			certificate.name = certificate.name.replace('IC', 'RW')
		return {
					'type': 'ir.actions.act_window',
					'name': 'Certificate (%s)' % certificate.name,
					'res_id': certificate.id,
					'views': [[False, 'form']],
					'res_model': 'installation.certificate',
					'view_mode': 'tree,form',
				}
	@api.multi
	def _compute_certy_count(self):
		for sub in self:
			subscription_id = self.env['installation.certificate'].search([('subscription_id', '=', sub.id)])
			sub.certy_count = len(subscription_id.ids)

	@api.multi
	def action_sub_certification(self):
		subscription_id = self.env['installation.certificate'].search([('subscription_id', '=', self.id)])
		return {
			'name': _('Certificates'),
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'installation.certificate',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', subscription_id.ids)],
		}

	@api.multi
	def update_dates(self):
		return False

class JobCard(models.Model):
	_inherit = "job.card"

	move_line_id = fields.Many2one('stock.move.line', "Move Line")

	@api.multi
	def close_job_card(self):
		res = super(JobCard, self).close_job_card()
		if self.sale_order_id:
			move_line_id = self.env['stock.move.line']
			order_lines = self.sale_order_id.order_line.filtered(lambda x: x.product_id == self.device_id and x.order_id.partner_id == self.company_id)
			ordered_qty = sum(order_lines.mapped('product_uom_qty'))
			delivered_qty = sum(order_lines.mapped('qty_delivered'))
			if ordered_qty >= delivered_qty:
				picking_id = self.sale_order_id.picking_ids.filtered(lambda x: x.state not in ['cancel', 'done'])
				if picking_id:
					if len(picking_id) > 1:
						raise UserError(_('Multiple picking found. Please process previous pickings'))
					move_lines = picking_id.mapped('move_lines').filtered(lambda x: x.product_id == self.device_id and x.picking_id.partner_id == self.company_id)
					for move in move_lines:
						move_line_id = self.env['stock.move.line'].create({
								'move_id': move.id,
								'product_id': move.product_id.id,
								'product_uom_id': move.product_uom.id,
								'location_id': move.location_id.id,
								'location_dest_id': move.location_dest_id.id,
								'picking_id': picking_id.id,
								'lot_id': self.device_serial_number_new_id and self.device_serial_number_new_id.id,
								'qty_done': 1,
							})
						# if not picking_id.date_done:
						# 	picking_id.date_done = fields.Datetime.now()
						move_lines._action_done()
						if move_line_id:
							picking_id.job_card_id = self.id
							self.move_line_id = move_line_id and move_line_id.id
		return res

class StockPicking(models.Model):
	_inherit = "stock.picking"

	is_invoiced = fields.Boolean(string="Invoiced")
	supervisor_id = fields.Many2one('res.users', string='Supervisor')
	job_scheduled_date = fields.Date(string='Job Scheduled Date')

	@api.onchange('group_id', 'technician')
	def onchange_po_detail(self):
		if self.technician and self.group_id and self.group_id.sale_id:
			self.po_number = self.group_id.sale_id.purchase_order_no
			self.po_date = self.group_id.sale_id.purchase_order_date

class StockMove(models.Model):
	_inherit = "stock.move"

	def _action_assign(self):
		""" Reserve stock moves by creating their stock move lines. A stock move is
		considered reserved once the sum of `product_qty` for all its move lines is
		equal to its `product_qty`. If it is less, the stock move is considered
		partially available.
		"""
		assigned_moves = self.env['stock.move']
		partially_available_moves = self.env['stock.move']
		# Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
		# cache invalidation when actually reserving the move.
		reserved_availability = {move: move.reserved_availability for move in self}
		for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
			missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
			missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
			if move.location_id.should_bypass_reservation()\
					or move.product_id.type == 'consu':
				# create the move line(s) but do not impact quants
				if move.product_id.tracking == 'serial' and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
					for i in range(0, int(missing_reserved_quantity)):
						self.env['stock.move.line'].create(move._prepare_move_line_vals(quantity=1))
				else:
					to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
															ml.location_id == move.location_id and
															ml.location_dest_id == move.location_dest_id and
															ml.picking_id == move.picking_id and
															not ml.lot_id and
															not ml.package_id and
															not ml.owner_id)
					if to_update:
						to_update[0].product_uom_qty += missing_reserved_uom_quantity
					else:
						self.env['stock.move.line'].create(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
				assigned_moves |= move
			else:
				if not move.move_orig_ids:
					if move.procure_method == 'make_to_order':
						continue
					# If we don't need any quantity, consider the move assigned.
					need = missing_reserved_quantity
					if float_is_zero(need, precision_rounding=move.product_id.uom_id.rounding):
						assigned_moves |= move
						continue
					# Reserve new quants and create move lines accordingly.
					available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id)
					if available_quantity <= 0 or (move.sale_line_id and move.sale_line_id.product_id.tracking == 'serial'):
						continue
					taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, strict=False)
					if float_is_zero(taken_quantity, precision_rounding=move.product_id.uom_id.rounding):
						continue
					if need == taken_quantity:
						assigned_moves |= move
					else:
						partially_available_moves |= move
				else:
					# Check what our parents brought and what our siblings took in order to
					# determine what we can distribute.
					# `qty_done` is in `ml.product_uom_id` and, as we will later increase
					# the reserved quantity on the quants, convert it here in
					# `product_id.uom_id` (the UOM of the quants is the UOM of the product).
					move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
					keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

					def _keys_in_sorted(ml):
						return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

					grouped_move_lines_in = {}
					for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
						qty_done = 0
						for ml in g:
							qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
						grouped_move_lines_in[k] = qty_done
					move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move)\
						.filtered(lambda m: m.state in ['done'])\
						.mapped('move_line_ids')
					# As we defer the write on the stock.move's state at the end of the loop, there
					# could be moves to consider in what our siblings already took.
					moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
					moves_out_siblings_to_consider = moves_out_siblings & (assigned_moves + partially_available_moves)
					reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
					move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')
					keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

					def _keys_out_sorted(ml):
						return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)

					grouped_move_lines_out = {}
					for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
						qty_done = 0
						for ml in g:
							qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
						grouped_move_lines_out[k] = qty_done
					for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
						grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
					available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in.keys()}
					# pop key if the quantity available amount to 0
					available_move_lines = dict((k, v) for k, v in available_move_lines.items() if v)

					if not available_move_lines:
						continue
					for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
						if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
							available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)] -= move_line.product_qty
					for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
						need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
						# `quantity` is what is brought by chained done move lines. We double check
						# here this quantity is available on the quants themselves. If not, this
						# could be the result of an inventory adjustment that removed totally of
						# partially `quantity`. When this happens, we chose to reserve the maximum
						# still available. This situation could not happen on MTS move, because in
						# this case `quantity` is directly the quantity on the quants themselves.
						available_quantity = self.env['stock.quant']._get_available_quantity(
							move.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
						if float_is_zero(available_quantity, precision_rounding=move.product_id.uom_id.rounding):
							continue
						taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity), location_id, lot_id, package_id, owner_id)
						if float_is_zero(taken_quantity, precision_rounding=move.product_id.uom_id.rounding):
							continue
						if need - taken_quantity == 0.0:
							assigned_moves |= move
							break
						partially_available_moves |= move
		partially_available_moves.write({'state': 'partially_available'})
		assigned_moves.write({'state': 'assigned'})
		self.mapped('picking_id')._check_entire_pack()


class AccountJournal(models.Model):
	_inherit = "account.journal"

	label_type = fields.Selection([('cash_tax_inv', 'Cash Tax Invoice'), ('cash_tax_inv_inclu', 'Cash Tax Invoice-Inclusive'), ('tax_inv', 'Tax Invoice'), ('tax_inv_incl', 'Tax Invoice-Inclusive')],
								   'Invoice Type')

class AccountAccount(models.Model):
	_inherit = "account.account"

	active = fields.Boolean(default=True, help="Set active to false to hide the account without removing it.")

class AccountInvoice(models.Model):
	_inherit = "account.invoice"

	date_invoice = fields.Date(string='Invoice Date',
		readonly=True, states={'draft': [('readonly', False)]}, index=True,
		help="Keep empty to use the current date", copy=False, default=fields.Datetime.now)
	sale_type = fields.Selection(selection_add=[('pilot_sale', 'Pilot')])
	job_invoice_ref = fields.Char(string="Job Invoice Ref")

class AccountInvoiceLine(models.Model):
	_inherit = "account.invoice.line"

	def compute_tax_price(self):
		# calculate price tax
		price_tax = 0.0
		currency = self.invoice_id and self.invoice_id.currency_id or None
		price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
		taxes = False
		if self.invoice_line_tax_ids:
			taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
			price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
		return price_tax

class account_register_payments(models.TransientModel):
	_inherit = 'account.register.payments'

	payment_type_method = fields.Selection([('cash', 'Cash'), ('fund_transfer', 'Fund Transfer'), ('cheque', 'Cheque')], default='cash')
	fund_transfer_detail = fields.Char()
	fund_transfer_date = fields.Date()
	cheque_number = fields.Char()
	cheque_date = fields.Date()
	issuing_bank = fields.Char()

class AccountPayment(models.Model):
	_inherit = "account.payment"

	partner_id = fields.Many2one(
		'res.partner', 'Customer',
		index=True, states={'confirmed': [('readonly', True)]}, check_company=True, change_default=True,
		help='Choose partner for whom the order will be invoiced and delivered. You can find a partner by its Name, TIN, Email or Internal Reference.',
		domain=[('customer', '=', True), ('state','=', 'confirm')])


class CrmLead(models.Model):
	_inherit = 'crm.lead'

	partner_id = fields.Many2one(
		'res.partner', string='Customer', check_company=True, index=True, tracking=10,
		domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('customer', '=', True), ('state', '=', 'confirm')]",
		help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")

	customer_state = fields.Selection(string="Customer State", related='partner_id.state')
