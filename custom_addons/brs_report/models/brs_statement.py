from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
import time
import dateutil.relativedelta
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError,except_orm
import calendar
from dateutil import relativedelta as rdelta

class BrsReconcile(models.Model):
    _name = 'brs.reconcile'

    name   = fields.Char('Name')
    active = fields.Boolean('Active',default=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env['res.company']._company_default_get('brs.reconcile'))    
    brs_reconcile_line = fields.One2many('brs.reconcile.line','brs_reconcile_id',string='Journal')

class BrsReconcileLine(models.Model):
    _name = 'brs.reconcile.line'

    brs_reconcile_id = fields.Many2one('brs.reconcile',string='Journal Line')
    journal_id     = fields.Many2one('account.journal',string='Journal')

class BrsStatement(models.Model):
    _name = 'brs.statement'
    _rec_name= 'brs_id'

    #@api.multi
    def _unreconcile_amount(self):
        for order in self:
            val = val1 = val2 = val3 = 0.0
            for line in order.statement_line:
                if line.reconcile:
                    val  += line.balance
                    val1 += line.credit
                else:
                    val2 += line.balance
                    val3 += line.credit
            order.debit = val
            order.credit = val1
            order.unreconcile_debit = val2
            order.unreconcile_credit = val3
            #~ print 'ccccccccccc', val                          
            #~ print 'ccccccccccc', val1                          
            #~ print 'ccccccccccc', val2                          
            #~ print 'ccccccccccc', val3                         

    #@api.multi
    def _balance_amount(self):
        for line in self:
            line.unreconcile_balance = line.opening_balance + (line.debit - line.credit)
            
    #@api.multi
    def _balance_amount_book(self):
        for line in self:
            line.unreconcile_balance_book = line.bank_balance + (line.debit - line.credit)
            
    #@api.multi
    def _balance_unreconcile_system_amount(self):
        for line in self:
            line.unreconcile_sys_balance = line.unreconcile_debit - line.unreconcile_credit

    share               = fields.Char('Paid')
    brs_id              = fields.Many2one('brs.reconcile','BRS Journal',required=True)
    from_date           = fields.Date('From Date',required=True)
    to_date             = fields.Date('To Date',required=True)
    bank_balance        = fields.Float('Bank Statement Balance')
    opening_balance     = fields.Float('Opening Balance')
    is_imported         = fields.Boolean('Imported Entry',default=False)
    statement_line      = fields.One2many('brs.statement.line','brs_id','Account Entry')
    unreconcile_balance = fields.Float(compute='_balance_amount', string='Book/Reconcile Balance', digits= dp.get_precision('Discount'))
    unreconcile_balance_book = fields.Float(compute='_balance_amount_book', string='Bank/Reconcile Balance', digits= dp.get_precision('Discount'))
    unreconcile_sys_balance = fields.Float(compute='_balance_unreconcile_system_amount', string='Unreconcile Balance', digits= dp.get_precision('Discount'))
    debit               = fields.Float(compute='_unreconcile_amount', digits=dp.get_precision('Discount'), string='Debit')
    credit              = fields.Float(compute='_unreconcile_amount', digits=dp.get_precision('Discount'), string='Credit')
    unreconcile_debit   = fields.Float(compute='_unreconcile_amount', digits=dp.get_precision('Discount'), string='Unreconcile Debit')
    unreconcile_credit  = fields.Float(compute='_unreconcile_amount', digits=dp.get_precision('Discount'), string='Unreconcile Credit')
    state               = fields.Selection([('draft', 'Draft'),('progress', 'Progress'),('cancel', 'Cancel'),('reconcile', 'Reconciled'),('done','Done')],string='Status', select=True, readonly=True, copy=False, default='draft')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env['res.company']._company_default_get('brs.statement'))

    #@api.multi
    def unlink(self):
        for line in self:
            if line.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an BRS statement which is not draft or cancelled.'))
        return super(BrsStatement, self).unlink()

    #@api.multi
    def select_all(self):
        for line in self.statement_line:
            if not line.reconcile:
                line.write({'reconcile':True,'reconcile_date':self.to_date})

    #@api.multi
    def un_select_all(self):
        for line in self.statement_line:
            if line.reconcile:
                line.write({'reconcile':False,'reconcile_date':None})

    #@api.multi
    def reset_to_draft(self):
        if self.statement_line != []:
            for i in self.statement_line:
                i.env.cr.execute(""" DELETE FROM brs_statement_line WHERE id = %d """ % (i.id))
        self.write({'state':'draft'})

    #@api.multi
    def done(self):
        self.write({'state':'done'})

    #@api.multi
    def cancel(self):
        for line in self.statement_line:
            ss = self.env['account.move'].search([('id', 'in', line.move_id.ids)])
            ss.write({'reconcile':False})
            line.write({'reconcile':False})
            line.write({'reconcile_date':False})
        self.write({'state':'cancel'})

    #@api.multi
    def generate(self):
        if self.to_date:
            if self.to_date < self.from_date:
                raise UserError(_("To Date must be greater then From Date"))
        brs_state = self.env['brs.statement'].search([('id', '<', self.id)])
        for rec in brs_state:
            if rec.state != 'done':
                month = datetime.strptime(rec.from_date, '%Y-%m-%d').strftime('%B')
                year = datetime.strptime(rec.from_date, '%Y-%m-%d').strftime('%Y')
                raise UserError(_("Please convert the '%s-%s' BRS Statement into Done State.")%(month,year))
        dat = datetime.strptime(self.to_date, '%Y-%m-%d')
        day_string = dat.strftime('%Y-%m-%d')
        calib = datetime.strptime(day_string, '%Y-%m-%d')
        t=calib + rdelta.relativedelta(days=-1)
        #~ search_id=self.env['brs.statement'].search([('to_date','=',t.strftime('%Y-%m-%d'))],limit=1,order='to_date desc' )
        #~ print 'rrrrrrrrrrrr', search_id
        #~ if search_id:
            #~ self.opening_balance=search_id.unreconcile_balance
        #~ else:
            #~ self.opening_balance=0.00
        brs_val = self.env['brs.reconcile'].browse(self.brs_id.id)
        lines = []
        for rec in brs_val.brs_reconcile_line:
            where=''
            self.env.cr.execute("""select count(id) from brs_statement_line""")
            count_line = self.env.cr.fetchall()
            #~ print 'counttttttttttttttt', count_line
            if self.from_date == self.to_date:
                where += "am.date = '%s' and am.date = '%s' AND am.journal_id = %d and am.company_id=%s" % (self.from_date,self.to_date,rec.journal_id.id,self.company_id.id)
            else:
                if count_line[0][0]==0:
                    where += "am.date >= '%s' and am.date <= '%s' AND am.journal_id = %d and am.company_id=%s" % (self.from_date,self.to_date,rec.journal_id.id,self.company_id.id)
                else:
                    #~ print 'elseeeeeeeeeeeeeee'
                    where += "am.date >= '%s' and am.date <= '%s' AND am.journal_id = %d and am.company_id=%s" % (self.from_date,self.to_date,rec.journal_id.id,self.company_id.id)
            self.env.cr.execute(""" SELECT distinct on(aml.move_id) am.date, aml.debit, aml.credit, am.ref AS cheque, am.bank_date,
                                    am.id AS move_id, am.narration, aml.partner_id
                                    FROM account_move AS am
                                    LEFT JOIN account_move_line AS aml ON (aml.move_id = am.id)
                                    LEFT JOIN account_journal AS aj ON (aj.id=am.journal_id)
                                    LEFT Join brs_statement_line as bsl on am.id=bsl.move_id
                                    WHERE %s and aml.debit > 0 and aml.account_id = aj.default_debit_account_id
                                    AND ((am.reconcile is null) OR (am.reconcile = False)) AND am.bank_date is null
                                    ORDER BY aml.move_id, aml.id""" % (where))
            line_list = [i for i in self.env.cr.dictfetchall()]
            lines.extend(line_list)
            #~ print 'pppppppppp', where
            self.env.cr.execute(""" SELECT distinct on(aml.move_id) am.date, aml.debit, aml.credit, am.ref AS cheque, am.bank_date,
                                    am.id AS move_id, am.narration, aml.partner_id
                                    FROM account_move AS am
                                    LEFT JOIN account_move_line AS aml ON (aml.move_id = am.id)
                                    LEFT JOIN account_journal AS aj ON (aj.id=am.journal_id)
                                    LEFT Join brs_statement_line as bsl on am.id=bsl.move_id
                                    WHERE %s and aml.credit > 0 and aml.account_id = aj.default_credit_account_id
                                    AND ((am.reconcile is null) OR (am.reconcile = False)) AND am.bank_date is null
                                    ORDER BY aml.move_id, aml.id""" % (where))
            line_list = [i for i in self.env.cr.dictfetchall()]
            lines.extend(line_list)
        if lines != []:
            for l in lines:
                vals = {
                       'brs_id'      : self.id,
                       'cheque'      : l['cheque'],
                       'date'        : l['date'],
                       'credit'      : l['credit'],
                       'balance'     : l['debit'],
                       'move_id'     : l['move_id'],
                       'description' : l['narration'],
                       'partner_id'  : l['partner_id'],
                       'reconcile_date' : l['bank_date']
                }
                self.env['brs.statement.line'].create(vals)
        self.write({'state':'progress'})

    #@api.multi
    def validate(self):
        val = 0
        for a in self.statement_line:
            if a.reconcile == True:
                val += 1
        if val > 0:
            for rec in self.statement_line:
                if rec.reconcile == True:
                    if rec.reconcile_date != None:
                        ss = self.env['account.move'].search([('id', '=', rec.move_id.id)])
                        ss.write({
                                  'reconcile' : rec.reconcile,
                                  'bank_date' : rec.reconcile_date,
                        })

                    else:
                        raise UserError(_("Transcation Date Can't Be Empty !"))
        else:
            raise UserError(_("Select atleast One Account Entry Line."))
        self.write({'state':'reconcile'})

    #@api.multi
    def unreconcile(self):
        val = 0
        for a in self.statement_line:
            if a.un_select == True:
                val += 1

        if val > 0:
            for rec in self.statement_line:
                if rec.un_select == True:

                    rec.reconcile = False
                    rec.reconcile_date = False

                    ss = self.env['account.move'].search([('id', '=', rec.move_id.id)])
                    ss.write({
                              'reconcile' : rec.reconcile,
                              'bank_date' : rec.reconcile_date,
                    })
        else:
            raise UserError(_("Unselect atleast One Account Entry Line."))
        self.write({'state':'done'})

