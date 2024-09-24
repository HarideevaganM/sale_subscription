# -*- coding: utf-8 -*-
import csv
import base64
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class JobCard(models.Model):
	_inherit = "job.card"

	device_status = fields.Selection([('active', 'Active'), ('in_active', 'In Active'), ('non_active', 'Non Active')], string='Device Status')
	repair_id = fields.Many2one("repair.order", "Repair")
	repair_job_type = fields.Selection([('re_installation', 'Re-Installation Vehicle'),
		('defective_device_replacement', 'Defective Device replacement'),
		('defective_component_replacement', 'Defective Component Replacement'),
		('calibartion_testing', 'Calibration and Testing'),
		('removal', 'Removal and Retained'),
		('removal_returned', 'Removal and Returned'),
		('deactive_device', 'Deactivation of Device'), 
		('reactive_device', 'Reactivation of Device'), 
		('non_technical', 'Non Technical')], string="Support Type")


class SubcriptionCloseWizard(models.TransientModel):
	_name = 'subcription.close.wizard'
	_description = "Subcription Close Wizard"

	def action_subcription_close(self):
		active_id = self.env.context.get('active_id')
		if active_id:
			repair = self.env['repair.order'].browse(active_id)
			if repair:
				repair.job_vehicle_subcription()
		return True

	def no_action_subcription_close(self):
		active_id = self.env.context.get('active_id')
		if active_id:
			repair = self.env['repair.order'].browse(active_id)
			if repair:
				repair.no_job_vehicle_subcription()
		return True

class AccountMove(models.Model):
	_inherit = 'account.move'

	support_id = fields.Many2one("website.support.ticket", "Ticket")

class StockLocation(models.Model):
	_inherit = "stock.location"

	loc_interanl_type = fields.Selection([('material', 'Material'), ('spare', 'Spare'), ('defective', 'Defective'), ('repair', 'Repair'), ('rental', 'Rental'), ('lease', 'Lease'), ('other', 'Other')])

class StockPicking(models.Model):
	_inherit = "stock.picking"

	support_id = fields.Many2one('website.support.ticket')

class RepairLine(models.Model):
	_inherit = 'repair.line'

	type = fields.Selection([('add', 'Add'),('remove', 'Remove')], 'Type', required=True, default='add')

