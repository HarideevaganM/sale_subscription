# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    bank_statement_id = fields.Many2one('bank.statement', 'Bank Statement', copy=False)
    statement_date = fields.Date('Bank.St Date', copy=False)

    @api.constrains('statement_date')
    def check_statement_date(self):
        if self.statement_date:
            if self.bank_statement_id and self.bank_statement_id.date_from and self.bank_statement_id.date_to and self.statement_date < self.bank_statement_id.date_from or self.statement_date > self.bank_statement_id.date_to:
                raise UserError(_("Statement Date must be in between statement periods...!"))

    #@api.multi
    def write(self, vals):
        for rec in self:
            if not vals.get("statement_date"):
                vals.update({"reconciled": False})
                if rec.payment_id and rec.payment_id.state == 'reconciled':
                    rec.payment_id.state = 'posted'
            elif vals.get("statement_date"):
                vals.update({"reconciled": True})
                if rec.payment_id:
                    rec.payment_id.state = 'reconciled'
        res = super(AccountMoveLine, self).write(vals)
        return res