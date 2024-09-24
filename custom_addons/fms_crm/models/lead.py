# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import ValidationError, UserError

class CrmLeadInherit(models.Model):
    _inherit='crm.lead'

    state_type=fields.Selection([
    ('draft','Draft'),
    ('in_progress','In Progress'),
    ('qualified','Qualified'),
    ('won','Won'),
    ('dropped','Dropped')
    ], string='State', default="draft")
    sale_number=fields.Integer("Quote",compute="compute_sale")
    pilot_lead=fields.Selection([
        ('pilot','Pilot'),
        ('non_pilot','Non Pilot')
    ],string='Project Type',default='non_pilot')

    customer_types=fields.Selection([
    ('opal customer','OPAL Customer'),
    ('non opal customer',' NON OPAL Customer')
    ], string='Customer Type' ,compute="compute_customer_type",required=True)

    return_date=fields.Datetime(string='Return Date')

    pilot_status_inlead = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed')

    ], string='Pilot Order Status')
    planned_revenue = fields.Float('Expected Revenue',digits=(16,3),track_visibility='always')

    #@api.multi
    def compute_sale(self):
        var=self.env['sale.order'].search([('opportunity_id','=',self.id)])
        if var:
            self.sale_number=len(var)

# for creating lead set default draft stage
    #@api.multi
    def close_dialog(self):
        self.stage_id=1
        return True

# for creating lead set default draft stage

    #@api.multi
    def edit_dialog(self):
        self.stage_id=1
        return True
# for intial level approval from manager
    #@api.multi
    def initial_approval(self):
        self.write({'state_type':'in_progress'})
        self.stage_id =2
        return True
#for authorization from manager for approve
    #@api.multi
    def manager_approval_lead(self):
        self.write({'state_type':'qualified'})
        self.stage_id =3
        return True

      
#for authorization from manager fro reject

    #@api.multi
    def manager_reject_lead(self):
        self.write({'state_type':'dropped'})
        self.stage_id =5
        return True

    # for new quotation creation
    #@api.multi
    def new_quotation(self):
        vals = {

            'partner_id': self.partner_id.id,
            'opportunity_id': self.id,
            'sale_type':'cash',
        }

        self.env['sale.order'].create(vals)


    # for pilot order quotation creation
    #@api.multi
    def pilot_quotation(self):
        if self.pilot_lead=='pilot':
            pilot_sequence = self.env['ir.sequence'].next_by_code('sale.order.pl') or _('New')

            vals={
                'name': pilot_sequence,
                'partner_id': self.partner_id.id,
                'opportunity_id': self.id,
                'sale_type': 'pilot',
                'is_subscription': True
                }

            sale = self.env['sale.order'].create(vals)


# for onchange from res.partner to crm.lead
    @api.onchange('partner_id')
    def compute_customer_type(self):
        if self.partner_id:
            self.customer_types=self.partner_id.customer_types

#for onchange from res.useres while changing team_id
    @api.onchange('team_id')
    def onchange_user_id(self):
            crm=self.env['crm.team'].search([('id','=',self.team_id.id)])
            if crm:
                if self.team_id:
                    for val in crm:
                        if val:
                            res = {'domain': {'user_id': [('id', 'in', val.member_ids.ids)]}}
                            return res
# sale.order class
class SaleOrderInherit(models.Model):
    _inherit='sale.order'
   
    no_of_days = fields.Datetime(string="Remaining Days" )


    is_pilot=fields.Boolean("Is Pilot")

    pilot_status=fields.Selection([
        ('success','Success'),
        ('failed','Failed')

    ] ,string='Pilot Order Status')

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('reject','Pilot Reject')
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
# for sale order creation from draft to to sale state
#for on change on pilot status from sale.order to crm.lead while pilot status changing
    @api.onchange('pilot_status')
    def onchge_pilot_status_inlead(self):
        status = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)])
        if status:
            status.write({'pilot_status_inlead':self.pilot_status})
    #STAGES AND STATES CHANGES CORRESPONDINGLY IN CRM
    #@api.multi
    def action_confirm(self):
        res=super(SaleOrderInherit,self).action_confirm()
        # if self.sale_type == 'pilot':
        val=self.env['crm.lead'].search([('id','=',self.opportunity_id.id)])
        if val:
            if self.sale_type!='pilot':
                if val.state_type =='qualified':
                    val.write({'state_type': 'won'})
                    val.stage_id = 4

            elif self.sale_type=='pilot':
                if self.pilot_status=='success':
                    if val.state_type == 'qualified':
                        val.write({'state_type': 'won'})
                        val.stage_id = 4
        return res

    
    #@api.multi
    def action_reject(self):
            self.env.cr.execute("""select count(so.id) count from sale_order so
                                   join stock_picking sp on(so.id=sp.sale_id) where sp.state='done' and so.id=%d"""%self.id)
            reject=self.env.cr.dictfetchall()
            for rej in reject:
                if rej['count']==2:
                    self.write({'state': 'reject'})
                    val = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)])
                    if val:
                        val.write({'state_type': 'dropped'})
                        val.write({'stage_id': 5})

                else:
                    raise UserError(_("You Should Create GRN And Make It Done State"))



#customer type in customer master
class PartnerIdInherit(models.Model):
    _inherit='res.partner'
    #customer type captureing
    customer_types=fields.Selection([
    ('opal customer','OPAL Customer'),
    ('non opal customer',' NON OPAL Customer')
    ], string='Customer Type')
# find sales and marketing teams difference
class UserIdInherit(models.Model):
    _inherit = 'crm.team'
    is_sale=fields.Boolean(string='Is Sale' ,store=True)



#stock.picking inherit class
class Stock_Picking_Inherit_new(models.Model):
    _inherit = 'stock.picking'

    sale_order_id=fields.Many2one('sale.order',string='Sale Id')

    # onchage on operation types from destination id
    @api.onchange('location_dest_id')
    def onchange_stok_picking_inherit(self):
        if self.location_dest_id.id == 20:
            self.picking_type_id=8


#product_template
class Product_Template_Inherit_New(models.Model):
    _inherit = 'product.template'

    monthly_rate=fields.Float(string='Monthly Rate')



    

    
   
    
   
    
    
    
  
