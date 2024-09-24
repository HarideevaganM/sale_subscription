from odoo import api, fields, models, _
from datetime import datetime
import re
from odoo.exceptions import UserError
from collections import Counter
import string
from itertools import groupby
from operator import itemgetter
from num2words import num2words


class ResCurrencyInherit(models.Model):
    _inherit = "res.currency"

    report_currency_name = fields.Char("Report Currency Name")


class PurchaseOrderReport(models.AbstractModel):
    _name = 'report.fms_purchase_order_report.purchasereport'

    def _get_product_details(self,data):
        self.env.cr.execute('''select pt.name as name,pt.description as desc,pol.product_qty as qty,
        pt.default_code as code, pol.price_unit as price,pol.price_subtotal as tot,uom.name as u_name from product_template pt 
        join product_product pp on pt.id=pp.product_tmpl_id join product_uom as uom on pt.uom_id=uom.id join purchase_order_line pol
        on pp.id=pol.product_id join purchase_order po on pol.order_id=po.id where po.id=%s order by pol.id'''%(data.id))
        pro_details = self.env.cr.dictfetchall()
        return pro_details
        
    # @api.multi
    # def convert_num_to_word(self,data):
    #     total = '%.3f'%data.amount_total
    #     val = str(total).split('.')
    #     res = ''
    #     amount=int(val[0])
    #     amount1 = num2words(amount)
    #     amount2 = int(val[1])
    #     amount3 = len(val[1])
    #     if amount2 > 0:
    #         res += str(amount1).title()+' '+'&'+' '+str(amount2).title()+' '+'Baisa'
    #     else:
    #         res += str(amount1).title()
    #     return res

    # @api.multi
    def convert_num_to_word(self, data):
        amount = data.amount_total
        amount_in_words = data.currency_id.with_context(lang=data.partner_id.lang or 'es_ES').amount_to_text(amount).title()
        return amount_in_words

    #~ @api.multi
    #~ def convert_num_to_word(self,data):
        #~ total = data.amount_total
        #~ val = str(total).split('.')
        #~ res = ''
        #~ amount=int(val[0])
        #~ amount1 = num2words(amount)
        #~ amount2 = int(val[1])
        #~ amount4 = str(val[1])
        #~ amount3 = len(val[1])
        #~ if amount3 == 3:
            #~ res += str(amount1).title()+' '+'&'+' '+str(amount2).title()+' '+'Baisa'
        #~ else:
            #~ res += str(amount1).title()+' '+'Dollars'+' '+str(amount1).title()+' '+'Cents'
        #~ return res
        
        #~ total = '%.3f'%data.amount_total
        #~ val = total.split('.')
        #~ res = str(num2words(int(val[0]))).title()
        #~ if len(val[1]) == 2:
            #~ res = str(num2words(int(val[0]))).title()+' '+'Dollars'+' '+str(num2words(int(val[1]))).title()+' '+'Cents'
        #~ if len(val[1]) == 3:
            #~ res = str(num2words(int(val[0]))).title()+' '+'&'+' '+ str(val[1]) +' '+'Baisa'
        #~ return res
            
        
        
        
        
    #~ @api.multi
    #~ def convert_num_to_word(self,data):
        #~ total = '%.3f'%data.amount_total
        #~ val = str(total).split('.')
        #~ res = ''
        #~ amount=int(val[0])
        #~ amount1 = num2words(amount)
        #~ amount2 = (val[1])
        #~ if amount2 == 3:
            #~ res += str(amount1).title()+' '+'&'+' '+str(amount2).title()+' '+'Baisa'
        #~ if amount2 == 2:
            #~ res += str(amount1).title()+' '+'Dollars'+' '+str(amount1).title()+' '+'Cents'
        #~ else:
            #~ res += str(amount1).title()             
        #~ return res
    
    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['purchase.order'].browse(ids)
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        department = employee.department_id.name
        return {
            'doc_ids': ids,
            'doc_model': 'purchase.order',
            'docs': report_obj,
            'data': data,
            'department': department,
            'get_product_details': self.get_product_details,
            'convert_num_to_word': self.convert_num_to_word,
        }
