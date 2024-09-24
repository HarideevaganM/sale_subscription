# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import UserError
from datetime import datetime


class WebsiteSupportTicketClose(models.TransientModel):
	_inherit = 'website.support.ticket.close'

	def close_ticket(self):
		res = super(WebsiteSupportTicketClose,self).close_ticket()
		if self.ticket_id:
			self.ticket_id.close_time = fields.Datetime.now()
		else:
			active_id  = self.env.context.get('active_id')
			if active_id:
				ticket_id = self.env['website.support.ticket'].browse(active_id)
				if ticket_id:
					ticket_id.close_time =  fields.Datetime.now()
		return res


class JobCard(models.Model):
	_inherit = "job.card"

	sale_type = fields.Selection([('cash', 'Retail Sales'),
								  ('purchase', 'Corporate Sales'),
								  ('lease', 'Lease (To Own) Sales'),
								  ('rental', 'Lease (Rental) Sales'),
								  ('pilot', 'Renewal Sales'),
								  ('pilot_sale', 'Pilot Testing'),
								  ('service', 'Services Sales'),
								  ('support', 'Support Service'),
								  ], string='Sale Type')


class AccountMove(models.Model):
	_inherit = "account.move"

	sale_type = fields.Selection(selection_add=[('support', 'Support Service')], ondelete={'support': 'cascade'})
	repair_ids = fields.Many2many('repair.order')


class ProjectInherit(models.Model):
	_inherit = "project.project"

	sale_type = fields.Selection(selection_add=[('support', 'Support Service')], ondelete={'support': 'cascade'})


class SaleOrder(models.Model):
	_inherit = 'sale.order'

	# @api.multi
	def _prepare_invoice(self):
		repair_ids = self.env['repair.order']
		invoice_vals = super(SaleOrder, self)._prepare_invoice()
		if self.support_id and self.sale_type == 'support':
			support_ids = self.env['website.support.ticket'].search([('customer_support_id', '=', self.support_id.id)])
			if support_ids:
				repair_ids = self.env['repair.order'].search([('support_id', 'in', support_ids.ids)])
			if not all([repair.state == 'done' for repair in repair_ids]):
				raise UserError('You can not create invoice for this order becoz some repairs are not processed')
			invoice_vals.update({'repair_ids': [(6, 0, repair_ids.ids)]})
		return invoice_vals

	# @api.multi
	def open_repair_view(self):
		repair_ids = self.env['repair.order']
		for sale in self:
			if sale.support_id:
				support_ids = self.env['website.support.ticket'].search([('customer_support_id', '=', sale.support_id.id)])
				repair_ids = self.env['repair.order'].search([('support_id', 'in', support_ids.ids)])
		return {
			'name': _('Repairs'),
			# 'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'repair.order',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', repair_ids.ids)],
		}

	@api.model
	def _compute_repair_count(self):
		repair_ids = self.env['repair.order']
		for sale in self:
			if sale.support_id:
				support_ids = self.env['website.support.ticket'].search([('customer_support_id', '=', sale.support_id.id)])
				repair_ids = self.env['repair.order'].search([('support_id', 'in', support_ids.ids)])
				sale.repair_count = len(repair_ids.ids)
			else:
				sale.repair_count = 0

	repair_count = fields.Integer(compute='_compute_repair_count', string='Repairs')
	support_id = fields.Many2one('fms.customer.support', string="Support")
	sale_type = fields.Selection(selection_add=[('support', 'Support Service')], ondelete={'support': 'cascade'})

