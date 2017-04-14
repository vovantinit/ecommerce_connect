# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PosSession(models.Model):
    _inherit = 'pos.session'


    sum_cash = fields.Float(compute='_compute_sum_cash', digits=0, default=0, string='Tổng tiền mặt', store=True)

    @api.one 
    @api.depends('statement_ids.line_ids.amount')
    def _compute_sum_cash(self):
        self.sum_cash = sum(line.amount for line in self.statement_ids.filtered(lambda r: r.journal_id.type != 'bank').mapped('line_ids') )

    @api.multi
    def sky_re_open_session(self):
        self.write({'state': 'opened'})

    @api.multi
    def action_pos_session_close(self):

        for order in self.mapped('order_ids'):
            if order.alert_order and not order.approve_user_id:
                raise ValidationError(_('Tất cả đơn trả hàng bất thường phải được duyệt trước khi đóng phiên.'))

        res = super(PosSession, self).action_pos_session_close()
        self = self.sudo()
        payment_method_id = self.env.ref('account.account_payment_method_manual_out').id
        Payment = self.env['account.payment']

        for session in self:
            if not session.config_id.sky_control_bank_journal_id:
                raise ValidationError(_("Bank control haven't set up."))
            if not session.config_id.sky_control_cash_journal_id:
                raise ValidationError(_("Cash control haven't set up."))
            
            company_id = session.config_id.company_id.id
            ctx = dict(self.env.context, force_company=company_id, company_id=company_id, payment_method_id=payment_method_id)
            for st in session.statement_ids:
                if st.journal_id.type != 'bank':
                    sum_cash = sum(line.amount for line in st.line_ids) 
                    if sum_cash > 0:
                        payment_id = Payment.with_context(ctx).create({
                            'payment_date':          fields.Date.today(),
                            'payment_type':         'transfer',
                            'communication':        'From ' + session.name,
                            'journal_id':               st.journal_id.id,
                            'destination_journal_id':   session.config_id.sky_control_cash_journal_id.id,
                            'amount':                   sum_cash,  
                            'payment_method_id':        payment_method_id, 
                            'session_id':               session.id,                   
                        })
                        payment_id.post()
                else:
                    # if sum(line.amount for line in st.line_ids.filtered(lambda r: r.pass_pos)) != 0:
                    #     raise UserError(_('So tien tra lai phai tuong ung voi gia tri cua don hang!'))
                    # for line in st.line_ids.filtered(lambda r: not r.pass_pos):
                    for line in st.line_ids:
                        if line.pass_pos: continue
                        payment_id = Payment.with_context(ctx).create({
                            'payment_date':          line.date,
                            'payment_type':         'transfer',
                            'communication':        (line.name or '') + ' ' + (line.ref or ''),
                            'journal_id':               st.journal_id.id,
                            'destination_journal_id':   session.config_id.sky_control_bank_journal_id.id,
                            'amount':                   line.amount,  
                            'payment_method_id':        payment_method_id,  
                            'pos_order_id':             line.pos_statement_id and line.pos_statement_id.id or False,            
                        })
                        payment_id.post()                

        return res