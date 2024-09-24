from odoo import api, fields, models, _
from datetime import datetime,date,timedelta
from odoo.exceptions import UserError, AccessError,ValidationError
from num2words import num2words


class SaleInvoiceReport(models.AbstractModel):
    _name = 'report.fms_sale.sale_invoice_report'        
            
    def _get_purchase_date(self, data):
        self.env.cr.execute("""SELECT TO_CHAR(po.date_order,'dd-MM-YY') as date_order FROM purchase_order po
                            JOIN account_move ai ON(po.name=ai.invoice_origin)WHERE ai.id=%d""" % data.id)
        date_order = self.env.cr.dictfetchall()
        return date_order

    # @api.multi
    def _get_product_details(self,data):
        self.env.cr.execute('''select pt.name as name,pt.description as desc,ail.quantity as aty,
                                pt.default_code as code,ail.price_unit as price,ail.price_subtotal as tot,
                                uom.name as u_name
                                from product_template pt 
                                join product_product pp on pt.id=pp.product_tmpl_id 
                                join product_uom as uom on pt.uom_id=uom.id 
                                join account_move_line ail on pp.id=ail.product_id 
                                join account_move ai on ail.move_id=ai.id
                                where ai.id=%s order by ail.id''' % data.id)
        pro_details = self.env.cr.dictfetchall()
        return pro_details

    # @api.multi
    def _get_currency_name(self,data):
        self.env.cr.execute('''select rc.name as currency, rc.rounding from account_move ai 
                                join res_currency rc on ai.currency_id=rc.id where ai.id =%s ''' % data.id)
        currency_name = self.env.cr.dictfetchall()
        return currency_name

    # @api.multi
    def _get_device_details(self, data):
        self.env.cr.execute("""select spl.name as serial,
                        pt.name as device,vm.name as vehicle,
                        jc.vehicle_description as vehicle_name,jc.chassis_no as chassis,
                        jc.gsm_number as gsm,jc.installation_date as ins_date,
                        jc.device_status as status
                        from account_move ai left join
                        sale_order so on so.name=ai.invoice_origin left join
                        job_card jc on jc.sale_order_id=so.id
                        left join vehicle_master vm on vm.id=jc.vehicle_number
                        left join stock_production_lot spl
                        on spl.id=jc.device_serial_number_new_id left join
                        product_product pp on pp.id=jc.device_id left join
                        product_template pt on pt.id=pp.product_tmpl_id

                        where ai.id=%s and jc.state='done' """ % (data.id))
        device_details = self.env.cr.dictfetchall()
        return device_details
    
    # @api.multi
    # def convert_num_to_word(self,data):
    #     total = '%.3f'%data.amount_total
    #     val = str(total).split('.')
    #     res = ''
    #     amount=int(val[0])
    #     amount1 = num2words(amount)
    #     amount2 = int(val[1])
    #     if amount2 > 0:
    #         res += str(amount1).title()+' '+'&'+' '+str(amount2).title()+' '+'Baisa'
    #
    #     else:
    #         res += str(amount1).title()
    #     return res

    # @api.multi
    def convert_num_to_word(self, data):
        amount = data.amount_total
        amount_in_words = data.currency_id.with_context(lang=data.partner_id.lang or 'es_ES').amount_to_text(amount).title()
        return amount_in_words

    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['account.move'].browse(ids)
        for report in report_obj:
            if report.move_type == 'out_invoice':
                return {
                    'doc_ids': ids,
                    'doc_model': 'account.move',
                    'docs': report_obj,
                    'data': data,
                    'get_purchase_date': self.get_purchase_date,
                    'get_device_details': self.get_device_details,
                    'convert_num_to_word': self.convert_num_to_word,
                    'get_product_details': self.get_product_details,
                    'get_currency_name': self.get_currency_name,
                }
            else:
                raise ValidationError("This is not sale Invoice")
                
                
