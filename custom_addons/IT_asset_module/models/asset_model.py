from odoo import models, fields, api, _, exceptions
import collections


class AssetModel(models.Model):
    _name = 'asset.model'

    name = fields.Char(string="Name")
    asset_category = fields.Many2one('account.asset.category', string="Asset Category")
    reordering_rule = fields.Integer(string="Number of Assets")