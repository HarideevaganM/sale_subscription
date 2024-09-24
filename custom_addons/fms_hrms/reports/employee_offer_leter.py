from odoo import api, fields,models,_
from datetime import datetime
from odoo.exceptions import UserError


class EmployeeOfferLetter(models.AbstractModel):
    _name = 'report.fms_hrms.offer_letter'

    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['hr.employee'].browse(ids)       
        return {      
            'doc_ids': ids,
            'doc_model': 'hr.employee',
            'docs': report_obj,
            'data': data,
        }
        #~ return self.env['report'].render('fms_hrms.offer_letter', docargs)
