from odoo import api, fields, models, _


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_subscribe(self, partner_ids=None, subtype_ids=None, customer_ids=None):
        res = super(MailThread, self)._message_subscribe(partner_ids, subtype_ids, customer_ids)
        if 'partner_id' in self._fields:
            if self.partner_id.id in self.message_partner_ids.ids:
                partner_follower = self.message_follower_ids.filtered(lambda x: x.partner_id.id == self.partner_id.id)
                if partner_follower:
                    partner_follower.sudo().unlink()
        return res