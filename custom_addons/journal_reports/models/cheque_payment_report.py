from odoo import api, fields, models,_
from datetime import datetime
from num2words import num2words as nw
import re
from odoo.exceptions import UserError
import json


class ChequeAmountWordJournal(models.AbstractModel):
    _name = 'report.journal_reports.report_journal_cheque'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj=self.env['account.move'].browse(docids)
        return{
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': report_obj ,
            'data': data,
            'amount_total_words': self.amount_total_words,
            'cheque_partner': self._cheque_partner,
            'cheque_amount': self._cheque_amount,
            'amount_credit': self._amount_credit,
            
        }
    
    # @api.multi
    def _cheque_partner(self,obj):
        self.env.cr.execute('''SELECT res_partner.name from account_move
                               LEFT JOIN account_payment ON account_payment.ref = account_move.ref
                               LEFT JOIN res_partner ON res_partner.id = account_payment.partner_id
                               WHERE account_move.id=%d '''%(obj.id))
        partnerr_name = self.env.cr.fetchone()
        for i in partnerr_name:
            name = i
        return name
    
    # @api.multi
    def _cheque_amount(self,obj):
        self.env.cr.execute('''SELECT account_payment.amount from account_move
                               LEFT JOIN account_payment ON account_payment.ref = account_move.ref
                               WHERE account_move.id=%d '''%(obj.id))
        amount_tot = self.env.cr.fetchone()
        amount = 0.0
        for j in amount_tot:
            amount = j
        return amount
        
    # @api.multi
    def _amount_credit(self,obj):
        cred = {}
        account_val = self.env['account.account'].search([('name', '=', 'Bank')])
        self.env.cr.execute('''SELECT account_move_line.credit from account_move_line 
                                LEFT JOIN account_move ON account_move_line.move_id = account_move.id
                                WHERE account_move_line.move_id = %d and account_move_line.account_id = %d '''%(obj.id,account_val.id))
        tot_credit = self.env.cr.fetchall()
        total_credit = 0.0
        credit_len = len(tot_credit)
        for j in range(credit_len):
            total_credit += tot_credit[j][0]
        cred = total_credit
        return cred
        
    def amount_total_words(self, obj):
       # print('\n---', obj, '--wGenerator--')
       return nw(obj)


class ChequeAmountWord(models.AbstractModel):
    _name = 'report.journal_reports.report_cheque_pay'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj = self.env['account.payment'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.payment',
            'docs': report_obj ,
            'data': data,
            'amount_total_words': self.amount_total_words,
        }

    def amount_total_words(self, obj):
        # print('\n---', obj, '--wGenerator--')
        return nw(obj)


class PaymentVoucherAmountWord(models.AbstractModel):
    _name = 'report.journal_reports.report_payment_voucher'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj = self.env['account.payment'].browse(docids)
        
        for i in report_obj:
            if i.partner_type != 'supplier':  
               raise UserError(_("You can print the Receipt Voucher only ...!! "))
        return {
            'doc_ids': docids,
            'doc_model': 'account.payment',
            'docs': report_obj ,
            'data': data,
            'amount_total_words': self.amount_total_words,
            'get_memo': self.get_memo,
        }

    def _get_memo(self, obj):
        product=[]
        value=[]
        no=0
        for o in obj: 
            tax=''      
            self.env.cr.execute('''select ap.ref as memo,rp.name as partner,pt.reference as transaction
                                   ,ap.cheque_date as date,
                                    ap.amount as amount,aaa.name as analytic_account,ap.cheque_no as no from account_payment as ap
                                    left join res_partner as rp on ap.partner_id=rp.id
                                    left join payment_transaction as pt on ap.payment_transaction_id=pt.id
                                    Left Join account_analytic_account as aaa on ap.analytic_account_id = aaa.id
                                    where ap.id = %d'''%(o.id))
            s = self.env.cr.fetchall()
            for i in range(len(s)):
                d=s[i][0].replace('\n', ' ').replace('\r', '')
                l=d.split(' ')
                chunks=d.split('\n')    
                f = lambda x, n, acc=[]: f(x[n:], n, acc+[(x[:n])]) if x else acc
                ff=list(f(d,50))
            for i in o.tax_id:
                tax+=i.name+' '
            for j in range(len(ff)):
                if j==0:
                    product.append({ 
                                  'partner' :s[0][1],
                                  'memo':ff[j],
                                  'transaction':s[0][2],
                                  'analytic_account':s[0][5],
                                  'subtotal':'{:,.2f}'.format(s[0][4]),
                                  'date':s[0][3],
                                  'no':s[0][6]
                                  
                                  }) 
                else:
                    product.append({ 
                                  'partner' :'',
                                  'memo':ff[j],
                                  'transaction':'',
                                  'analytic_account':'',
                                  'subtotal':'',
                                  'date':' ',
                                  'no':' '
                                  })
        return product

    def amount_total_words(self, obj):
        # print('\n---', obj, '--wGenerator--')
        return nw(obj)


class ReceiptVoucherAmountWord(models.AbstractModel):
    _name = 'report.journal_reports.report_receipt_voucher'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj = self.env['account.payment'].browse(docids)
        for i in report_obj:
            if i.partner_type != 'customer':  
               raise UserError(_("You can print the Payment Voucher only ...!! "))
        return {
            'doc_ids': docids,
            'doc_model': 'account.payment',
            'docs': report_obj ,
            'data': data,
            'amount_total_words': self.amount_total_words,
        }

    def amount_total_words(self, obj):
        # print('\n---', obj, '--wGenerator--')
        return nw(obj)


class JournalReport(models.AbstractModel):
    _name = 'report.journal_reports.report_journal_voucher'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': report_obj,
            'data': data,
            'amount_debit': self._amount_debit,
            'amount_credit': self._amount_credit,
        }
        
    # @api.multi
    def _amount_debit(self,obj):
        deb = {}       
        self.env.cr.execute('''SELECT account_move_line.debit from account_move_line 
                                LEFT JOIN account_move ON account_move_line.move_id = account_move.id
                                WHERE account_move_line.move_id=%d '''%(obj.id))
        tot_debit = self.env.cr.fetchall()
        total_debit = 0.0
        debit_len = len(tot_debit)
        for i in range(debit_len):
            total_debit += tot_debit[i][0]          
        deb=total_debit
        return deb
    
    # @api.multi
    def _amount_credit(self,obj):
        cred = {}        
        self.env.cr.execute('''SELECT account_move_line.credit from account_move_line 
                                LEFT JOIN account_move ON account_move_line.move_id = account_move.id
                                WHERE account_move_line.move_id=%d '''%(obj.id))
        tot_credit = self.env.cr.fetchall()
        total_credit = 0.0
        credit_len = len(tot_credit)
        for j in range(credit_len):
            total_credit += tot_credit[j][0]
        cred=total_credit
        return cred
  
class DueVendorInvoicesReport(models.AbstractModel):
    _name = 'report.journal_reports.report_due_vendor_invoices'
    
    def _get_type(self,obj):
       for i in obj.account_ids:
           return i.type

    @api.model
    def _get_report_values(self, docids, data=None):
        Report = self.env['report']
        stock_report = Report._get_report_from_name('journal_reports.report_due_vendor_invoices')
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        report_obj = self.env['vendor.list.wizard'].browse(docids)
      
        return {
            'doc_ids': docids,
            'doc_model': 'vendor.list.wizard',
            'docs': report_obj,
            'data': data,
            'get_type': self.get_type,
        }

