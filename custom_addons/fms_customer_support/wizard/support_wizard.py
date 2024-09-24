# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class PartialSupport(models.TransientModel):
	_name = 'partial.support'
	_description = 'Partial Support'

	no_of_vehicles = fields.Integer()
	partner_id = fields.Many2one('res.partner', "Customer")
	support_lines = fields.One2many('partial.support.line', 'wizard_id')
	
	@api.model
	def default_get(self, vals):
		res = super(PartialSupport, self).default_get(vals)
		active_id = self.env.context.get('active_id')
		if active_id:
			support = self.env['fms.customer.support'].browse(active_id)
			if support:
				res.update({
						'partner_id': support.partner_id and support.partner_id.id,
						'no_of_vehicles': support.no_of_vehicles,
					})
		return res	

	def create_support_ticket(self):
		active_id = self.env.context.get('active_id') 
		if active_id:
			support = self.env['fms.customer.support'].browse(active_id)
			if support:
				if len(self.support_lines) > support.no_of_vehicles:
					raise UserError(_('You can not add more line than no of vehicles'))
				else:
					for line in self.support_lines:
						if not line.get_service_type():
							raise UserError(_('This combination are not exit : %s - %s') %(line.service_type, line.service_sub_type))
						vals = {
							'partner_id': support.partner_id.id,
							'subject': "%s : %s" %(support.name, support.subject),
							'ticket_create_date' : support.date,
							'user_id' : support.user_id and support.user_id.id,
							'person_name' : support.contact_name,
							'email': support.email,
							'phone_number': support.phone,
							'category': support.category and support.category.id,
							'sub_category_id': support.sub_category_id and support.sub_category_id.id,
							'repair_job_type': line.get_service_type(),
							'service_sub_type' : line.service_sub_type,
							'billing_method': support.billing_method,
							'customer_support_id': support.id,
							'description': support.description,
						}
						self.env['website.support.ticket'].create(vals)
				support.write({'state': 'ticket'})
		return True


class PartialSupportLine(models.TransientModel):
	_name = 'partial.support.line'

	def _get_service_type(self):
		if self.service_type == 'calibartion_testing' and self.service_sub_type == 'sub_calibration_test':
			return 'calibartion_testing'
		if self.service_type == 'defective_component_replacement' and self.service_sub_type == 'sub_comp_replace':
			return 'defective_component_replacement'
		if self.service_type == 'deactive_device' and self.service_sub_type == 'sub_deactive_device':
			return 'deactive_device'
		if self.service_type == 'reactive_device' and self.service_sub_type == 'sub_reactive_device':
			return 'reactive_device'
		if self.service_type == 'defective_device_replacement':
			if self.service_sub_type in ('same_remove_replace', 'diff_remove_replace', 'ref_remove_replace', 'replace_same_device'):
				return 'defective_device_replacement'
		if self.service_type == 'inactive_device':
			if self.service_sub_type in ('exist_reinstall', 'new_reinstall'):
				return 're_installation'
		if self.service_type == 'active_device':
			if self.service_sub_type == 'remove_reinstall':
				return 're_installation'
			if self.service_sub_type == 'remove_retain':
				return 'removal'
			if self.service_sub_type == 'remove_return':
				return 'removal_returned'
		return False

	wizard_id = fields.Many2one('partial.support')
	category = fields.Many2one('website.support.ticket.categories', string="Category", track_visibility='onchange')
	sub_category_id = fields.Many2one('website.support.ticket.subcategory', string="Sub Category")
	service_type = fields.Selection([
			('calibartion_testing', 'Inspection'), 
			('defective_component_replacement', 'Component Replacement'), 
			('defective_device_replacement', 'Defective Device Movement'), 
			('deactive_device', 'Deactivation'), 
			('reactive_device', 'Reactivation'),
			('active_device', 'Active Device Movement'), 
			('inactive_device', 'In active device Movement')
		])	
	service_sub_type = fields.Selection([
			('sub_calibration_test', 'Calibration and Testing'),
			('sub_comp_replace', 'Component Replacement'),
			('sub_deactive_device', 'Deactivation of Device'),
			('sub_reactive_device', 'Reactivation of Device'),
			('same_remove_replace', 'Remove/Replace Alternate Device - Same type'),
			('diff_remove_replace','Remove/Replace Alternate Device - Differet type'),
			('ref_remove_replace','Remove/Replace Same Device Refurbished'),
			('replace_same_device','Replace with Same Device - Rectified'),
			('remove_reinstall', 'Remove/Reinstall Another Vehicle'),
			('remove_retain', 'Remove/Retain by Client'), 
			('remove_return', 'Remove/Return to Company'),
			('exist_reinstall', 'Re install-Existing Fleet Vehicle'),
			('new_reinstall', 'Re install-New Vehicle (create)')
		])
