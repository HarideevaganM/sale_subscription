# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
# from odoo.tools.amount_to_text_en import amount_to_text
from datetime import datetime
# from  amt_to_txt import Number2Words
import re
from odoo.exceptions import UserError
from collections import Counter
import string
from itertools import groupby
from operator import itemgetter


class QuotationOrderReport(models.AbstractModel):
    _name = 'report.fms_quotation_report.quotation_report'

    def _get_user(self, data):
        user = self.env['res.users'].search([('login', '=', 'fms_admin')])
        return user

    # @api.multi
    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj = self.env['sale.order'].search([('id', 'in', docids)])
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': report_obj,
            'data': data,
            'get_user': self.get_user,
        }


class QuotationOrderReportInclusive(models.AbstractModel):
    _name = 'report.fms_quotation_report.quotation_report_inclusive'

    def _get_user(self, data):
        user = self.env['res.users'].search([('login', '=', 'fms_admin')])
        return user

    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['sale.order'].browse(ids)
        return {
            'doc_ids': ids,
            'doc_model': 'sale.order',
            'docs': report_obj,
            'data': data,
            'get_user': self.get_user,
        }
