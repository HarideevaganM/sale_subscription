# -*- coding: utf-8 -*-

from odoo import models, fields, api
from lxml import etree
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_open_subscriptions(self):
        res = super(SaleOrder, self).action_open_subscriptions()
        res['context'] = {'create': False}
        return res

    # @api.multi
    def action_view_invoice(self):
        res = super(SaleOrder, self).action_view_invoice()
        res['context'] = {'create': False}
        return res


class SaleSubscription(models.Model):
    _inherit = 'sale.order'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(SaleSubscription, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field"):
                is_manager = self.env.user.has_group('sale_subscription.group_sale_subscription_manager')
                modifiers = json.loads(node.get("modifiers"))
                modifiers['readonly'] = False if is_manager else True
                node.set("modifiers", json.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res