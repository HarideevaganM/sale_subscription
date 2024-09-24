# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class BbisAccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    # @api.depends('balance')
    # def _balance_reverse(self):
    #     for r in self:
    #         if r.balance > 0:
    #             r.balance_reverse = r.balance * -1
    #         else:
    #             r.balance_reverse = abs(r.balance)
    #
    # @api.depends('balance')
    # def _account_move_tax(self):
    #     for r in self:
    #         tax_amount = sum(r.tax_ids.mapped('amount')) / 100
    #
    #         price_vat = r.credit * tax_amount
    #         r.amount_tax = price_vat

    product_category = fields.Many2one(related='product_id.categ_id', store=True, string='Product Category', readonly=True)
    group_id = fields.Many2one(related='account_id.group_id', store=True, string='Account Group', readonly=True)
    # balance_reverse = fields.Float(compute='_balance_reverse', string='_Balance', help="Only use for Reports, reversing balance", readonly=True, store=True)
    # amount_tax = fields.Monetary(compute='_account_move_tax', store=True, string='Tax', readonly=True)
