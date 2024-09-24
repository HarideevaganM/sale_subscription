# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
import re
from odoo.exceptions import UserError,ValidationError
from collections import Counter
import string
from itertools import groupby
from operator import itemgetter


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('move_id.invoice_line_ids')
    def _get_sequence_ref(self):
        for inv in self:
            no = 0
            inv.sequence_ref = no
            for line in inv.move_id.invoice_line_ids.sorted(key=lambda r: r.sequence):
                no += 1
                line.sequence_ref = no

    sequence_ref = fields.Integer('No', compute="_get_sequence_ref")


class AccountMove(models.Model):
    _inherit = "account.move"

    def total_amount_in_word(self, total_amount):
        amount_in_words = self.currency_id.with_context(lang=self.partner_id.lang or 'es_ES').amount_to_text(total_amount).title()
        amount_in_words = "{} {} {}".format('Rial Omani', amount_in_words.split('Baise')[0], 'only')
        return amount_in_words


class InvoiceReport(models.AbstractModel):
    _name = 'report.fms_invoice_report.invoicereport'

    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['account.move'].browse(ids)
        for report in report_obj:
            if report.move_type == 'in_invoice':
                return {
                    'doc_ids': ids,
                    'doc_model': 'account.move',
                    'docs': report_obj,
                    'data': data,
                }
            else:
                raise ValidationError("This is not purchase invoice")


class TaxInvoiceReport(models.AbstractModel):
    _name = 'report.fms_invoice_report.report_gfms_tax_invoice_extended'

    def _get_excluding_vat(self, line):
        amount_excluding_vat = 0.0
        amount_excluding_vat = (line.quantity * line.price_unit) - line.discount
        return amount_excluding_vat

    def _get_output_vat(self, line):
        after_discount = 0.0
        output_vat = 0.0
        after_discount = (line.quantity * line.price_unit) - line.discount
        amount = sum(line.tax_ids.mapped('amount'))
        output_vat = (after_discount * amount) / 100  
        return output_vat

    def _get_total(self, line):
        after_discount = 0.0
        output_vat = self.get_output_vat(line)
        after_discount = (line.quantity * line.price_unit) - line.discount
        return after_discount + output_vat

    def _prepare_line(self, invoice_ids):
        lines = []
        for inv_line in invoice_ids.mapped('invoice_line_ids'):
            lines.append({
                    'sequence_ref': inv_line.sequence_ref,
                    'default_code': inv_line.product_id.default_code,
                    'name': inv_line.name,
                    'quantity': inv_line.quantity,
                    'price_unit': inv_line.price_unit,
                    'discount': inv_line.discount,
                    'tax_name': ','.join(inv_line.tax_ids.filtered(lambda x: x.description).mapped('description')) or '',
                    'amount_excluding_vat': self.get_excluding_vat(inv_line),
                    'output_vat': self.get_output_vat(inv_line),
                    'total': self.get_total(inv_line),
                })
        return lines

    # @api.model
    def _get_report_values(self, docids, data):
        invoice_ids = self.env['account.move'].browse(docids)
        company_id = self.env.user.company_id
        lines = self._prepare_line(invoice_ids)
        docargs = {
            'docs': invoice_ids,
            'tax_invoice_lines': self._prepare_line(invoice_ids),
            'company_id': company_id,
        }
        return docargs
