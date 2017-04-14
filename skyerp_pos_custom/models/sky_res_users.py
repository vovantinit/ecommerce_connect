# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    sky_pos_config_ids = fields.Many2many('pos.config', 'sky_pos_config_res_users', 'user_id', 'pos_config_id', string='POS Config')