class SaleInvoiceReportInclusive(models.AbstractModel):
    _name = 'report.fms_sale.sale_invoice_report_inclusive'        
            
    def _get_purchase_date(self, data):
        self.env.cr.execute("""SELECT TO_CHAR(po.date_order,'dd-MM-YY') as date_order FROM purchase_order po
                            JOIN account_move ai ON(po.name=ai.invoice_origin)WHERE ai.id=%d""" % data.id)
        date_order = self.env.cr.dictfetchall()
        return date_order

    # @api.multi
    def _get_product_details(self, data):
        self.env.cr.execute('''select pt.name as name,pt.description as desc,ail.quantity as aty,
                                pt.default_code as code,ail.price_unit as price,ail.price_subtotal as tot,
                                uom.name as u_name
                                from product_template pt 
                                join product_product pp on pt.id=pp.product_tmpl_id 
                                join product_uom as uom on pt.uom_id=uom.id 
                                join inclusive_invoice_line ail on pp.id=ail.product_id 
                                join account_move ai on ail.move_id=ai.id
                                where ai.id=%s order by ail.id''' % data.id)
        pro_details = self.env.cr.dictfetchall()
        return pro_details

    # @api.multi
    def _get_currency_name(self, data):
        self.env.cr.execute('''select rc.name as currency, rc.rounding from account_move ai 
                                join res_currency rc on ai.currency_id=rc.id where ai.id =%s ''' % data.id)
        currency_name = self.env.cr.dictfetchall()
        return currency_name

    # @api.multi
    def _get_device_details(self, data):
        self.env.cr.execute("""select spl.name as serial,
                        pt.name as device,vm.name as vehicle,
                        jc.vehicle_description as vehicle_name,jc.chassis_no as chassis,
                        jc.gsm_number as gsm,jc.installation_date as ins_date,
                        jc.device_status as status
                        from account_move ai left join
                        sale_order so on so.name=ai.invoice_origin left join
                        job_card jc on jc.sale_order_id=so.id
                        left join vehicle_master vm on vm.id=jc.vehicle_number
                        left join stock_production_lot spl
                        on spl.id=jc.device_serial_number_new_id left join
                        product_product pp on pp.id=jc.device_id left join
                        product_template pt on pt.id=pp.product_tmpl_id
                        where ai.id=%s and jc.state='done' """ % data.id)
        device_details = self.env.cr.dictfetchall()
        return device_details
    
    # @api.multi
    # def convert_num_to_word(self,data):
    #     total = '%.3f'%data.amount_total
    #     val = str(total).split('.')
    #     res = ''
    #     amount=int(val[0])
    #     amount1 = num2words(amount)
    #     amount2 = int(val[1])
    #     if amount2 > 0:
    #         res += str(amount1).title()+' '+'&'+' '+str(amount2).title()+' '+'Baisa'
    #
    #     else:
    #         res += str(amount1).title()
    #     return res

    # @api.multi
    def convert_num_to_word(self, data):
        amount = data.amount_total
        amount_in_words = data.currency_id.with_context(lang=data.partner_id.lang or 'es_ES').amount_to_text(amount).title()
        return amount_in_words

    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['account.move'].browse(ids)
        for report in report_obj:
            if report.move_type == 'out_invoice':
                return {
                    'doc_ids': ids,
                    'doc_model': 'account.move',
                    'docs': report_obj,
                    'data': data,
                    'get_purchase_date': self.get_purchase_date,
                    'get_device_details': self.get_device_details,
                    'convert_num_to_word': self.convert_num_to_word,
                    'get_product_details': self.get_product_details,
                    'get_currency_name': self.get_currency_name,
                }
            else:
                raise ValidationError("This is not sale Invoice")


class LeaseInvoiceReport(models.AbstractModel):
    _name = 'report.fms_sale.lease_invoice_report'

    # @api.multi
    def _get_date_details(self, data):
        division_inv_date = datetime.strptime(str(data.invoice_date), '%Y-%m-%d')
        month = division_inv_date.month
        return month
    
    # @api.multi
    def convert_num_to_word(self,data):
        total = '%.3f' % data.amount_total
        val = str(total).split('.')
        res = ''
        amount = int(val[0])
        amount1 = num2words(amount)
        amount2 = int(val[1])
        if amount2 > 0:
            res += str(amount1).title()+' '+'&'+' '+str(amount2).title()+' '+'Baisa'
        else:
            res += str(amount1).title()
        return res  
    
    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['division.invoice'].browse(ids)
        return {      
            'doc_ids': ids,
            'doc_model': 'division.invoice',
            'docs': report_obj,
            'data': data,
            'get_date_details': self.get_date_details,
            'convert_num_to_word': self.convert_num_to_word,
        }


#~ class DeliveryReport(models.AbstractModel):
    #~ _name = "report.fms_sale.delivery_order_template"
    
    #~ def line_item(self,data):
        #~ self.env.cr.execute(""" select sml.lot_name as lot,sml.qty_done as qty,
                                #~ pt.name as pname,
                                #~ spl.name as name from stock_move_line sml join stock_picking sp
                                #~ on sp.id=sml.picking_id join stock_production_lot spl
                                #~ on spl.id=sml.lot_id join product_product proname 
                                #~ on proname.id=spl.product_id join product_template pt
                                #~ on pt.id=proname.product_tmpl_id where sp.id=%s"""%(data.id))
        #~ lot_obj = self.env.cr.dictfetchall()
        #~ return lot_obj
                                
    #~ @api.model
    #~ def _get_report_values(self,docids,data=None):
        #~ delivery_obj = self.env["stock.picking"].browse(docids)
        #~ return {
                #~ 'doc_ids': docids,
                #~ 'doc_model': "stock.picking",
                #~ 'docs': delivery_obj,
                #~ 'data': data,
                #~ 'line_item': self.line_item,
                
        #~ }


class InstallationCertificate(models.AbstractModel):
    _name = "report.fms_sale.installation_certificate"
    
    @api.model
    def _get_report_values(self, docids, data=None):
        certificate_obj = self.env["installation.certificate"].browse(docids)
        return {
                'doc_ids': docids,
                'doc_model': "installation.certificate",
                'docs': certificate_obj,
                'data': data,
                
        }
