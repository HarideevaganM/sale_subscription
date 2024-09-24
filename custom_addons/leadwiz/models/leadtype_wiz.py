# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'
 
    lead_type = fields.Selection([
        ('tele marketing', 'TELE MARKETING'),
        ('define events', 'DEFINE EVENTS'),
        ('plan/schdule campaifgns', 'PLAN/SCHEDULE CAMPAIGNS'),
        ('web based enquires', 'WEB BASED ENQUIRIES'),
        ('inbound calls', 'INBOUND CALLS')
    ], string='Lead Type', required=True, store=True)

