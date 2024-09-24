from odoo import api, exceptions, fields, models, _


class JobcardDashboard(models.Model):
    _name='jobcard.dashboard'

    name = fields.Many2one('project.task', 'Task Reference')
    # count_open_card = fields.Integer(compute='open_card_count', string='Open')
    open_card = fields.Char(string='Open')
    approve_card = fields.Char(string='To be approved')
    # count_approve_card = fields.Integer(compute='to_approve_card_count',string='To Approve')
    sale_order_id = fields.Many2one("sale.order", "Sale Reference")
    color = fields.Integer(string='Color Index')
    engineer_id = fields.Many2one("hr.employee", "Engineer")

    #@api.multi
    def open_card_count(self):
        for obj in self:
            job_card_obj = self.env['job.card'].search([('task_id','=',obj.name.id)])
            open_list = []
            for card in job_card_obj:
                if card.state in ['open','configured','installed']:
                    open_list.append(card)
                    obj.count_open_card = len(open_list)
                    obj.open_card = len(open_list)

    #@api.multi
    def to_approve_card_count(self):
        for obj in self:
            job_card_obj = self.env['job.card'].search([('task_id','=',obj.name.id)])
            to_approve_list = []
            for card in job_card_obj:
                if card.state in ['submitted']:
                    to_approve_list.append(card)
                    obj.count_approve_card = len(to_approve_list)
                    obj.approve_card = len(to_approve_list)

    #@api.multi
    def approve_job_card_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'job_order_action')
        approve_list = []
        if self.name:
            approve_job_card_obj = self.env['job.card'].search([('task_id', '=', self.name.id)])
        else:
            approve_job_card_obj = self.env['job.card'].search([('sale_order_id', '=', self.sale_order_id.id)])
        for card in approve_job_card_obj:
            if card.state == 'submitted':
                approve_list.append(card.id)
        res['domain'] = [('id', 'in', approve_list)]
        return res

    #@api.multi
    def open_job_card_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'job_order_action')
        open_list = []
        if self.name:
            job_card_obj = self.env['job.card'].search([('state','in',['open', 'configured']),('task_id','=',self.name.id)])
        else:
            job_card_obj = self.env['job.card'].search([('state','in',['open', 'configured']),('sale_order_id','=',self.sale_order_id.id)])
        for card in job_card_obj:
            open_list.append(card.id)
        res['domain'] = [('id', 'in', open_list)]
        return res

    #@api.multi
    def installed_job_card_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'job_order_action')
        open_list = []
        if self.name:
            job_card_obj = self.env['job.card'].search([('state','=', 'installed'),('task_id','=',self.name.id)])
        else:
            job_card_obj = self.env['job.card'].search([('state', '=', 'installed'), ('sale_order_id', '=', self.sale_order_id.id)])
        for card in job_card_obj:
            open_list.append(card.id)
        res['domain'] = [('id', 'in', open_list)]
        return res

    #@api.multi
    def view_open_cards(self):
        res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'job_order_action')
        open_list = []
        if self.name:
            job_card_obj = self.env['job.card'].search([('state', 'in', ['open', 'configured', 'installed']),('task_id','=',self.name.id)])
        else:
            job_card_obj = self.env['job.card'].search([('state', 'in', ['open', 'configured', 'installed']), ('sale_order_id', '=', self.sale_order_id.id)])
        for card in job_card_obj:
            open_list.append(card.id)
        res['domain'] = [('id', 'in', open_list)]
        self.open_card = len(open_list)
        return res

    #@api.multi
    def view_submitted_cards(self):
        res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'job_order_action')
        approved = []
        if self.name:
            job_card_obj = self.env['job.card'].search([('state', '=','submitted'), ('task_id', '=', self.name.id)])
        else:
            job_card_obj = self.env['job.card'].search([('state', '=', 'submitted'), ('sale_order_id', '=', self.sale_order_id.id)])
        for card in job_card_obj:
            approved.append(card.id)
        res['domain'] = [('id', 'in', approved)]
        self.approve_card = len(approved)
        return res

class ProjectTaskInherit(models.Model):
    _inherit = 'project.task'

    @api.model
    def create(self,vals):
        res = super(ProjectTaskInherit,self).create(vals)
        jobcard_dashboard_obj = self.env['jobcard.dashboard']
        jobcard_dashboard_obj.create({'name': res.id})
        return res

