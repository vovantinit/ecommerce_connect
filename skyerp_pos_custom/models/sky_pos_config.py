# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class POSConfig(models.Model):
    _inherit = 'pos.config'

    sky_user_ids = fields.Many2many('res.users', 'sky_pos_config_res_users', 'pos_config_id', 'user_id', string='Users')
    sky_control_bank_journal_id = fields.Many2one('account.journal', 'Control bank journal')
    sky_control_cash_journal_id = fields.Many2one('account.journal', 'Control cash journal')