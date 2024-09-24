from odoo import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_types = fields.Selection([
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
        ('neft', 'NEFT'),
       ], string='Payment Method')

    payment_ref = fields.Char('Payment Reference')

    @api.model
    def default_get(self, fields):
        rec = super(AccountPayment, self).default_get(fields)
        # invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        invoice_defaults = self.update({'invoice_ids': [(0, 0, rec.get('invoice_ids'))]})
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            rec['name'] = invoice['name']
            rec['num'] = invoice['name']
        return rec