class RepairOrder(models.Model):
	_inherit = 'repair.order'

	def compute_job_count(self):
		for repair in self:
			job_ids = self.env['job.card'].search([('repair_id', '=', repair.id)])
			repair.job_count = len(job_ids.ids)

	picking_ids = fields.One2many('stock.picking', 'repair_id')
	repair_job_type = fields.Selection(related='support_id.repair_job_type', string='Job Type', store=True)
	support_id = fields.Many2one('website.support.ticket')
	vechicle_id = fields.Many2one('vehicle.master', string='New Vehicle')
	return_lot_id = fields.Many2one('stock.lot', string='New Serial')
	invoice_count = fields.Integer('Invoices', compute='compute_repair_invoice_count')
	job_count = fields.Integer('Invoices', compute='compute_job_count')
	location_dest_id = fields.Many2one('stock.location', 'Delivery Location', states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]})

	@api.onchange('location_id')
	def onchange_location_id(self):
		if self.location_id:
			self.location_dest_id = self.location_id.id
		else:
			self.location_dest_id = False

	# @api.multi
	def open_job_view(self):
		for repair in self:
			job_ids = self.env['job.card'].search([('repair_id', '=', repair.id)])
			return {
				'name': _('Job Card'),
				# 'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'job.card',
				'view_id': False,
				'type': 'ir.actions.act_window',
				'domain': [('id', 'in', job_ids.ids)],
			}

	# @api.multi
	def create_job_card(self):
		return True

	@api.onchange('vechicle_id')
	def onchange_vechicle(self):
		if self.vechicle_id:
			lot = self.vechicle_id.device_serial_number_id
			if lot:
				raise UserError('You can not select this vehicle. because it is already allocated')
			else:
				subscription_id = self.env['sale.order'].search([('vehicle_number', '=', self.vechicle_id.id), ('is_subscription', '=', True)], limit=1)
				if subscription_id: 
					raise UserError('You can not select this vehicle. Select other vehicle or create new vehicle')

	@api.onchange('return_lot_id')
	def onchange_return_lot(self):
		if self.return_lot_id:
			quants = self.return_lot_id.quant_ids.filtered(lambda q: q.location_id.usage in ['internal', 'transit', 'customer'])
			lot_product_qty = sum(quants.mapped('quantity'))
			if lot_product_qty < 1:
				raise UserError(_('This device serial is not availabe'))

	# @api.multi
	def action_invoice_view(self):
		if self._context is None:
			context = {}
		# invoice_tree = self.env["ir.actions.act_window"].for_xml_id("account", 'action_invoice_tree1')
		invoice_tree = self.env.ref('account.action_move_out_invoice_type')
		invoice_tree['context'] = self._context
		invoices = self.env["account.move"].search([('repair_id', '=', self.id)])
		invoice_tree['domain'] = [('id', 'in', invoices.ids)]
		return invoice_tree

	# @api.multi
	def action_invoice_create(self, group=False):
		invoice_dict = super(RepairOrder, self).action_invoice_create(group=False)
		for value in invoice_dict.values():
			if value:
				invoice_id = self.env['account.move'].browse(value)
				invoice_id.repair_id = self.id
		return invoice_dict

	# @api.multi
	def action_invoice_create_maintainance(self, group=False):
		invoice_id = super(RepairOrder, self).action_invoice_create_maintainance()
		if invoice_id:
			invoice_id.repair_id = self.id
		return invoice_id

	# @api.multi
	def action_invoice_create_maintainance_before(self, group=False):
		invoice_dict = super(RepairOrder, self).action_invoice_create_maintainance_before()
		for value in invoice_dict.values():
			if value:
				invoice_id = self.env['account.move'].browse(value)
				invoice_id.repair_id = self.id
		return invoice_dict 

	def compute_repair_invoice_count(self):
		for repair in self:
			invoice_ids = self.env['account.move'].search([('repair_id', '=', repair.id)])
			repair.invoice_count = len(invoice_ids.ids)

	# @api.multi
	def action_repair_end_delivery(self):
		move_line_ids = self.env['stock.move.line']
		if self.repair_job_type == 'defective_device_replacement':
			lot_replace_id = self.return_lot_id and self.support_id and self.lot_id
			if not lot_replace_id:
				raise UserError('Please set replacement serial device no')
			else:
				# device replace
				subscription_id = self.env['sale.order'].search([('serial_no', '=', self.lot_id.id), ('vehicle_number', '=', self.support_id.vehicle_id.id), ('is_subscription', '=', True)], limit=1)
				if not subscription_id:
					raise UserError('There is no subscription for this lot and vehicle')
				else:
					subscription_id.serial_no = self.return_lot_id.id
				job_id = self.env['job.card'].search([('device_serial_number_new_id', '=', self.lot_id.id), ('vehicle_number', '=', self.support_id.vehicle_id.id)], limit=1)
				if job_id:
					job_id.write({'device_serial_number_new_id': self.return_lot_id.id , 'device_serial_number_old_id': self.lot_id.id})
				self.support_id.vehicle_id.write({'device_serial_number_id': self.return_lot_id.id})
				# return new lot
				picking_id = self.picking_ids.filtered(lambda x: x.picking_type_id.code == 'outgoing' and x.state != 'done')
				if picking_id:
					if not picking_id.product_lots_id:
						picking_id.product_lots_id = self.return_lot_id.id
					if not picking_id.move_line_ids:
						for move in picking_id.move_lines:
							vals = {
								'move_id': move.id,
								'product_id': move.product_id.id,
								'product_uom_id': move.product_uom.id,
								'location_id': move.location_id.id,
								'location_dest_id': move.location_dest_id.id,
								'picking_id': move.picking_id.id,
								'lot_id': self.return_lot_id and self.return_lot_id.id,
								'qty_done': 1,
								}
							move_line_ids = self.env['stock.move.line'].create(vals)
					if move_line_ids:
						picking_id.action_done()

		# re_installation
		if self.repair_job_type == 're_installation':
			vehicle_replace_id = self.support_id and self.lot_id and self.vechicle_id  
			if not vehicle_replace_id:
				raise UserError('Please set replacement vehicle number')
			else:
				# re_installation
				subscription_id = self.env['sale.order'].search([('serial_no', '=', self.lot_id.id), ('vehicle_number', '=', self.support_id.vehicle_id.id), ('is_subscription', '=', True)], limit=1)
				if not subscription_id:
					raise UserError('There is no subscription for this lot and vehicle')
				else:
					subscription_id.vehicle_number = self.vechicle_id.id
				job_id = self.env['job.card'].search([('device_serial_number_new_id', '=', self.lot_id.id), ('vehicle_number', '=', self.support_id.vehicle_id.id)], limit=1)
				if job_id:
					job_id.write({'vehicle_number_old': self.support_id.vehicle_id.id, 'vehicle_number': self.vechicle_id.id})
				if self.support_id.vehicle_id:
					self.vechicle_id.write({
						'device_serial_number_id': self.support_id.serial_no and self.support_id.serial_no.id,
						'installation_location_id': self.support_id.vehicle_id.installation_location_id and self.support_id.vehicle_id.installation_location_id.id,
						'installation_date': self.support_id.vehicle_id.installation_date,
						'activation_date': self.support_id.vehicle_id.activation_date,
					})
		self.state = 'done'  

	def action_validate(self):
		self.ensure_one()
		self.action_repair_confirm()
		for rec in self:
			mail_template = self.env.ref('fms_repair_extended.email_template_maintenance_confirm')
			mail_template.sudo().send_mail(rec.id, force_send=True)

	# @api.multi
	def component_move_customer(self):
		picking_type_id = self.env["stock.picking.type"]
		dest_location = self.env["stock.location"]
		location_id = self.env["stock.location"]
		dest_location = self.location_dest_id
		if not dest_location:
			raise UserError(_('Source location not found for component'))
		location_id = self.env['stock.location'].search([('usage', '=', 'internal'), ('loc_interanl_type', '=', 'spare')], limit=1)
		if not location_id:
			raise UserError(_('Spare location not found for component'))
		if self.picking_id:
			picking_type_id = self.picking_id.picking_type_id
		else:
			picking_type_id = self._find_outgoing_type()
		if not picking_type_id:
			raise UserError(_('Picking type not found for component'))
		operations = self.operations.filtered(lambda x: x.product_id and x.product_id.type in ('product', 'consu'))
		if dest_location and picking_type_id and location_id and operations:
			vals = {
					'repair_id': self.id,
					'origin': self.name,
					'partner_id': self.partner_id.id,
					'scheduled_date': datetime.now().date(),
					'location_id': location_id.id,
					'location_dest_id': dest_location.id,
					'picking_type_id': picking_type_id.id,
					'support_id': self.support_id and self.support_id.id,
				}
			picking_id = self.env['stock.picking'].create(vals)
			if picking_id:
				for comp in operations:
					line_value = {
						'product_id': comp.product_id and comp.product_id.id,
						'name': comp.name,
						'product_uom_qty': comp.product_uom_qty,
						'product_uom': comp.product_uom and comp.product_uom.id,
						'location_id': location_id and location_id.id,
						'location_dest_id': dest_location and dest_location.id,
						'picking_id': picking_id and picking_id.id,
						'picking_type_id': picking_type_id.id,
					}
					move_id = self.env['stock.move'].create(line_value)
					move_id.picking_id.action_assign()
					if move_id.move_line_ids:
						move_id.move_line_ids.write({'qty_done': comp.product_uom_qty})
				picking_id.action_done()

	def _find_outgoing_type(self):
		company_id = self.env.context.get('company_id') or self.env.user.company_id.id
		return_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)], limit=1)
		if not return_type_id:
			return_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)], limit=1)
		return return_type_id

	# @api.multi
	def location_move_stock(self):
		for repair in self:
			move_line_ids = self.env['stock.move.line']
			picking_type_id = self.env["stock.picking.type"]
			dest_location = self.env["stock.location"]
			source_location = self.env["stock.location"]
			if repair.lot_id:
				dest_location = self.env['stock.location'].search([('usage', '=', 'internal'), ('loc_interanl_type', '=', 'defective')], limit=1)
				if not dest_location:
					raise UserError(_('Defective location not found for return picking'))
				# source_location = repair.location_dest_id
				# source = self.env['stock.quant'].search([('product_id', '=', repair.product_id.id), ('lot_id', '=', repair.lot_id.id), ('available_quantity', '>', 0)])
				source = self.env['stock.move.line'].search([('product_id', '=', repair.product_id.id), ('lot_id', '=', repair.lot_id.id), ('qty_done', '>=', 1), ('state', '=', 'done')], order='date desc')
				source1 = self.env['stock.quant'].search([('product_id', '=', repair.product_id.id), ('lot_id', '=', repair.lot_id.id), ('available_quantity', '>=', 1)], order='create_date desc')
				if source:
					source_location = source[0].location_dest_id
				elif source1:
					source_location = source1[0].location_id
				if not source_location:
					raise UserError(_('Source location not found for Return Picking. Kindly fill Destination Location in Location Tab'))
				if repair.picking_id:
					picking_type_id = repair.picking_id.picking_type_id and repair.picking_id.picking_type_id.return_picking_type_id
				else:
					picking_return_id = repair._find_outgoing_type()
					if picking_return_id:
						picking_type_id = picking_return_id.return_picking_type_id
				if not picking_type_id:
					raise UserError(_('Picking type not found for return picking'))
			if source_location and dest_location and picking_type_id:
				vals = {
					'repair_id': repair.id,
					'partner_id': repair.partner_id.id,
					'origin': repair.name,
					'scheduled_date': datetime.now().date(),
					'location_id': source_location.id,
					'location_dest_id': dest_location.id,
					'picking_type_id': picking_type_id.id,
					'product_lots_id':repair.lot_id.id,
					'support_id': repair.support_id and repair.support_id.id,
				}
				picking_id = self.env['stock.picking'].create(vals)
				if picking_id:
					line_value = {
						'product_id': repair.product_id.id,
						'name': repair.product_id.name,
						'product_uom_qty': 1,
						'product_uom': repair.product_id.uom_id.id,
						'location_id': source_location.id,
						'location_dest_id': dest_location.id,
						'picking_id': picking_id.id,
						'picking_type_id': picking_type_id.id,
					}
					move = self.env['stock.move'].create(line_value)
					if move and not move.move_line_ids:
						vals = {
							'move_id': move.id,
							'product_id': move.product_id.id,
							'product_uom_id': move.product_uom.id,
							'location_id': move.location_id.id,
							'location_dest_id': move.location_dest_id.id,
							'picking_id': move.picking_id.id,
							'lot_id': repair.lot_id and repair.lot_id.id,
							'qty_done': 1,
							}
						move_line_ids = self.env['stock.move.line'].create(vals)
					if move_line_ids:
						picking_id._action_done()

	# @api.multi
	def location_move_customer(self):
		for repair in self:
			move_line_ids = self.env['stock.move.line']
			picking_type_id = self.env["stock.picking.type"]
			dest_location = self.env["stock.location"]
			source_location = self.env["stock.location"]
			if repair.picking_id:
				picking_type_id = repair.picking_id.picking_type_id
			else:
				picking_type_id = self._find_outgoing_type()
			if not picking_type_id:
				raise UserError(_('Picking type not found customer picking'))
			destination = self.env['stock.move.line'].search([('product_id', '=', repair.product_id.id), ('lot_id', '=', repair.lot_id.id), ('state', '=', 'done')], order='date desc')
			dest_location = destination[0].location_id if destination else repair.location_dest_id
			if not dest_location:
				raise UserError(_('Destination location not found customer picking'))
			source = self.env['stock.move.line'].search([('product_id', '=', repair.diff_product_id.id), ('lot_id', '=', repair.diff_lot_id.id), ('state', '=', 'done')],order='date desc')
			source1 = self.env['stock.quant'].search([('product_id', '=', repair.diff_product_id.id), ('lot_id', '=', repair.diff_lot_id.id), ('available_quantity', '>=', 1)], order='create_date desc')
			if source:
				source_location = source[0].location_dest_id
			elif source1:
				source_location = source1[0].location_id
			# source_location = repair.location_id
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
					'product_lots_id': repair.return_lot_id and repair.return_lot_id.id,
					'support_id': self.support_id and self.support_id.id,
				}
				picking_id = self.env['stock.picking'].create(vals)
				if picking_id:
					line_value = {
						'product_id': repair.product_id.id,
						'name': repair.product_id.name,
						'product_uom_qty': 1,
						'product_uom': repair.product_id.uom_id.id,
						'location_id': source_location.id,
						'location_dest_id': dest_location.id,
						'picking_id': picking_id.id,
						'picking_type_id': picking_type_id.id,
					}
					move = self.env['stock.move'].create(line_value)
					if move and repair.return_lot_id and not move.move_line_ids:
						vals = {
							'move_id': move.id,
							'product_id': move.product_id.id,
							'product_uom_id': move.product_uom.id,
							'location_id': move.location_id.id,
							'location_dest_id': move.location_dest_id.id,
							'picking_id': move.picking_id.id,
							'lot_id': repair.return_lot_id and repair.return_lot_id.id,
							'qty_done': 1,
							}
						move_line_ids = self.env['stock.move.line'].create(vals)
					if move_line_ids:
						picking_id.action_done()

	# @api.multi
	def action_repair_start_delivery(self):
		""" Writes repair order state to 'Under Repair'@return: True"""
		for repair in self:
			if repair.filtered(lambda repair: repair.state not in ['confirmed', 'assigned']):
				raise UserError(_("Repair must be confirmed before starting reparation."))
			if repair.repair_job_type in ('defective_device_replacement', 'removal'):
				repair.location_move_stock()
				if repair.repair_job_type == 'defective_device_replacement':
					repair.location_move_customer()
			if repair.repair_job_type == 'defective_component_replacement':
				repair.component_move_customer()
			repair.device_history()
			repair.mapped('operations').write({'state': 'confirmed'})
			repair.state = 'ready'

	def unlink(self):
		for line in self:
			if line.state in ('ready', 'invoiced', 'done'):
				raise ValidationError(_('You can not delete repair orders in ready or done or invoice states'))
		return super(RepairOrder, self).unlink()