class MrpRepair(models.Model):
	_inherit = 'repair.order'

	# @api.multi
	def action_delivery_view(self):
		stock = self.env["stock.picking"]
		if self._context is None:
			context = {}
		# obj = self.env["ir.actions.act_window"].for_xml_id("stock", 'action_picking_tree_all')
		obj = self.env.ref('stock.action_picking_tree_all')
		# obj['context'] = self._context
		context = self._context
		stock = self.env["stock.picking"].search([('repair_id', '=', self.id)])
		if self.sale_order_ids and self.repair_job_type == 'defective_component_replacement':
			stock |= self.sale_order_ids.mapped('picking_ids')
		# obj['domain'] = [('id', 'in', stock.ids)]
		domain = [('id', 'in', stock.ids)]
		return {
			'name': _('Transfers'),
			'res_model': 'stock.picking',
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'domain': domain,
			'context': context,
		}

	@api.model
	def compute_delivery_count(self):
		picking_ids = self.env['stock.picking']
		for rec in self:
			picking_ids = self.env['stock.picking'].search([('repair_id', '=', rec.id)])
			if rec.sale_order_ids and rec.repair_job_type == 'defective_component_replacement':
				picking_ids |= rec.sale_order_ids.mapped('picking_ids')
			if picking_ids:
				rec.delivery_count = len(picking_ids.ids)
			else:
				rec.delivery_count = 0

	rma_note = fields.Text(string='Comments')
	internal_note = fields.Text(string='Remarks')
	order_count = fields.Integer(compute='_compute_order_count', string='Orders')
	is_open = fields.Boolean('Subscription Open', copy=False)
	is_close = fields.Boolean('Subscription Close', copy=False)
	repair_date = fields.Datetime(string='Create Date', default=fields.Datetime.now())
	close_date = fields.Datetime(string='Close Date') 
	vehicle_id = fields.Many2one('vehicle.master', string="Vehicle")
	ticket_state = fields.Selection(related='support_id.states', string="TKT Status", store=True)
	customer_support_id = fields.Many2one('fms.customer.support', string="Work Order")
	user_id = fields.Many2one('res.users', string="Engineer")
	service_sub_type = fields.Selection(related='support_id.service_sub_type', string='Job Sub Type', store=True)
	diff_product_id  = fields.Many2one('product.product', string='New Device')
	diff_lot_id = fields.Many2one('stock.lot', string='New Serial')
	sale_order_ids = fields.Many2many('sale.order')
	work_picking_ids = fields.Many2many('stock.picking', string='Work Order Picking')
	lot_placement = fields.Selection([('at_partner', 'Partner Place'), ('at_fms', 'Fms Tech')], string='Device Location', default='at_partner')
	invoice_method = fields.Selection([("after_repair", "Non Chargeable"), ("b4repair", "Chargeable"), ("none", "")], string="Invoice Method",
		default='after_repair', index=True, readonly=True, required=True, states={'draft': [('readonly', False)]},)

	# @api.multi
	def open_order_view(self):
		return {
			'name': _('Orders'),
			# 'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'sale.order',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', self.sale_order_ids.ids)],
		}

	@api.model
	def _compute_order_count(self):
		for sale in self:
			sale.order_count = len(sale.sale_order_ids.ids)

	# @api.multi
	def action_repair_end_delivery(self):
		move_line_ids = self.env['stock.move.line']
		lot_replace_id = self.env['stock.lot']
		# deactive_device
		if self.repair_job_type == 'deactive_device':
			subscription_id = self.env['sale.order'].search([('serial_no', '=', self.lot_id.id), ('vehicle_number', '=', self.vehicle_id.id),('is_subscription', '=', True)], limit=1)
			if subscription_id:
				subscription_id.write({'subscription_status': 'in_active', 'stage_category': 'closed'})
		# reactive_device
		if self.repair_job_type == 'reactive_device':
			subscription_id = self.env['sale.order'].search([('serial_no', '=', self.lot_id.id), ('vehicle_number', '=', self.vehicle_id.id),('is_subscription', '=', True)], limit=1)
			# if subscription_id:
			# 	default_stage = self.env['sale.subscription.stage'].search([('category', '=', 'progress')], limit=1)
			# 	subscription_id.write({'subscription_status': 'active', 'stage_category': 'progress', 'stage_id': default_stage})

		# defective_device_replacement
		if self.repair_job_type in ('defective_device_replacement', 'defective_component_replacement'):
			move_line_ids = self.env['stock.move.line']
			if self.repair_job_type == 'defective_device_replacement':
				lot_vehicle = self.vehicle_id
				lot_replace_id = self.diff_lot_id
				product_id = self.diff_product_id
				# check
				if not lot_vehicle:
					raise UserError('Please set lot and vehicle for this repair')
				if not lot_replace_id:
					raise UserError('Please set Defective serial')
				if not product_id:
					raise UserError('Please set Defective product')
				# device replace
				subscription_id = self.env['sale.order'].search([('serial_no', '=', self.lot_id.id), ('vehicle_number', '=', self.support_id.vehicle_id.id),('is_subscription', '=', True)], limit=1)
				if not subscription_id:
					raise UserError('There is no subscription for this lot and vehicle')
				else:
					subscription_id.serial_no = lot_replace_id.id
				# update vehicle
				self.support_id.vehicle_id.write({'device_serial_number_id': lot_replace_id.id, 'device_id': product_id.id})
				# return new lot
				for picking_id in self.picking_ids.filtered(lambda x: x.picking_type_id.code == 'outgoing' and x.state != 'done'):
					if not picking_id.product_lots_id:
						picking_id.product_lots_id = lot_replace_id and lot_replace_id.id
					for move in picking_id.move_lines:
						vals = {
							'move_id': move.id,
							'product_id': product_id.id,
							'product_uom_id': move.product_uom.id,
							'location_id': move.location_id.id,
							'location_dest_id': move.location_dest_id.id,
							'picking_id': move.picking_id.id,
							'lot_id': lot_replace_id and lot_replace_id.id,
							'qty_done': 1,
							}
						move_line_ids = self.env['stock.move.line'].create(vals)
					if move_line_ids:
						picking_id.button_validate()
			else:
				for picking_id in self.work_picking_ids.filtered(lambda x: x.picking_type_id.code == 'outgoing' and x.state != 'done'):
					if not picking_id.repair_id:
						picking_id.repair_id = self.id
					for move in picking_id.move_lines:
						operations = self.operations.filtered(lambda x: move.product_id == x.product_id)
						vals = {
								'move_id': move.id,
								'product_id': move.product_id.id,
								'product_uom_id': move.product_uom.id,
								'location_id': move.location_id.id,
								'location_dest_id': move.location_dest_id.id,
								'picking_id': move.picking_id.id,
								'qty_done': sum(operations.mapped('product_uom_qty')),
							}
						move_line_ids = self.env['stock.move.line'].create(vals)
					if move_line_ids:
						picking_id.button_validate()

		# re_installation
		if self.repair_job_type == 're_installation':
			if self.lot_placement == 'at_fms':
				self.location_move_customer()
			if self.service_sub_type == 'exist_reinstall': 
				vehicle_replace_id = self.vechicle_id and self.return_lot_id
				if not vehicle_replace_id:
					raise UserError('Vehicle or replacement lot is missing')
				subscription_id = self.env['sale.order'].search([('vehicle_number', '=', self.vechicle_id.id),('is_subscription', '=', True)], limit=1)
				if not subscription_id:
					raise UserError('Subscription not found for this vehicle')
				else:
					subscription_id.write({'serial_no': self.return_lot_id.id, 'subscription_status': 'active'})
				job_id = self.env['job.card'].search([('vehicle_number', '=', self.vechicle_id.id)], limit=1)
				if job_id:
					job_id.write({'device_serial_number_old_id': self.support_id.serial_no.id, 'device_serial_number_new_id': self.return_lot_id.id})
				if self.vehicle_id:
					self.vehicle_id.write({'device_serial_number_id': False})
				if self.vechicle_id:
					self.vechicle_id.write({'device_serial_number_id': self.return_lot_id and self.return_lot_id.id })
			else:
				# sub
				vehicle_replace_id = self.support_id and self.lot_id and self.vechicle_id 
				if not vehicle_replace_id:
					raise UserError('Lot or replacement vehicle is missing')
				subscription_id = self.env['sale.order'].search([('serial_no', '=', self.lot_id.id),('is_subscription', '=', True)], limit=1)
				if subscription_id:
					subscription_id.write({'vehicle_number': self.vechicle_id.id, 'subscription_status': 'active'})
				# job
				job_id = self.env['job.card'].search([('device_serial_number_new_id', '=', self.lot_id.id)], limit=1)
				if job_id:
					job_id.write({'vehicle_number': self.vechicle_id.id})
				# vechile
				if self.vechicle_id:
					self.vechicle_id.write({ 'device_serial_number_id': self.lot_id and self.lot_id.id })
				if self.vehicle_id:
					self.vehicle_id.write({'device_serial_number_id': False})

		if self.repair_job_type in ('removal', 'removal_returned'):
			if self.vehicle_id:
				self.vehicle_id.write({'device_serial_number_id': False})
			subscription_id = self.env['sale.order'].search([('serial_no', '=', self.lot_id.id),('is_subscription', '=', True)], limit=1)
			if subscription_id:
				subscription_id.write({'subscription_status': 'non_active'})
		self.write({'state': 'done', 'close_date': fields.Datetime.now()}) 

	# @api.multi
	def action_repair_start_delivery(self):
		""" Writes repair order state to 'Under Repair'@return: True"""
		for repair in self:
			if repair.filtered(lambda repair: repair.state not in ['confirmed', 'assigned']):
				raise UserError(_("Repair must be confirmed before starting reparation."))
			# removal
			if repair.repair_job_type == 'removal_returned':
					repair.location_move_stock()
			# defective
			if repair.repair_job_type ==  'defective_device_replacement':
				repair.location_move_stock()
				if repair.service_sub_type == 'same_remove_replace':
					repair.location_move_customer()
				else:
					repair.picking_out_for_diff_refurnish()
			# component
			if repair.repair_job_type == 'defective_component_replacement':
				if repair.invoice_method == 'after_repair' or not repair.sale_order_ids:
					repair.component_move_customer()
				else:
					picking_ids = repair.sale_order_ids.mapped('picking_ids').filtered(lambda x: x.state != 'done' and x.picking_type_id.code == 'outgoing')
					repair.work_picking_ids = [(4, pick) for pick in picking_ids.ids]
					for sale in repair.sale_order_ids:
						if sale.state not in ('sale', 'done'):
							raise UserError('Please confirm quotaion to process chargeable work order')
			repair.device_history()
			repair.mapped('operations').write({'state': 'confirmed'})
			repair.state = 'ready'

	def _prepare_repair_quote_lines(self, line):
		return {
			'product_id': line.product_id.id,
			'name': line.product_id.name,
			'product_uom_qty': line.product_uom_qty,
			'product_uom': line.product_uom.id,
			'price_unit': line.price_unit,
			'tax_id': [(6, 0, line.tax_id.ids)],
			'location_id': self.location_id and self.location_id.id,
			'location_dest_id': self.location_dest_id and self.location_dest_id.id,
			'repair_id': self.id
		}

	def processs_component_picking(self):
		for line in self.sale_order_ids.mapped('order_line').filtered(lambda x: x.product_id.type in ('consu', 'product')):
			lines = self._prepare_repair_quote_lines(line)
			self.env['repair.line'].create(lines)
		return True

	def picking_out_for_diff_refurnish(self):
		for repair in self:
			product = repair.product_id
			if repair.diff_product_id:
				product = repair.diff_product_id
			move_line_ids = self.env['stock.move.line']
			picking_type_id = self.env["stock.picking.type"]
			dest_location = self.env["stock.location"]
			source_location = self.env["stock.location"]
			if repair.picking_id:
				picking_type_id = repair.picking_id.picking_type_id
			else:
				picking_type_id = repair._find_outgoing_type()
			if not picking_type_id:
				raise UserError(_('Picking type not found customer picking'))
			dest_location = repair.location_dest_id
			if not dest_location:
				raise UserError(_('Destination location not found customer picking'))
			source_location = repair.location_id
			if not source_location:
				raise UserError(_('Source location not found for customer picking'))
			if source_location and dest_location and picking_type_id:
				vals = {
					'repair_id': repair.id,
					'partner_id': repair.partner_id.id,
					'origin': repair.name,
					'scheduled_date': datetime.now().date(),
					'location_id': source_location.id,
					'location_dest_id': dest_location.id,
					'picking_type_id': picking_type_id.id,
					'product_lots_id': repair.diff_lot_id and repair.diff_lot_id.id,
					'support_id': self.support_id and self.support_id.id,
				}
				picking_id = self.env['stock.picking'].create(vals)
				if picking_id:
					line_value = {
						'product_id': product.id,
						'name': product.name,
						'product_uom_qty': 1,
						'product_uom': product.uom_id.id,
						'location_id': source_location.id,
						'location_dest_id': dest_location.id,
						'picking_id': picking_id.id,
						'picking_type_id': picking_type_id.id,
					}
					self.env['stock.move'].create(line_value)
		return True

	def action_open_subscription(self):
		domain  = [('is_subscription', '=', True)]
		if self.lot_id:
			domain.append(('serial_no', '=', self.lot_id.id))
		if self.vehicle_id:
			domain.append(('vehicle_number', '=', self.vehicle_id.id))
		if self.lot_id or self.vehicle_id:
			subscription_id = self.env['sale.order'].search(domain, limit=1)
			if subscription_id:
				# stage = self.env['sale.subscription.stage'].search([('category', '=', 'progress')])
				# subscription_id.write({'state': stage.id if stage else False, 'subscription_status': 'active'})
				self.is_open = True
			if subscription_id and self.vehicle_id:
				self.vehicle_id.write({'device_serial_number_id': False})
		return True

	def action_close_subscription(self):
		sub_domain = [('is_subscription', '=', True)]
		job_domain = []
		if self.lot_id:
			sub_domain.append(('serial_no', '=', self.lot_id.id))
			job_domain.append(('device_serial_number_new_id', '=', self.lot_id.id))
		if self.vehicle_id:
			sub_domain.append(('vehicle_number', '=', self.vehicle_id.id))
			job_domain.append(('vehicle_number', '=', self.vehicle_id.id))
		if self.lot_id or self.vehicle_id:
			job_id = self.env['job.card'].search(job_domain, limit=1)
			if job_id:
				job_id.write({
					'vehicle_number_old': self.vehicle_id.id,
					'vehicle_number': False,
					'device_serial_number_new_id': False,
					'device_serial_number_old_id': self.lot_id.id
				})				
			subscription_id = self.env['sale.order'].search(sub_domain, limit=1)
			if subscription_id:
				# stage = self.env['sale.subscription.stage'].search([('category', '=', 'closed')])
				# subscription_id.write({'state': stage.id if stage else False, 'subscription_status': 'in_active'})
				self.is_close = True
			if subscription_id and self.vehicle_id:
				self.vehicle_id.write({'device_serial_number_id': False})
		return True


