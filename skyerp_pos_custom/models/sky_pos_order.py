# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp

class PosOrder(models.Model):
    _inherit = ['mail.thread', 'pos.order']
    _name = 'pos.order'

    _description = 'Đơn hàng'

    @api.depends('lines.qty')
    def _compute_alert_order(self):
        for order in self:
            for line in order.lines:
                if line.qty < 0:
                    order.alert_order = True
                    break

    refund_from     = fields.Many2one('pos.order', string='Là trả hàng của đơn hàng', readonly=True)
    payment_ids     = fields.One2many('account.payment', 'pos_order_id', 'Payments')
    had_statement   = fields.Boolean('Đã có sao kê', compute='_compute_had_statement', store=True)

    old_order_name  = fields.Char('Old order')

    approve_user_id = fields.Many2one('res.users', readonly=True)
    alert_order     = fields.Boolean(compute='_compute_alert_order', store=True)

    @api.multi
    def sky_action_approve(self):
        for order in self:
            if order.approve_user_id: continue
            order.message_post(body=u'{} đã duyệt đơn hàng được cho là bất thường này.'.format(self.env.user.name))
            order.write({
                'approve_user_id':  self.env.user.id,
            })

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['old_order_name'] = ui_order.get('old_order_name', False)
        return order_fields

    @api.model
    def create(self, vals):
        if vals.get('old_order_name', False):
            old_order = self.search([('name','=',vals.get('old_order_name', False))], limit=1)
            if old_order:
                vals['refund_from'] = old_order.id
        return super(PosOrder, self).create(vals)

    @api.one
    @api.depends('payment_ids.move_line_ids.statement_id')
    def _compute_had_statement(self):
        for payment in self.sudo().payment_ids:
            for line in payment.move_line_ids:
                if line.journal_id == payment.destination_journal_id and \
                    line.account_id == payment.destination_journal_id.default_debit_account_id and line.statement_id:
                    self.sudo().had_statement = True
                    break

    @api.multi
    def refund(self):
        """Create a copy of order  for refund order"""
        PosOrder = self.env['pos.order']
        current_session = self.env['pos.session'].search([('state', '!=', 'closed'), ('user_id', '=', self.env.uid)], limit=1)
        if not current_session:
            raise UserError(_('To return product(s), you need to open a session that will be used to register the refund.'))
        for order in self:
            clone = order.copy({
                'session_id': current_session.id,
                'date_order': fields.Datetime.now(),
                'pos_reference': order.pos_reference,
                'refund_from': order.id,
            })
            clone.name = order.name + _(' REFUND')
            PosOrder += clone

        for clone in PosOrder:
            for order_line in clone.lines:
                order_line.write({'qty': -order_line.qty})
        return {
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': PosOrder.ids[0],
            'view_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }


    def add_payment(self, data):
        if self.refund_from:
            self.refund_from.statement_ids.write({'pass_pos': True})
        return super(PosOrder, self.with_context(default_pass_pos=self.refund_from and True or False)).add_payment(data)

    @api.multi
    def _tgl_check_qty_return(self):
        self.ensure_one()
        for order in self:
            # qty = record.qty + sum(self.search([('sky_note','=',record.order_id.name)]).mapped('qty'))
            pass

    @api.model
    def tgl_check_line_refund(self, product_id, partner_id, qty, price, old_order_name):
        print 'tgl_check_refund', product_id, partner_id, qty, price, old_order_name  
        
        product = self.env['product.product'].browse(product_id)
        OrderLine = self.env['pos.order.line']

        old_order = self.search([('name','=',old_order_name),('partner_id','=',partner_id)])
        if not old_order:
            return {'error': u'Bạn phải chọn đúng khách hàng và nhập đúng mã của đơn hàng cũ.' }

        old_date    = fields.Date.from_string(old_order.date_order[:10])
        date_today  = fields.Date.from_string(fields.Date.today())

        limit_return_day = int(self.env['ir.config_parameter'].sudo().get_param('limit_return_day'))
        if (date_today - old_date).days > limit_return_day:
            return {'notify': u'Đơn hàng đã quá {} ngày.'.format(limit_return_day) }

        line_return = OrderLine.search([('sky_note','=',old_order.name)]) + old_order.lines
        qty_can_be_return = sum(line_return.filtered(lambda r: r.product_id.id == product_id).mapped('qty'))

        if qty_can_be_return + qty < 0:
            return {'error': u'Đơn hàng {} chỉ có thể trả tối đa {} sản phẩm {}.'.format(old_order_name, int(qty_can_be_return), product.display_name) }

        return {'notify': 'Luu y, don hang nay phai duoc cap tren duyet truoc khi dong phien'}    

    @api.model
    def tgl_check_refund2(self, data, partner_id, order_name, session_id):

        # Tim don hang cu
        old_order = self.search([('name','=',order_name)])
        if not old_order:
            return {'error': u'Số đơn hàng cũ không được tìm thấy.'}
        # Kiem tra Khach hang
        order_partner_id = old_order.partner_id and old_order.partner_id.id or False
        if order_partner_id != partner_id:
            return {'error': u'Khách hàng không đúng.'}

        # Neu tat ca cac dong deu am (so luong < 0) thi tat ca thong tin phai trung khop
        if all(line['qty'] < 0 for line in data):
            if len(data) != len(old_order.lines):
                return {'error': u'Tất cả thông tin phải trùng khớp với đơn hàng cũ.'}
            if old_order.session_id.id != session_id:
                return {'error': u'Đơn trả hàng phải ở phiên hiện tại.' }
            for line in data:
                for order_line in old_order.lines:
                    if order_line.product_id.id == line['product_id'] \
                    and int(order_line.qty) + int(line['qty']) == 0 \
                    and order_line.price_subtotal + line['price']  == 0:
                        break
                else:
                    return {'error': u'Tất cả thông tin phải trùng khớp với đơn hàng cũ.'}

        else:
            # limit_return_day = int(self.env['ir.config_parameter'].sudo().get_param('limit_return_day'))
            Product = self.env['product.product']
            line_return = self.env['pos.order.line'].search([('order_id.refund_from','=',old_order.id)]) + old_order.lines
            for line in data:
                if line['qty'] > 0: continue
                product = Product.browse(line['product_id'])
                qty_can_be_return = sum(line_return.filtered(lambda r: r.product_id.id == line['product_id']).mapped('qty'))
                if qty_can_be_return + line['qty'] < 0:
                    return {'error': u'Đơn hàng {} chỉ có thể trả tối đa {} sản phẩm {}.'.format(order_name, int(qty_can_be_return), product.display_name) }

            else:
                pass
        return {}

    @api.model
    def tgl_check_payment(self, data, order_name):
        print data, order_name


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.multi
    def write(self, vals):
        res = super(PosOrderLine, self).write(vals)
        for record in self:
            if record.order_id.refund_from and record.qty > 0:
                raise ValidationError(_('Đây là đơn hàng trả lại. Số lượng sản phẩm không thể lớn hơn 0.'))
        return res

