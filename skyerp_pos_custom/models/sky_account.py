# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import formatLang

class account_journal(models.Model):
    _inherit = 'account.journal'

    @api.multi
    def get_journal_dashboard_datas(self):
        res = super(account_journal, self).get_journal_dashboard_datas()
        self.env.cr.execute("""
            SELECT COUNT(DISTINCT(pos_order_id)) FROM account_payment WHERE  
                id IN (SELECT distinct(payment_id) FROM  account_move_line WHERE statement_id is NULL AND journal_id in %s)
                AND pos_order_id IS NOT NULL AND had_statement = FALSE
            """, (tuple(self.ids),))
        pos_order_count = self.env.cr.fetchone()[0]

        self.env.cr.execute("""
            SELECT COUNT(DISTINCT(session_id)) FROM account_payment WHERE  
                id IN (SELECT distinct(payment_id) FROM  account_move_line WHERE statement_id is NULL AND journal_id in %s)
                AND session_id IS NOT NULL AND had_statement = FALSE
            """, (tuple(self.ids),))
        
        pos_session_count = self.env.cr.fetchone()[0]

        self.env.cr.execute("""
            SELECT sum(sum_cash) FROM pos_session where id in 
                (SELECT DISTINCT(session_id) FROM account_payment WHERE  
                    id IN (SELECT distinct(payment_id) FROM  account_move_line WHERE statement_id is NULL AND journal_id in %s)
                    AND session_id IS NOT NULL AND had_statement = FALSE)
            """, (tuple(self.ids),))

        sum_session_cash = self.env.cr.fetchone()[0]

        self.env.cr.execute("""
            SELECT sum(sky_bank_total) FROM pos_order where id in 
            (SELECT DISTINCT(pos_order_id) FROM account_payment WHERE  
                id IN (SELECT distinct(payment_id) FROM  account_move_line WHERE statement_id is NULL AND journal_id in %s)
                AND pos_order_id IS NOT NULL AND had_statement = FALSE)
            """, (tuple(self.ids),))

        sum_order_bank = self.env.cr.fetchone()[0]

        # pos_order_ids = self.env['account.move.line'].search([('journal_id','in',self.ids),('statement_id','=',False)]).mapped('payment_id').mapped('pos_order_id').filtered(lambda r: not r.had_statement)
        # pos_session_ids = self.env['account.move.line'].search([('journal_id','in',self.ids),('statement_id','=',False)]).mapped('payment_id').filtered(lambda r: not r.had_statement).mapped('session_id')

        res['pos_order_not_statemnet'] = pos_order_count
        res['pos_session_not_statemnet'] = pos_session_count
        res['sum_session_cash'] = sum_session_cash and formatLang(self.env, sum_session_cash, currency_obj=self.currency_id or self.company_id.currency_id) or sum_session_cash
        res['sum_order_bank'] = sum_order_bank and formatLang(self.env, sum_order_bank, currency_obj=self.currency_id or self.company_id.currency_id) or sum_order_bank
        return res


    @api.multi
    def action_open_pos_order(self):
        ctx = self._context.copy()
        self.env.cr.execute("""
            SELECT id FROM pos_order where id in 
            (SELECT DISTINCT(pos_order_id) FROM account_payment WHERE  
                id IN (SELECT distinct(payment_id) FROM  account_move_line WHERE statement_id is NULL AND journal_id in %s)
                AND pos_order_id IS NOT NULL AND had_statement = FALSE)
            """, (tuple(self.ids),))

        pos_order_ids = [order['id'] for order in self.env.cr.dictfetchall()]

        return {
            'name': _('Đơn hàng chưa có sao kê'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'domain':   [('id', 'in', pos_order_ids)],
            'context': ctx,
        }

    @api.multi
    def action_open_pos_session(self):
        ctx = self._context.copy()
        # pos_session_ids = self.env['account.move.line'].search([('journal_id','in',self.ids),('statement_id','=',False)]).mapped('payment_id').filtered(lambda r: not r.had_statement).mapped('session_id').mapped('id')

        self.env.cr.execute("""
            SELECT id FROM pos_session where id in 
                (SELECT DISTINCT(session_id) FROM account_payment WHERE  
                    id IN (SELECT distinct(payment_id) FROM  account_move_line WHERE statement_id is NULL AND journal_id in %s)
                    AND session_id IS NOT NULL AND had_statement = FALSE)
            """, (tuple(self.ids),))

        pos_session_ids = [order['id'] for order in self.env.cr.dictfetchall()]

        return {
            'name': _('Phiên POS chưa có sao kê'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'pos.session',
            'domain':   [('id', 'in', pos_session_ids)],
            'context': ctx,
        }        

