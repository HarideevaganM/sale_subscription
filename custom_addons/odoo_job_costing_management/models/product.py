# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    boq_type = fields.Selection([
        ('eqp_machine', 'Machinery / Equipment'),
        ('worker_resource', 'Worker / Resource'),
        ('work_cost_package', 'Work Cost Package'),
        ('subcontract', 'Subcontract')], 
        string='BOQ Type')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, vals):
        record = super(ProductTemplate, self).create(vals)
        record['name_seq'] = self.env['ir.sequence'].next_by_code('product.template.code') or _('New')
        return record
    #
    # def create(self, vals):
    #     if 'name_seq' not in vals or vals['name'] == _('New'):
    #         vals['name_seq'] = self.env['ir.sequence'].next_by_code('product.template') or _('New')
    #     return super(ProductTemplate, self).create(vals)

    name_seq = fields.Char(string='Product Reference')

    # def create(self):
    #     if 'name_seq' not in vals or vals['name'] == _('New'):
    #         vals['name_seq'] = self.env['ir.sequence'].next_by_code('product.template.code') or _('New')
    #     return super(ProductTemplate, self).create(vals)
    #
    # name_seq = fields.Char(string="Order Reference", copy=False, default=lambda self: _('New'), required=True)

