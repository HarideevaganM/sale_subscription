
from odoo import models,fields,api, _
from odoo.exceptions import ValidationError

class CRMPiplineWizard(models.TransientModel):
    _name = 'fms.crm.wizard.line'

    create_date = fields.Datetime(string="Create Date")
    name = fields.Char(string="Opportunities")
    type = fields.Selection([('lead','Lead'),('opportunity', 'Opportunity'),
        ], string='Type', default="Opportunities", track_visibility='onchange', copy=False)
    contact_name = fields.Char(string="Contact")
    email_from = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    user_id = fields.Many2one('res.users', string="Salesperson")
    team_id = fields.Many2one('crm.team', string="Sales Channel")
    lead_id = fields.Many2one('crm.lead', string="Crm Lead")
    wizard_id = fields.Many2one('fms.crm.pipline.wizard', string="wizard_id")


class CRMPiplineWizard(models.TransientModel):
    _name = 'fms.crm.pipline.wizard'

    def _prepare_crm_line(self, line):
        return {
            'create_date': line.create_date,
            'name':line.name,
            'type':line.type,
            'contact_name' : line.contact_name,
            'email_from': line.email_from,
            'phone' : line.phone,
            'team_id' : line.team_id.id,
            'lead_id' : line.id,
            }

    @api.model
    def default_get(self, fields):
        lines = []
        result = super(CRMPiplineWizard, self).default_get(fields)
        lead_ids = self.env['crm.lead'].browse(self._context.get('active_ids'))
        if lead_ids:
            team_id = lead_ids.mapped('team_id')
            if len(team_id) > 1:
                raise ValidationError(_('Please select same sales team'))
            if not team_id.user_id:
                raise ValidationError(_('Please set sale team manager'))
            for rec in lead_ids:
                if not rec.team_id:
                    raise ValidationError(_('Please set sales team on %s' %rec.name))
                lines.append((0, 0, self._prepare_crm_line(rec)))
            result.update({
                    'opportunity_ids' : lines, 
                    'team_id': team_id.id, 
                    'user_id': team_id.user_id.id, 
                    'member_ids' : [(6, 0,[x for x in team_id.member_ids.ids])]
                })
        return result

    opportunity_ids = fields.One2many('fms.crm.wizard.line', 'wizard_id', string='Leads/Opportunities')
    user_id = fields.Many2one('res.users', 'Manager')
    team_id = fields.Many2one('crm.team', 'Sales Team')
    assign_type = fields.Selection([('assign_sale_manag','Assign Sales Manager'), ('assign_sale_user', 'Assign Sale User')], string='Assign Type', default="assign_sale_manag")
    assign_user_id = fields.Many2one('res.users', string="Sale User")
    member_ids = fields.Many2many('res.users', string="Team Members")

    #@api.multi
    def assign_team(self):
        for rec in self.opportunity_ids:
            if not rec.user_id and self.assign_type == 'assign_sale_user':
                raise ValidationError(_('Please select salesperson in line'))
            manag_stage_id = self.env.ref('fms_crm_extended.stage_lead5')
            user_stage_id = self.env.ref('fms_crm_extended.stage_lead6')
            if manag_stage_id and user_stage_id:
                if self.assign_type == 'assign_sale_manag':
                    rec.lead_id.write({'user_id' : self.user_id.id, 'stage_id' : manag_stage_id.id})
                else:
                    rec.lead_id.write({'user_id' : rec.user_id.id, 'stage_id' : user_stage_id.id})
        return True

    @api.onchange('assign_user_id')
    def onchange_reconcile(self):
        for rec in self.opportunity_ids:
            rec.user_id = self.assign_user_id and self.assign_user_id.id