class WebsiteSupport(models.Model):
	_inherit = 'website.support.ticket'
	_rec_name = "ticket_number"

	ticket_create_date = fields.Datetime(string="Reported on", default=fields.Datetime.now())
	user_id = fields.Many2one('res.users', string="Assigned User", default=lambda self: self.env.uid)
	job_card_type = fields.Selection([('sale', 'New Sale'),
									  ('support', 'Support/Repair'),
									  ('additional_service', 'Additional Service')
									  ], string="Support Type", default='support')
	repair_job_type = fields.Selection([('re_installation', 'Re-Installation Vehicle'),
		('defective_device_replacement', 'Defective Device Replacement'),
		('defective_component_replacement', 'Defective Component Replacement'),
		('calibartion_testing', 'Calibration and Testing'),
		('removal', 'Remove-Retain by Client'),
		('removal_returned', 'Remove-Return to FMS'),
		('deactive_device', 'Deactivation of Device'), 
		('reactive_device', 'Reactivation of Device'), 
		('non_technical', 'Non Technical')], string="Service Type")
	sup_repair_count = fields.Integer('Count', compute='compute_repair_count')

	# @api.model
	def compute_repair_count(self):
		for support in self:
			support.sup_repair_count = len(self.env['repair.order'].search([('support_id', '=', support.id)]))
			# support.sup_repair_count = len(support_ids.ids)

	def find_picking_id(self):
		if self.serial_no and self.partner_id:
			move_line_id = self.env['stock.move.line'].search([('lot_id', '=', self.serial_no.id), ('move_id.sale_line_id', '!=', False), ('move_id.picking_code', '=', 'outgoing'), ('state', '=', 'done')], order='date desc', limit=1)
			if not move_line_id:
				move_line_id = self.env['stock.move.line'].search([('picking_id.partner_id', '=', self.partner_id.id), ('lot_id', '=', self.serial_no.id), ('move_id.picking_code', '=', 'outgoing'), ('state', '=', 'done')], order='date desc', limit=1)
			if move_line_id:
				return move_line_id
		return False

	# @api.multi
	def open_repair_view(self):
		repaire_ids = self.env['repair.order'].search([('support_id', '=', self.id)])
		return {
			'name': _('Repair Order'),
			# 'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'repair.order',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', repaire_ids.ids)],
		}

	def _prepaire_repair(self, repair):
		move_line_id = self.find_picking_id()
		location_dest_id = self.env['stock.location']
		location_id = self.env['stock.location']
		if not move_line_id:
			quants = self.serial_no.quant_ids.filtered(lambda q: q.location_id.usage in ['internal', 'transit'] and q.location_id.loc_interanl_type in ['lease', 'rental'] and q.quantity >= 1)
			if quants:
				location_dest_id = quants.mapped('location_id').filtered(lambda x: x.partner_id == self.partner_id)
			if not location_dest_id:
				location_dest_id = self.env.ref('stock.stock_location_customers')
			if not location_dest_id:
				raise UserError(_('Customer location not found'))
			warehouse = self.env['stock.warehouse'].search([(('company_id', '=', self.env.user.company_id.id))], limit=1)
			location_id = warehouse.lot_stock_id if warehouse else False
			if not location_id:
				raise UserError(_('Stock location not found'))
		return {
			'support_id': repair and repair.id,
			'partner_invoice_id': self.partner_id and self.partner_id.id,
			'guarantee_limit': repair.vehicle_id and repair.vehicle_id.activation_date,
			'lot_id' : self.serial_no and self.serial_no.id or False,
			'product_id' : self.serial_no and self.serial_no.product_id.id or False,
			'partner_id' : self.partner_id and self.partner_id.id,
			'product_uom' : self.serial_no and self.serial_no.product_id.uom_id.id or False,
			'picking_id' : move_line_id.picking_id and move_line_id.picking_id.id if move_line_id else False,
			'location_dest_id' : move_line_id.location_dest_id and move_line_id.location_dest_id.id if move_line_id else location_dest_id and location_dest_id.id or False,
			'location_id' : move_line_id.location_id and move_line_id.location_id.id if move_line_id else location_id and location_id.id or False,
		}

	# @api.multi
	def create_repair(self):
		for rec in self:
			if not rec.serial_no:
				raise UserError(_('Device serial number not found'))
			repair_dict = rec._prepaire_repair(rec)
			repair_id = self.env['repair.order'].create(repair_dict)
			rec.states = 'under_repair'
			return {
				'type': 'ir.actions.act_window',
				'name': repair_id.name,
				'res_id': repair_id.id,
				'views': [[False, 'form']],
				'res_model': 'repair.order',
				'view_mode': 'tree,form',
			}

	# @api.multi
	def action_invoice_view(self):
		if self._context is None:
			context = {}
		# invoice_tree = self.env["ir.actions.act_window"].for_xml_id("account", 'action_invoice_tree1')
		invoice_tree = self.env.ref('account.action_move_out_invoice_type')
		invoice_tree['context'] = self._context
		invoices = self.env["account.move"].search([('support_id', '=', self.id)])
		invoice_tree['domain'] = [('id', 'in', invoices.ids)]
		return invoice_tree

	# @api.multi
	def compute_invoice_count(self):
		for rec in self:
			rec.invoice_count = len(self.env['account.move'].search([('support_id', '=', self.id)]))

	# @api.multi
	def action_invoice_create(self):
		# if self.repair_job_type != 'non_technical':
		# 	raise UserError('You can not create repair invoice for here')
		invoice = super(WebsiteSupport, self).action_invoice_create()
		if invoice:
			invoice.support_id = self.id
		return invoice