class WebsiteSupport(models.Model):
	_inherit = 'website.support.ticket'

	# @api.one
	@api.depends('state_id')
	def _compute_unattend(self):
		for rec in self:
			#BACK COMPATABLITY Use open and customer reply as default unattended states
			# opened_state = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_open')
			opened_state = self.env.ref('website_support.website_ticket_state_open')
			# customer_replied_state = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_customer_replied')
			customer_replied_state = self.env.ref('website_support.website_ticket_state_customer_replied')
			if rec.state_id and rec._fields:
				state_field = rec._fields.get('state')
				if state_field and state_field.type == 'many2one':
					if rec.state_id == opened_state or rec.state_id == customer_replied_state or rec.state_id.unattended:
						rec.unattended = True
					else:
						rec.unattended = False
				else:
					rec.unattended = False
			else:
				rec.unattended = False

	# @api.multi
	def open_close_ticket_wizard(self):
		repair_ids = self.env['repair.order'].search([('support_id', '=', self.id), ('state', '!=', 'cancel')])
		if not all(rec.state == 'done' for rec in repair_ids):
			raise UserError('Some ticket are not in done state')
		return {
			'name': "Close Support Ticket",
			'type': 'ir.actions.act_window',
			# 'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'website.support.ticket.close',
			'context': {'default_ticket_id': self.id},
			'target': 'new'
		}

	@api.depends('sale_order_ids', 'sale_order_ids.state')
	def _quote_state(self):
		for rec in self:
			for sale in rec.sale_order_ids:
				if sale.state == 'sale':
					rec.quote_state = True
				else:
					rec.quote_state = False

	engineer_id = fields.Many2one('res.users', string="Engineer")
	is_ticket = fields.Boolean(copy=False)
	quote_state = fields.Boolean(compute='_quote_state', string='Quote Status', store=True)
	customer_support_id = fields.Many2one('fms.customer.support', string="Work Order")
	billing_method = fields.Selection([('chargeable', 'Chargeable'), ('no_chargeable', 'Non Chargeable')], default='no_chargeable')
	sale_order_ids = fields.Many2many('sale.order')
	repair_id = fields.Many2one('repair.order', string="Repair")
	repair_state = fields.Selection(related='repair_id.state', string="Repair State", store=True)
	repair_job_type = fields.Selection([
		('calibartion_testing', 'Inspection'),
		('defective_component_replacement', 'Defective Component Replacement'),
		('defective_device_replacement', 'Defective Device Replacement'),
		('deactive_device', 'Deactivation of Device'), 
		('reactive_device', 'Reactivation of Device'), 
		('removal', 'Remove-Retain by Client'),
		('removal_returned', 'Remove-Return to FMS'),
		('re_installation', 'Re-Installation Vehicle'),
		('non_technical', '')], string="Service Type")
	service_sub_type = fields.Selection([
			('sub_calibration_test', 'Inspection'),
			('sub_deactive_device', 'Deactivation of Device'),
			('sub_reactive_device', 'Reactivation of Device'),
			('sub_comp_replace', 'Defective Device - Component Replacement'),
			('same_remove_replace', 'Defective Device - Remove/Replace (Same Type)'),
			('diff_remove_replace','Defective Device - Remove/Replace (Differet type)'),
			('ref_remove_replace','Defective Device - Remove/Replace (Same Device)'),
			('remove_retain', 'Active Device - Remove-Retain by Client'), 
			('remove_return', 'Active Device - Remove-Retain to FMS'),
			('remove_reinstall', 'Active Device - Remove/Reinstall (Another Vehicle)'),
			('exist_reinstall', 'Inactive Device - Re-install Existing Fleet Vehicle'),
			('new_reinstall', 'Inactive Device - Re-install New Vehicle (Create)'),
			('replace_same_device','')
		])

	# @api.multi
	def create_repair(self):
		for rec in self:
			if not rec.service_sub_type == 'exist_reinstall' and not rec.serial_no:
				raise UserError(_('Device serial number is missing'))
			repair_dict = rec._prepaire_repair(rec)
			repair_id = self.env['repair.order'].create(repair_dict)
			if rec.billing_method == 'chargeable' and self.repair_job_type == 'defective_component_replacement':
				repair_id.processs_component_picking()
			rec.write({'states': 'under_repair', 'is_ticket': True, 'repair_id': repair_id and repair_id.id})
			return {
				'type': 'ir.actions.act_window',
				'name': repair_id.name,
				'res_id': repair_id.id,
				'views': [[False, 'form']],
				'res_model': 'repair.order',
				'view_mode': 'tree,form',
			}

	def find_picking_id(self):
		move_line_id = self.env['stock.move.line']
		location_dest_id = self.env.ref('stock.stock_location_customers')
		warehouse = self.env['stock.warehouse'].search([(('company_id', '=', self.env.user.company_id.id))], limit=1)
		location_id = warehouse.lot_stock_id if warehouse else False
		if location_id and location_dest_id:
			domain = [('location_id', '=', location_id.id), ('location_dest_id', '=', location_dest_id.id),('picking_id.partner_id', '=', self.partner_id.id), ('lot_id', '=', self.serial_no.id), ('move_id.picking_code', '=', 'outgoing'), ('state', '=', 'done')]
			move_line_id = self.env['stock.move.line'].search(domain, order='id desc', limit=1)
		if not move_line_id:
			domain = [('picking_id.partner_id', '=', self.partner_id.id), ('lot_id', '=', self.serial_no.id), ('move_id.picking_code', '=', 'outgoing'), ('state', '=', 'done')]
			domain.append(('location_dest_id.loc_interanl_type', 'in', ('lease', 'rental')))
			move_line_id = self.env['stock.move.line'].search(domain, order='id desc', limit=1)
		if not move_line_id:
			domain = [('picking_id.partner_id', '=', self.partner_id.id), ('lot_id', '=', self.serial_no.id), ('move_id.picking_code', '=', 'outgoing'), ('state', '=', 'done')]
			domain.append(('picking_id.repair_id', '!=', False))
			move_line_id = self.env['stock.move.line'].search(domain, order='id desc', limit=1)
		return move_line_id

	def _prepaire_repair(self, repair):
		move_line_id = self.env['stock.move.line']
		picking_id = self.env['stock.picking']
		location_dest_id = self.env['stock.location']
		location_id = self.env['stock.location']
		product = self.device_duplicate or self.vehicle_id and self.vehicle_id.device_id or self.serial_no and self.serial_no.product_id
		if not product:
			raise UserError('Lot or vehicle or product is missing')
		move_line_id = self.find_picking_id()
		if not move_line_id:
			quants = self.serial_no.quant_ids.filtered(lambda q: q.location_id.loc_interanl_type in ['lease', 'rental'] and q.quantity == 1)
			location_dest_id = quants.mapped('location_id')
			if not quants:
				quants = self.serial_no.quant_ids.filtered(lambda q: q.location_id.usage in ['internal', 'transit'] and q.quantity == 1)
				location_dest_id = quants.mapped('location_id')
			if not location_dest_id:
				location_dest_id = self.env.ref('stock.stock_location_customers')
			if not location_dest_id:
				raise UserError(_('Customer location not found'))
			warehouse = self.env['stock.warehouse'].search([(('company_id', '=', self.env.user.company_id.id))], limit=1)
			location_id = warehouse.lot_stock_id if warehouse else False
			if not location_id:
				raise UserError(_('Stock location not found'))
		return {
			'repair_date': self.schedule_time and self.schedule_time or fields.Datetime.now(),
			'vehicle_id': self.vehicle_id and self.vehicle_id.id or False,
			'user_id': self.engineer_id and self.engineer_id.id,
			'invoice_method': 'b4repair' if self.billing_method == 'chargeable' else 'after_repair',
			'sale_order_ids': [(4, x) for x in self.customer_support_id.sale_order_ids.ids],
			'support_id': self and self.id,
			'customer_support_id': self.customer_support_id and self.customer_support_id.id,
			'partner_invoice_id': self.partner_id and self.partner_id.id,
			'guarantee_limit': self.vehicle_id.activation_date,
			'lot_id': self.serial_no and self.serial_no.id or False,
			'product_id': product.id,
			'partner_id': self.partner_id and self.partner_id.id,
			'product_uom': product.uom_id.id or False,
			'vechicle_id': self.vehicle_id and self.vehicle_id.id if self.service_sub_type == 'exist_reinstall' else False,
			'diff_product_id': product.id if self.service_sub_type == 'same_remove_replace' else False,
			'picking_id': move_line_id.picking_id and move_line_id.picking_id.id if move_line_id else False,
			# 'location_dest_id' : move_line_id.location_dest_id and move_line_id.location_dest_id.id if move_line_id else location_dest_id and location_dest_id.id or False,
			'location_id': move_line_id.location_id and move_line_id.location_id.id if move_line_id else location_id and location_id.id or False,
		}


