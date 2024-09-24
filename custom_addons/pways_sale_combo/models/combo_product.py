# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class ProductCombo(models.Model):
	_name = 'product.combo'
	_description = 'Product Bundle'

	@api.onchange('product_id')
	def _onchange_product_id(self):
		if self.product_id:
			self.combo_price = self.product_id.lst_price

	product_tmplte_id = fields.Many2one('product.template')
	product_id = fields.Many2one('product.product', string="Product")
	product_uom_qty = fields.Float(string="Qty", default=1.0)
	combo_price = fields.Float(string="Price")

class ProductTemplate(models.Model):
	_inherit = "product.template"

	is_combo = fields.Boolean("Can be Bundle")
	product_combo_ids = fields.One2many('product.combo', 'product_tmplte_id')

class SaleOrder(models.Model):
	_inherit = "sale.order"

	#@api.multi
	def _action_confirm(self):
		super(SaleOrder, self)._action_confirm()
		for order in self:
			for line in order.order_line.filtered(lambda x: x.product_id.product_combo_ids):
				line._action_launch_combo_rule()

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	#@api.multi
	def invoice_line_create(self, invoice_id, qty):
		invoice_lines = self.env['account.move.line']
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		for line in self:
			is_combo_ids = line.product_id.product_combo_ids
			if not float_is_zero(qty, precision_digits=precision):
				if is_combo_ids:
					for combo in is_combo_ids:
						vals = line._prepare_invoice_combo_line(combo,qty=qty)
						vals.update({'invoice_id': invoice_id, 'sale_line_ids': [(6, 0, [line.id])]})
						invoice_lines |= self.env['account.move.line'].create(vals)
				else:
					vals = line._prepare_invoice_line(qty=qty)
					vals.update({'invoice_id': invoice_id, 'sale_line_ids': [(6, 0, [line.id])]})
					invoice_lines |= self.env['account.move.line'].create(vals)
		return invoice_lines

	#@api.multi
	def _prepare_invoice_combo_line(self, combo, qty):
		self.ensure_one()
		res = {}
		product = self.product_id.with_context(force_company=self.company_id.id)
		account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
		if not account:
			raise UserError(_('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
				(self.product_id.name, self.product_id.id, self.product_id.categ_id.name))
		fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
		if fpos:
			account = fpos.map_account(account)
		res = {
				'name': self.name,
				'sequence': self.sequence,
				'origin': self.order_id.name,
				'account_id': account.id,
				'discount': self.discount,
				'price_unit': combo.combo_price,
				'quantity': combo.product_uom_qty,
				'uom_id': combo.product_id.uom_id and combo.product_id.uom_id.id,
				'product_id': combo.product_id.id or False,
				'layout_category_id': self.layout_category_id and self.layout_category_id.id or False,
				'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
				'account_analytic_id': self.order_id.analytic_account_id.id,
				'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
		}
		return res

	def _get_combo_qty_procurement(self):
		self.ensure_one()
		for line in self:
			for com_line in line.product_id.product_combo_ids:
				qty = 0.0
				for move in line.move_ids.filtered(lambda r: r.product_id == com_line.product_id and r.state != 'cancel'):
					if move.picking_code == 'outgoing':
						qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
					elif move.picking_code == 'incoming':
						qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
		return qty

	#@api.multi
	def _prepare_combo_procurement_values(self, group_id=False):
		values = {}
		self.ensure_one()
		date_planned = datetime.strptime(self.order_id.confirmation_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(days=self.customer_lead or 0.0) - timedelta(days=self.order_id.company_id.security_lead)
		values.update({
			'company_id': self.order_id.company_id,
			'group_id': group_id,
			'sale_line_id': self.id,
			'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
			'route_ids': self.route_id,
			'warehouse_id': self.order_id.warehouse_id or False,
			'partner_dest_id': self.order_id.partner_shipping_id
		})
		return values

	#@api.multi
	def _action_launch_combo_rule(self):
		errors = []
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		# precision
		for sale_line in self.filtered(lambda x: x.product_id.is_combo and x.product_id.product_combo_ids):
			group_id = sale_line.order_id.procurement_group_id
			if not group_id:
				group_id = self.env['procurement.group'].create({
					'name': sale_line.order_id.name, 
					'move_type': sale_line.order_id.picking_policy,
					'sale_id': sale_line.order_id.id,
					'partner_id': sale_line.order_id.partner_shipping_id.id,
				})
				sale_line.order_id.procurement_group_id = group_id
			# combo picking
			for line in sale_line.product_id.mapped('product_combo_ids'):
				# check qty
				qty = sale_line._get_combo_qty_procurement()
				if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
					continue
				# group data
				values = sale_line._prepare_combo_procurement_values(group_id=group_id)
				product_qty = line.product_uom_qty - qty
				procurement_uom = sale_line.product_uom
				quant_uom = line.product_id.uom_id
				get_param = self.env['ir.config_parameter'].sudo().get_param
				if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
					product_qty = sale_line.product_uom._compute_quantity(product_qty, quant_uom, rounding_method='HALF-UP')
					procurement_uom = quant_uom
				try:
					self.env['procurement.group'].run(line.product_id, product_qty, procurement_uom, sale_line.order_id.partner_shipping_id.property_stock_customer, sale_line.name, sale_line.order_id.name, values)
				except UserError as error:
					errors.append(error.name)
				if errors:
					raise UserError('\n'.join(errors))
		return True
