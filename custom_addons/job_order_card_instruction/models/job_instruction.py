# -*- coding: utf-8 -*-

from odoo import models, fields, api


class JobInstruction(models.Model):
    _name = "job.instruction"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'id desc'
    _description = 'Job Instruction'
    
    name = fields.Char(
        string='Number',
    )
    description = fields.Text(
        string="Description",
        required=True,
    )
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('start', 'Started'),
        ('post', 'Paused'),
        ('done', 'Finished'),
        ('cancel', 'Cancelled')],
        string='State',
        readonly=True,
        default='draft',
        track_visibility='onchange')
    instruction_type = fields.Many2one(
        'instruction.type',
        string='Job Instruction',
        required=True,
    )
    quality_checklist_ids = fields.Many2many(
        'quality.checklist',
        string='Quality Checklist',
        readonly=False,
    )
    job_id = fields.Many2one(
        'project.task',
        string='Job',
    )
    image_1 = fields.Binary(
        string='Instruction Photo1',
        related='instruction_type.image_1',
    )
    image_2 = fields.Binary(
        string='Instruction Photo2',
        related='instruction_type.image_2',
    )
    image_3 = fields.Binary(
        string='Instruction Photo3',
        related='instruction_type.image_3',
    )
    image_4 = fields.Binary(
        string='Instruction Photo4',
        related='instruction_type.image_4',
    )
    image_5 = fields.Binary(
        string='Instruction Photo5',
        related='instruction_type.image_5',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible User',
        default=lambda self: self.env.user.id,
        required=True,
    )
    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        default=lambda self: self.env.user.id,
        required=True,
    )
    instruction_date = fields.Date(
        string='Date',
        default=fields.date.today(),
    )

    @api.model
    def create(self, vals):
        vals.update({
            'name': self.env['ir.sequence'].next_by_code('job.instruction.seq')
        })
        return super(JobInstruction, self).create(vals)

    # @api.multi
    @api.onchange('instruction_type')
    def onchange_instruction_type(self):
        for rec in self:
            rec.description = rec.instruction_type.name
            
    # @api.multi
    def start_state(self):
        for rec in self:
            rec.state = 'start'
            
    # @api.multi
    def pause_state(self):
        for rec in self:
            rec.state = 'post'
            
    # @api.multi
    def post_state(self):
        for rec in self:
            rec.state = 'post'
            
    # @api.multi
    def finish_state(self):
        for rec in self:
            rec.state = 'done'
            
    # @api.multi
    def cancel_state(self):
        for rec in self:
            rec.state = 'cancel'
            
    # @api.multi
    def reset_state(self):
        for rec in self:
            rec.state = 'draft'
            
            
    # @api.multi
    def print_job_instruction(self):
        return self.env.ref('job_order_card_instruction.job_instruction_information').report_action(self)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