class FmsCustomerSupport(models.Model):
	_name = "fms.customer.support"
	_description = "Fms Customer Support"
	_order = "id desc"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	name = fields.Char(string="Name", readonly=True, copy=False)
	subject = fields.Char(string="Subject")
	date = fields.Datetime(string="Create Date", default=fields.Datetime.now())
	close_date = fields.Datetime(string="Close Date")
	partner_id = fields.Many2one('res.partner', string="Customer")
	sale_user_id = fields.Many2one('res.users', string="Sales User")
	user_id = fields.Many2one('res.users', string="Reporting User", default=lambda self: self.env.user)
	contact_name = fields.Char(string='Contact Name')
	email = fields.Char(string="Email")
	phone = fields.Char(string="Phone")
	ticket_done = fields.Boolean(copy=False)
	quote_done = fields.Boolean(copy=False)
	no_of_vehicles = fields.Integer(default=1)
	service_type = fields.Selection([
			('calibartion_testing', 'Inspection'),
			('defective_component_replacement', 'Defective Component Replacement'),
			('defective_device_replacement', 'Defective Device Movement'), 
			('deactive_device', 'Deactivation'),
			('reactive_device', 'Reactivation'), 
			('active_device', 'Active Device Movement'), 
			('inactive_device', 'In-Active Device Movement')
		])	
	service_sub_type = fields.Selection([
			('sub_calibration_test', 'Inspection'),
			('sub_deactive_device', 'Deactivation of Device'),
			('sub_reactive_device', 'Reactivation of Device'),
			('sub_comp_replace', 'Defective Device - Component Replacement'),
			('same_remove_replace', 'Defective Device - Remove/Replace (Same Type)'),
			('diff_remove_replace','Defective Device - Remove/Replace (Differet type)'),
			('ref_remove_replace','Defective Device - Remove/Replace (Same Device)'),
			('remove_retain', 'Active Device - Remove-Retain by Client'), 
			('remove_return', 'Active Device - Remove-Retain to FMS'),
			('remove_reinstall', 'Active Device - Remove/Reinstall (Another Vehicle)'),
			('exist_reinstall', 'Inactive Device - Re-install Existing Fleet Vehicle'),
			('new_reinstall', 'Inactive Device - Re-install New Vehicle (Create)'),
			('replace_same_device','')
		])

	work_order_type = fields.Selection([('technical', 'Technical'),('non_technical', 'Non Technical')], default='technical',copy=False)
	billing_method = fields.Selection([('chargeable', 'Chargeable'), ('no_chargeable', 'Non Chargeable')], default='no_chargeable', copy=False)
	category = fields.Many2one('website.support.ticket.category', string="Category", track_visibility='onchange')
	sub_category_id = fields.Many2one('website.support.ticket.subcategory', string="Sub Category")
	description = fields.Text(string="Description")
	support_comment = fields.Text(string="Support Comment")
	support_count = fields.Integer('Count', compute='compute_support_count')
	quotations_count = fields.Integer(compute='_quotations_count', string='Quotations')
	invoice_state = fields.Boolean(compute='_invoice_state', string='Invoice Status', store=True)
	sale_order_ids = fields.One2many('sale.order', 'support_id')
	state = fields.Selection([('draft', 'Draft'), ('confirm', 'Open'), ('quote', 'Quotation'), ('ticket', 'In progress'), ('done', 'Closed'), ('cancel', 'Cancel')], default='draft', string="Status")

	@api.onchange('partner_id')
	def onchange_partner_id(self):
		if self.partner_id:
			self.email = self.partner_id.email
			self.phone = self.partner_id.phone
			self.sale_user_id = self.partner_id.user_id and self.partner_id.user_id.id

	@api.model
	def create(self, vals):
		if vals.get('name', 'New') == 'New':
			vals['name'] = self.env['ir.sequence'].next_by_code('fms.customer.support') or '/'
		return super(FmsCustomerSupport, self).create(vals)

	# @api.multi
	def button_confirm(self):
		if self.work_order_type == 'technical':
			self.write({'state': 'confirm'})
		else:
			self.write({'state': 'ticket'})

	# @api.multi
	def button_done(self):
		ticket_ids = self.env['website.support.ticket'].search([('customer_support_id', '=', self.id), ('states', '!=', 'done')])
		if ticket_ids:
			raise UserError('Some support tickets are still need to process')
		self.write({'state': 'done', 'close_date': fields.Datetime.now()})

	# @api.multi
	def button_quotation(self):
		self.write({'state': 'quote'})

	# @api.multi
	def button_cancel(self):
		ticket_ids = self.env['website.support.ticket'].search([('customer_support_id', '=', self.id)])
		if ticket_ids:
			repair_ids = self.env['repair.order'].search([('support_id', 'in', ticket_ids.ids)])
			if any(rec.state == 'done' for rec in repair_ids):
				raise UserError('Some repair order are in done state')
			ticket_ids.write({'states': 'cancel'})	
		for sale in self.sale_order_ids:
			vals = {'order_id': sale.id, 'cancellation_reason' : 'customer ticket cancelled'}
			sale_cancel_wizard = self.env['sale.advance.cancel.inv'].with_context(active_ids=sale.id, active_model='sale.order').create(vals)
			if sale_cancel_wizard:
				sale_cancel_wizard.update_details()
		self.write({'state': 'cancel'})

	def _get_service_type(self):
		if self.service_sub_type == 'sub_comp_replace':
			return 'defective_component_replacement'
		if self.service_sub_type == 'sub_calibration_test':
			return 'calibartion_testing'
		if self.service_sub_type == 'sub_deactive_device':
				return 'deactive_device'
		if self.service_sub_type == 'sub_reactive_device':
				return 'reactive_device'
		if self.service_sub_type in ('same_remove_replace', 'diff_remove_replace', 'ref_remove_replace'):
			return 'defective_device_replacement'
		if self.service_sub_type in ('exist_reinstall', 'new_reinstall'):
			return 're_installation'
		if self.service_sub_type == 'remove_reinstall':
			return 're_installation'
		if self.service_sub_type == 'remove_retain':
			return 'removal'
		if self.service_sub_type == 'remove_return':
			return 'removal_returned'
		return False

	# @api.multi
	def create_ticket(self):
		for support in self:
			if self.billing_method == 'chargeable' and not self.sale_order_ids:
				raise UserError(_('Please create quotation first for chargeable work orders'))
			if not support.get_service_type():
				raise UserError(_('This combination are not exit : %s') %(support.service_sub_type))
			for line in range(support.no_of_vehicles):
				vals = {
					'partner_id': support.partner_id.id,
					'subject': "%s : %s" %(support.name, support.subject),
					'ticket_create_date': support.date,
					'user_id' : support.user_id and support.user_id.id,
					'person_name' : support.contact_name,
					'email': support.email,
					'phone_number': support.phone,
					'repair_job_type': support.get_service_type(),
					'service_sub_type': support.service_sub_type,
					'billing_method': support.billing_method,
					'customer_support_id': support.id,
					'description': support.description,
					'sale_order_ids': [(4, x) for x in support.sale_order_ids.ids],
				}
				self.env['website.support.ticket'].create(vals)
			support.write({'state': 'ticket', 'ticket_done': True})
		return True

	@api.depends('sale_order_ids', 'sale_order_ids.state')
	def _invoice_state(self):
		for rec in self:
			for sale in rec.sale_order_ids:
				if sale.state == 'sale':
					rec.invoice_state = True
				else:
					rec.invoice_state = False

	# @api.model
	def compute_support_count(self):
		for support in self:
			support.support_count = len(self.env['website.support.ticket'].search([('customer_support_id', '=', support.id)]))
			# support.support_count = len(support_ids.ids)

	# @api.multi
	def open_support_view(self):
		support_ids = self.env['website.support.ticket'].search([('customer_support_id', '=', self.id)])
		return {
			'name': _('Support Tickets'),
			# 'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'website.support.ticket',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', support_ids.ids)],
		}

	def _quotations_count(self):
		for rec in self:
			rec.quotations_count = len(self.env['sale.order'].search([('support_id', '=', rec.id)]))
			# rec.quotations_count = len(order_id.ids)

	def prepair_sale_order(self):
		return {
				'partner_id': self.partner_id.id,
				'date_order': datetime.now().date(),
				'sale_type': 'support',
				'support_id': self.id,
				'user_id': self.sale_user_id and self.sale_user_id.id,
			}

	def create_quotation(self):
		for rec in self:
			values = self.prepair_sale_order()
			order_id = self.env['sale.order'].create(values)
			rec.write({'sale_order_ids': [(4, x.id) for x in order_id], 'quote_done': True})
			return {
				'type': 'ir.actions.act_window',
				'name': order_id.name,
				'res_id': order_id.id,
				'views': [[False, 'form']],
				'res_model': 'sale.order',
				'view_mode': 'tree,form',
			}

	# @api.multi
	def open_quotations(self):
		order_ids = self.env['sale.order'].search([('support_id', '=', self.id)])
		return {
			'name': _('Quotes'),
			# 'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'sale.order',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', order_ids.ids)],
		}