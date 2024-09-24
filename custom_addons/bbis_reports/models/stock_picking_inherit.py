# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class BbisStockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    shipment_date = fields.Date()
    remarks_pb = fields.Boolean(string='Remarks Page Break')
    delivery_signatures_pb = fields.Boolean(string='Delivery Signatures Page Break')
