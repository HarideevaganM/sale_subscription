from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Inherit account invoice in ITC for updating the invoice number in ITC screen.
class ITCaccountinvoice_inherit(models.Model):
    _inherit = 'account.move'

    itc_permit_ids = fields.One2many("invoice.itc.details", 'invoice_id', string="ITC Permit Details")

    # Inherit the action_invoice_open for updating the ITC Permits Invoice Number while validating the invoice.
    #@api.multi
    def action_invoice_open(self):
        res = super(ITCaccountinvoice_inherit, self).action_invoice_open()
        itc_details = self.env['invoice.itc.details'].search([('invoice_id', '=', self.id)])
        for itc in itc_details:
            itc_permit = self.env['itc.permit'].search([('id', '=', itc.permit_id.id)])
            if itc_permit:
                itc_permit.write({'invoice_no': self.id})
        return res


# Create model for ITC details in Invoice
class InvoiceITCDetails(models.Model):
    _name = "invoice.itc.details"

    invoice_id = fields.Many2one('account.move', string="Invoice Number")
    permit_id = fields.Many2one('itc.permit', string="ITC Permit ID")
    request_number = fields.Char(related='permit_id.request_number', string='Request Number')
    partner_id = fields.Many2one(related='permit_id.partner_id', string='Client Name')
    vehicle_no = fields.Many2one(related='permit_id.vehicle_no', string='Vehicle Number')
    permit_start_date = fields.Date(related='permit_id.permit_start_date', string='Start Date')
    permit_end_date = fields.Date(related='permit_id.permit_end_date', string='End Date')
    state = fields.Selection(related='permit_id.state', string='Status')

    def unlink(self):
        for record in self:
            if record.permit_id.invoice_no:
                users_groups = self.env.ref('fms_access_group.group_profile_accounting_manager').users.ids
                if self.env.uid in users_groups:
                    self.permit_id.write({'invoice_no': False})
                else:
                    raise ValidationError(_("Sorry, you dont have permission to delete this entry."))

        result = super(InvoiceITCDetails, self).unlink()
        return result
