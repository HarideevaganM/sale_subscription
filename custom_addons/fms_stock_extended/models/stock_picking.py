# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
	_inherit = 'stock.picking'

	courier = fields.Char(string="Courier")
	code = fields.Char(string="Code")
	awb_no = fields.Char(string="AWB No")

class ProductionLot(models.Model):
	_inherit = "stock.lot"

	start_date = fields.Date(string='Warranty Start Date')
	end_date = fields.Date(string="Warranty End Date")
	iemi_number = fields.Char('IEMI Number')
	firmware_no = fields.Char('Firmware No')

class StockMoveLine(models.Model):
	_inherit = "stock.move.line"

	start_date = fields.Date(string='Warranty Start Date')
	end_date = fields.Date(string="Warranty End Date")
	iemi_number = fields.Char('IEMI Number')
	firmware_no = fields.Char('Firmware No')
	production_ref = fields.Char('Production')
