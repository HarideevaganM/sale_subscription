from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    #~ #@api.multi
    #~ def name_get(self):
        #~ res = super(ResPartner, self).name_get()
        #~ data = []
        #~ for partner in self:
           #~ display_value = ''
           #~ display_value += partner.name or ""
           #~ display_value += ' - '
           #~ display_value += partner.city or ""
           #~ data.append((partner.id, display_value))
        #~ return data
    
    #~ #@api.multi
    #~ def name_get(self):
        #~ result = []
        #~ for record in self:
            #~ record_name = str(record.name) + ' - ' + str(record.city)
            #~ result.append((record.id, record_name))
        #~ return result
    
    def name_get(self): 
        result = []
        for inv in self:
            result.append((inv.id, "%s - %s" % (inv.name, inv.city or '')))
        return result
