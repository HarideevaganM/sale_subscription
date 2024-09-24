# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class StockSummaryReport(models.TransientModel):
    _name = "wizard.stock.summary"
    _description = "Stock Summary"

    start_date = fields.Date('From', required=True)
    end_date = fields.Date('To', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', domain="[('company_id','=',company_id)]")
    location_id = fields.Many2one('stock.location', string='Locations',
                                  domain="[('usage','=','internal'),('company_id','=',company_id)]")
    parent_location = fields.Many2one('stock.location', string='Main Location', domain="[('child_ids','>',0)]")
    all_locations = fields.Boolean(string='All Locations')
    show_cost = fields.Boolean(string='Show Cost')

    def print_stock_report(self):
        if not self.all_locations:
            if not self.location_id and not self.parent_location:
                raise ValidationError(_('Please select Locations or Main Location for Summary Report'))

        context = self._context
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.stock.summary'
        datas['form'] = self.read()[0]
        datas['location'] = self.location_id.display_name
        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]
        return self.env.ref('stock_summary_report.stock_summary_xlsx').report_action(self, data=datas)

    @api.onchange('parent_location', 'location_id')
    def onchange_main_location(self):
        if self.parent_location:
            self.location_id = ''


      