class BrsStatementLine(models.Model):
    _name = 'brs.statement.line'

    un_select   = fields.Boolean('Unselect')
    brs_id      = fields.Many2one('brs.statement',string='BRS Statement',ondelete='cascade')
    move_id     = fields.Many2one('account.move')
    date        = fields.Date('Value Date')
    cheque      = fields.Char('Cheque No')
    partner_id  = fields.Many2one('res.partner',string='Customer Name')
    description = fields.Text('Description')
    balance     = fields.Float('Debit')
    credit      = fields.Float('Credit')
    reconcile   = fields.Boolean('Reconcile')
    reconcile_date = fields.Date('Transaction Date')
    state          = fields.Selection([('draft', 'Draft'),('progress', 'Progress'),('cancel', 'Cancel'),('done', 'Done')],string='Status', select=True, readonly=True, copy=False, default='draft',related='brs_id.state')

    @api.onchange('reconcile')
    def onchange_reconcile(self):
        self.reconcile_date = False

class AccountMoveInheritBrs(models.Model):
    _inherit= 'account.move'

    reconcile       = fields.Boolean('Reconcile',default=False)
    is_consolidated = fields.Boolean('Is Consolidated Entry',default=False)
    bank_date       = fields.Date('Bank Book Date')
    consolidate_cheque_no = fields.Char('Reference No')

