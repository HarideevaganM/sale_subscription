# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError,Warning,ValidationError,AccessError


class AccountMove(models.Model):
	_inherit = "account.move"
	
	source_invoice = fields.Char("Main Invoice")
	consolidated_number = fields.Char("Consolidated Invoice No")
	consolidate_invoice_created = fields.Boolean("Source Invoice")
	consolidate_invoice = fields.Boolean("Consolidated Invoice")
	cons_validate_button_visible = fields.Boolean("Consolidated Button visible")
	consolidate_state_visible = fields.Boolean("Consolidated state visible")
	consolidate_state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated')], string="State", default='draft')
	subscription_start_date = fields.Date("Subscription Start Date")
	subscription_end_date = fields.Date("Subscription End Date")
	merge_id = fields.Many2one('account.move')
	invoice_consol_ids = fields.One2many('account.move', 'merge_id', string='Source Invoices')
	
	def consolidate_validate(self):
		self.consolidate_state = 'validated'
		self.cons_validate_button_visible = False
	
	# @api.multi
	def unlink(self):
		for inv in self:
			if inv.invoice_consol_ids:
				inv.invoice_consol_ids.write({'consolidate_invoice_created': False})
				inv.consolidate_invoice = False
		return super(AccountMove, self).unlink()

