# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pos_order_id    = fields.Many2one('pos.order', string='POS Order')
    # pos_control_id  = fields.Many2one('pos.order', string='POS Order')
    had_statement   = fields.Boolean('Đã có sao kê', compute='_compute_had_statement', store=True)
    session_id      = fields.Many2one('pos.session', 'Phiên POS')

    @api.one
    @api.depends('move_line_ids.statement_id')
    def _compute_had_statement(self):
        for line in self.move_line_ids:
            if line.journal_id == self.destination_journal_id and \
                line.account_id == self.destination_journal_id.default_debit_account_id and line.statement_id:
                self.had_statement = True
                break

