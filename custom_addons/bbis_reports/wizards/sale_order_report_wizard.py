# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError


class BbisSaleOrderReportWizard(models.TransientModel):
    _name = 'bbis.sale.order.report.wizard'
    _description = 'BBIS Sales Order Report'

    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    sales_person = fields.Many2many('res.users', required=False, default=lambda self: [self.env.user.id])

    def print_xlsx_report(self):
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'sales_person': self.sales_person.ids,
        }

        start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d')

        num_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

        if start_date.year != end_date.year:
            if start_date.month == end_date.month or num_months >= 12:
                raise ValidationError("Sorry, please select dates with in 12 months range.")

        if start_date.year > end_date.year:
            raise ValidationError("Sorry, please select start date not greater then end date.")

        return self.env.ref('bbis_reports.bbis_sales_report_xlsx').report_action(self, data=data)
