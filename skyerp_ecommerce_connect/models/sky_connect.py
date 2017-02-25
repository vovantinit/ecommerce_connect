# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def ecommerce_get_category(self):
        self = self.sudo()
        return self.search_read([], ['id', 'name', 'parent_id'])

class ProductProduct(models.Model):
    _inherit = 'product.product'


    @api.model
    def ecommerce_get_product(self, limit=None):
        self = self.sudo()
        return self.search_read([], ['id', 'name', 'lst_price', 'categ_id', 'product_brand_id'], limit=limit)