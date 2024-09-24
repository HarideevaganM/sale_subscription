# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api


class AccountMoveReport(models.Model):
    _name = "account.move.report"
    _description = "Journal Entries Report"
    _auto = False
    _rec_name = 'date'
    _order = "date desc"

    date = fields.Date(readonly=True)
    account_id = fields.Many2one('account.account', string='Account Name', readonly=True)
    account_type_id = fields.Many2one('account.account.type', string='Account Type', readonly=True)
    account_group_id = fields.Many2one('account.group', string='Account Group', readonly=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    credit = fields.Float(readonly=True)
    debit = fields.Float(readonly=True)
    balance = fields.Float(readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    prod_category_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    tax = fields.Float(string='Tax', readonly=True)

    # @api.model
    # def init(self):
    #     tools.drop_view_if_exists(self.env.cr, 'account_move_report')
    #     self.env.cr.execute("""
    #         CREATE OR REPLACE VIEW account_move_report AS (
    #             SELECT
    #                 row_number() OVER () AS id,
    #                 line.account_type_id,
    #                 line.account_group_id,
    #                 line.account_id,
    #                 line.move_id,
    #                 line.journal_id,
    #                 line.credit,
    #                 line.debit,
    #                 line.balance,
    #                 line.partner_id,
    #                 line.product_id,
    #                 line.prod_category_id,
    #                 line.quantity,
    #                 line.invoice_id,
    #                 line.date,
    #                 line.tax
    #             FROM (
    #                 SELECT
    #                     aml.user_type_id as account_type_id,
    #                     ag.id as account_group_id,
    #                     ac.id as account_id,
    #                     am.id as move_id,
    #                     aml.journal_id as journal_id,
    #                     (CASE
    #                         WHEN aml.balance > 0
    #                             THEN aml.balance * -1
    #                             ELSE ABS(aml.balance)
    #                         END
    #                     ) as balance,
    #                     aml.credit as credit,
    #                     aml.debit as debit,
    #                     aml.partner_id as partner_id,
    #                     aml.product_id as product_id,
    #                     aml.product_category as prod_category_id,
    #                     (CASE
    #                         WHEN ai.type in ('out_refund','in_refund')
    #                             THEN aml.quantity * -1
    #                             ELSE ABS(aml.quantity)
    #                         END
    #                     ) as quantity,
    #                     aml.invoice_id as invoice_id,
    #                     aml.date as date,
    #                     (CASE_compute_discount_amount
    #                         WHEN aml.credit > 0
    #                             THEN (aml_tax.total_tax / 100) * aml.credit
    #                             ELSE (aml_tax.total_tax / 100) * aml.debit * -1
    #                         END
    #                     ) as tax
    #                     FROM account_move_line aml
    #                     LEFT JOIN account_group ag ON ag.id = aml.group_id
    #                     LEFT JOIN account_account ac on ac.id = aml.account_id
    #                     LEFT JOIN account_move am on aml.move_id = am.id
    #                     LEFT JOIN account_invoice ai on aml.invoice_id = ai.id
    #                     LEFT JOIN (
    #                         SELECT
    #                         SUM(act.amount) as total_tax,
    #                         amlt_rel.account_move_line_id as aml_id
    #                         FROM account_tax act
    #                         LEFT JOIN account_move_line_account_tax_rel amlt_rel on amlt_rel.account_tax_id = act.id
    #                         GROUP BY amlt_rel.account_move_line_id
    #                     ) as aml_tax ON aml_tax.aml_id = aml.id
    #             ) as line
    #         )""")
