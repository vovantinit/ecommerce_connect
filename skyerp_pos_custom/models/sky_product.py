# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('seller_ids.name')
    def _compute_supplier_id(self):
        for record in self:
            for seller in record.seller_ids:
                if seller.name:
                    record.supplier_id = seller.name


    supplier_id = fields.Many2one('res.partner', compute='_compute_supplier_id', store=True)


