# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import csv

class JobCardCSV(models.AbstractModel):
    _name = 'report.lot_import_csv.lot_serial_template_csv'
    _inherit = 'report.report_csv.abstract'

    def generate_csv_report(self, writer, data, partners):
        filter_job_ids = self.env['job.card'].browse(data.get('job_ids'))
        writer.writeheader()
        for rec in filter_job_ids:
            writer.writerow({
                'job_card': str(rec.name),
                'date': str(rec.create_date),
                'device_serial': str(rec.device_serial_number_new_id.name),
                'device': str(rec.device_id.name),
                'customer': str(rec.company_id.name),
                'order': str(rec.sale_order_id.name),
            })

    def csv_report_options(self):
        res = super().csv_report_options()
        res['fieldnames'].append('job_card')
        res['fieldnames'].append('date')
        res['fieldnames'].append('device_serial')
        res['fieldnames'].append('device')
        res['fieldnames'].append('customer')
        res['fieldnames'].append('order')
        res['delimiter'] = ','
        res['quoting'] = csv.QUOTE_ALL
        return res
