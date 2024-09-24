# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class BbisMailMessageComposeInherit(models.TransientModel):
    _inherit = 'mail.compose.message'

    #@api.multi
    def _get_mail_values(self, res_ids):
        res = super(BbisMailMessageComposeInherit, self).get_mail_values(res_ids)

        for wizard in self:
            ActiveModel = self.env[wizard.model if wizard.model else 'mail.thread']

        for res_id in res:
            res[res_id]['email_cc'] = self.email_cc

            # Get the email of the current user
            current_uid = self.env.uid
            user = self.env['res.users'].browse(current_uid)

            if ActiveModel._name == 'sale.order':
                res[res_id]['email_from'] = user.email_formatted if user.email_formatted else self.email_from
                res[res_id]['reply_to'] = user.email_formatted if user.email_formatted else self.email_from

        return res

    email_cc = fields.Char('Cc', help="Carbon copy recipients (placeholders may be used here)")