class StockMove(models.Model):
	_inherit = 'stock.move'

	def _find_lot_id(self, lot_name, product):
		lot_id = self.env['stock.lot'].search([('name', '=', lot_name), ('product_id', '=', product.id)])

		# raise an error if lot id can not be found
		if not lot_id:
			raise UserError("Sorry! Serial %s not found in %s. Please make sure serial exist." % (lot_name, product.name))

		quants = lot_id.quant_ids.filtered(lambda q: q.location_id.usage in ['internal', 'transit'] and q.location_id.loc_interanl_type not in ['rental', 'lease'])
		product_qty = sum(quants.mapped('quantity'))

		# only show error if the product type is stockable. We can allow consumable here
		if product_qty < 1 and product.type == 'product':
			raise UserError(_("Serial %s for %s not availabe " %(lot_name, product.name)))
		return lot_id.id

	# @api.multi
	def lot_update(self):
		move_line = self.env['stock.move.line']
		for move in self:
			self.env.cr.execute("""delete from stock_move_line where move_id =%s """%(move.id))
			location_dest_id = move.location_dest_id._get_putaway_strategy(move.product_id) or move.location_dest_id
			if not location_dest_id:
				return False
			if not move.lot_upload:
				return False
			lot_list = base64.b64decode(move.lot_upload).decode("utf-8", "ignore")
			reader = csv.DictReader(lot_list.split('\n'))
			for line in reader:
				vals = {
					'move_id': move.id,
					'product_id': move.product_id.id,
					'product_uom_id': move.product_uom.id,
					'location_id': move.location_id.id,
					'location_dest_id': location_dest_id and location_dest_id.id,
					'picking_id': move.picking_id.id,
					'lot_name': line.get('Lot') if move.picking_code == 'incoming' else False,
					'lot_id' : self._find_lot_id(line.get('Lot'), move.product_id) if move.picking_code in ('outgoing', 'internal') else False,
					'qty_done': 1,
				}
				move_line |= self.env['stock.move.line'].create(vals)
		if move_line:
			attachment_ids = self.env['ir.attachment'].sudo().create({
				'name': move.file_name,
				# 'datas_fname': move.file_name,
				'datas': move.lot_upload,
				'res_model': 'stock.picking',
				'res_id': move.picking_id and move.picking_id.id,
				'res_name': move.file_name,
				'public': True
			})
			self.env['mail.message'].sudo().create({
				'body': _('<p>Attached Files : </p>'),
				'model': 'stock.picking',
				'message_type': 'comment',
				'res_id': move.picking_id.id,
				'attachment_ids': [(6, 0, attachment_ids.ids)],
			})