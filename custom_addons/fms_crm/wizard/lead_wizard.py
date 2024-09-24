# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CrmLeadInherit(models.Model):
    _inherit='crm.lead'
    
    # Selection field name changed Define Events as EVENTS and plan/schedule campaign as CAMPAIGN #
    lead_type=fields.Selection([
    ('tele marketing','TELE MARKETING'),
    ('define events','EVENTS'),
    ('plan/schdule campaifgns','CAMPAIGN'),
    ('web based enquires','WEB BASED ENQUIRIES'),
    ('inbound calls','INBOUND CALLS')
    ],string='Lead Source',required=True ,store=True)
    
