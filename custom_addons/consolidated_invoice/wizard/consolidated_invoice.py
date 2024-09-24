# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError,Warning,ValidationError,AccessError


class ConsolidatedInvoice(models.TransientModel):
	_name = 'consolidated.invoice'
	_description = 'Consolidated Invoice'

	res_partner_id = fields.Many2one('res.partner', "Customer")
	consolidated_invoice_lines = fields.Many2many('consolidated.invoice.line', 'consolidated_invoice_rel', 'cons_id', 'line_id', "Line")
	
	@api.model
	def default_get(self, vals):
		conso_lines = []
		res = super(ConsolidatedInvoice, self).default_get(vals)
		active_ids = self._context.get('active_ids')
		if active_ids:
			selected_invoices = self.env['account.move'].browse(active_ids)
			if len(selected_invoices) <= 1:
				raise UserError(_("Please select multiple invoices"))
			partner_ids = selected_invoices.mapped('partner_id')
			journal_ids = selected_invoices.mapped('journal_id')
			currency_ids = selected_invoices.mapped('currency_id')
			if len(partner_ids) > 1:
				raise UserError(_("Please select same customer invoices."))
			if len(journal_ids) > 1:
				raise UserError(_("Please select same journal invoices."))
			if len(currency_ids) > 1:
				raise UserError(_("Please select same currency invoices."))
			for invoice in selected_invoices:  
				if invoice.state != 'draft':
					raise UserError(_("Please select only draft invoices."))
				for line in invoice.invoice_line_ids:
					cons_inv_line = self.env['consolidated.invoice.line'].create({
						'product_id': line.product_id.id,
						'name': line.product_id.name,
						'price_unit': line.price_unit,
						'quantity': line.quantity,
						# 'origin': line.origin,
						'discount': line.discount,
						'price_subtotal': line.price_subtotal,
						'invoice_line_id': line.id,
						'invoice_line_tax_ids': [(6,0, line.tax_ids.ids)]
					})
					conso_lines.append(cons_inv_line.id)
				res['res_partner_id'] = invoice.partner_id.id
		res['consolidated_invoice_lines'] = [[6, 0, conso_lines]]
		return res	
	
	def create_invoice(self):
		active_ids = self._context.get('active_ids') 
		product_ids = []
		price_list = []
		quantity = 0.0    
		account_invoice_obj = self.env['account.move']
		account_invoice_line_obj = self.env['account.move.line']
		selected_invoices = self.env['account.move'].browse(active_ids)
		purchase_order_fil = selected_invoices.filtered(lambda x: x.purchase_order_date)
		if not selected_invoices:
			return False
		origin = ', '.join(selected_invoices.filtered(lambda x: x.invoice_origin).mapped('invoice_origin')) or ''
		name = ','.join(selected_invoices.filtered(lambda x: x.name).mapped('name')) or ''
		client_ref = ','.join(selected_invoices.filtered(lambda x: x.client_ref).mapped('client_ref')) or ''
		purchase_no = ','.join(selected_invoices.filtered(lambda x: x.purchase_order_no).mapped('purchase_order_no')) or ''
		vals = {
			'partner_id': selected_invoices[0].partner_id.id,
			'invoice_origin': origin,
			# 'name': '/',
			'purchase_order_no': purchase_no,
			'purchase_order_date': purchase_order_fil and purchase_order_fil[0].purchase_order_date,
			'client_ref': client_ref,
			'move_type': 'out_invoice',
			'currency_id': selected_invoices[0].currency_id.id,
			'journal_id': selected_invoices[0].journal_id.id,
			'sale_type': selected_invoices[0].sale_type,
		}
		invoice = self.env['account.move'].with_context(check_move_validity=False).create(vals)
		invoice._onchange_partner_id()
		# invoice._onchange_payment_term_date_invoice()
		# merge prod qty with same price
		# Changes made by BBIS - For getting the account id that selected in the invoice line table itself.
		for line in self.consolidated_invoice_lines:
			if line.invoice_line_id.account_id:
				account_id = line.invoice_line_id.account_id.id
			else:
				account_id = line.product_id.categ_id and line.product_id.categ_id.property_account_income_categ_id and line.product_id.categ_id.property_account_income_categ_id.id
			inv_line_vals = {
				'product_id': line.product_id.id,
				'name': line.name,
				'price_unit': line.price_unit,
				# 'origin': origin,
				'account_id': account_id,
				'quantity': line.quantity,
				'discount': line.discount,
				'move_id': invoice.id,
				'tax_ids': [(6,0, line.invoice_line_tax_ids.ids)],

			}
			inv_line_id = account_invoice_line_obj.with_context(check_move_validity=False).create(inv_line_vals)
			lines = []
			sale_line_id = self.env['sale.order.line'].search([('invoice_lines', '=', line.invoice_line_id.id)])
			lines.append(inv_line_id.id)
			sale_line_id.update({'invoice_lines': [[6, 0, lines]]})
		# vechiles info
		for vehicle in selected_invoices.mapped('vehicle_detail_ids'):
			new_vehicle = vehicle.sudo().copy()
			new_vehicle.invoice_id = invoice.id
		# tree view
		invoice.write({'consolidate_invoice': True, 'invoice_consol_ids': [(4, inv) for inv in selected_invoices.ids]})
		selected_invoices.write({'state': 'cancel', 'consolidate_invoice_created': True})
		# invoice.compute_taxes()
		invoice._recompute_dynamic_lines()
		# action = self.env.ref('account.action_move_out_invoice_type').read()[0]
		# action['domain'] = [('id', 'in', [invoice.id])]
		return {
			'name': _('Invoices'),
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
			'view_mode': 'tree,form',
			'domain': [('id', 'in', [invoice.id])],
			'context': {
				'create': False,
				'delete': False,
			}
		}


class ConsolidatedInvoiceLine(models.TransientModel):
	_name = 'consolidated.invoice.line'
	
	product_id = fields.Many2one('product.product', "Product")
	cons_id = fields.Many2one('consolidated.invoice', "Consolidated Invoice")
	invoice_line_id = fields.Many2one('account.move.line', "Invoice Line")
	name = fields.Char("Description")
	price_unit = fields.Float("Unit Price")
	price_subtotal = fields.Float("Subtotal")
	quantity = fields.Integer("Quantity")
	origin = fields.Char("Origin")
	discount = fields.Float("Discount")
	invoice_line_tax_ids = fields.Many2many('account.tax')

