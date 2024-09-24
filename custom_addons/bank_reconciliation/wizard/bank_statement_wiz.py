# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning



class BankStatement(models.Model):
    _name = 'bank.statement'

    @api.onchange('date_from', 'date_to', 'account_id')
    def _get_lines(self):
        self.currency_id = self.env.user.company_id.currency_id
        domain = [('account_id', 'in', self.account_id.ids)]
        if self.date_from:
            domain += [('date', '>=', self.date_from)]
        if self.date_to:
            domain += [('date', '<=', self.date_to)]
        s_lines = []
        lines = self.env['account.move.line'].search(domain)

        previous_line = self.env['account.move.line'].search([('account_id', 'in', self.account_id.ids),('date', '>=', '04-01-2020'), ('date', '<=', self.date_to), ('statement_date', '=', False)])
        for line in self.statement_lines:
            line.bank_statement_id = self.id
        for line in previous_line:
            if line.id not in lines.ids:
                line.bank_statement_id = self.id
                lines += line
        self.statement_lines = lines


    #@api.one
    @api.depends('statement_lines.statement_date')
    def _compute_amount(self):
        gl_balance = 0
        bank_balance = 0
        current_update = 0
        domain = [('account_id', 'in', self.account_id.ids)]
        lines = self.statement_lines
        gl_balance += sum([line.debit - line.credit for line in lines])
        domain += [('id', 'in', self.statement_lines.ids), ('statement_date', '!=', False)]
        lines = self.statement_lines.filtered(lambda x: x.statement_date != False)
        bank_balance += sum([line.balance for line in lines])
        current_update += sum([line.debit - line.credit if line.statement_date else 0 for line in self.statement_lines])

        self.gl_balance = gl_balance
        self.bank_balance = bank_balance + current_update
        self.balance_difference = self.gl_balance - self.bank_balance

        domain = [('account_id', 'in', self.account_id.ids)]
        if self.date_to:
            domain += [('date', '<=', self.date_to)]

        lines = self.env['account.move.line'].search(domain)
        self.opening_bal = sum([line.debit - line.credit for line in lines])

        self.debit_bal = sum([line.debit for line in self.statement_lines.filtered(lambda x: x.statement_date == False)])
        self.credit_bal = sum([line.credit for line in self.statement_lines.filtered(lambda x: x.statement_date == False)])

        self.bank_amount = self.opening_bal + self.credit_bal - self.debit_bal

    @api.constrains('date_from', 'date_to', 'account_id')
    def date_validation(self):
        rec = self.env['bank.statement'].search([('id', '!=', self.id), ('account_id', 'in', self.account_id.ids), ('date_from', '<=', self.date_from), ('date_to', '>=', self.date_to)])
        if rec:
            raise UserError(_("Statement already exist for this period...!"))


    state = fields.Selection([('draft', 'Draft'),('confirm', 'Confirmed')], string='Status', index=True, readonly=True, copy=False, default='draft')
    journal_id = fields.Many2one('account.journal', 'Bank', domain=[('type', '=', 'bank')])
    account_id = fields.Many2many('account.account', string='Bank Account', required=True)
    date_from = fields.Date('Date From', required=True)
    date_to = fields.Date('Date To', required=True)
    statement_lines = fields.One2many('account.move.line', 'bank_statement_id')
    gl_balance = fields.Monetary('Balance as per Company Books', readonly=True, compute='_compute_amount')
    bank_balance = fields.Monetary('Balance as per Bank', readonly=True, compute='_compute_amount')
    balance_difference = fields.Monetary('Amounts not Reflected in Bank', readonly=True, compute='_compute_amount')
    current_update = fields.Monetary('Balance of entries updated now')
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('bank.statement'))
    opening_bal = fields.Float("Balance as per Company Books", readonly=True, compute='_compute_amount')
    debit_bal= fields.Float("Debit Balance", readonly=True, compute='_compute_amount')
    credit_bal= fields.Float("Credit Balance", readonly=True, compute='_compute_amount')
    bank_amount = fields.Float("Balance as per Bank", readonly=True, compute='_compute_amount')


    #@api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("You can not delete a confirmed statement!"))
        return super(BankStatement, self).unlink()

    #@api.multi
    def set_to_draft(self):
        self.update({'state': 'draft'})

    #@api.multi
    def confirm(self):
        self.update({'state': 'confirm'})


