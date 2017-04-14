# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _

class PosConfig(models.Model):
    _inherit = 'pos.config'

    print_3_receipt = fields.Boolean(string='Print 3 bill')
    iface_orderline_sky_notes = fields.Boolean(string='Note in Order line')

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.multi
    @api.depends('statement_ids')
    def _sky_compute_total(self):
        for order in self:
            order.sky_bank_total = sum(line.amount for line in order.statement_ids if line.journal_id and line.journal_id.type == 'bank')
            order.sky_cash_total = sum(line.amount for line in order.statement_ids if line.journal_id and line.journal_id.type == 'cash')

    sky_bank_total = fields.Float(compute='_sky_compute_total', string='Bank total', digits=0, store=True)
    sky_cash_total = fields.Float(compute='_sky_compute_total', string='Cash total', digits=0, store=True)

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    sky_note = fields.Char('Note')    
    sky_discount_fix_price = fields.Float('Fix discount', digits=0, default=0.0)

    @api.depends('price_unit', 'tax_ids', 'qty', 'discount', 'product_id')
    def _compute_amount_line_all(self):
        super(PosOrderLine, self)._compute_amount_line_all()
        for line in self:
            line.price_subtotal -= (line.sky_discount_fix_price or 0.0) * line.qty
            line.price_subtotal_incl -= (line.sky_discount_fix_price or 0.0) * line.qty

class PosOrderReport(models.Model):
    _inherit = 'report.pos.order'

    price_unit      = fields.Float(string='Unit Price', readonly=True)
    discount        = fields.Float(string='Discount (%)')
    fix_discount    = fields.Float(string='Fix discount')
    sky_note        = fields.Char('Ghi chú')
    product_brand_id = fields.Many2one('product.brand', string='Thương hiệu')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_pos_order')
        self._cr.execute("""
            CREATE OR REPLACE VIEW report_pos_order AS (
                SELECT
                    MIN(l.id) AS id,
                    COUNT(*) AS nbr_lines,
                    s.date_order AS date,
                    SUM(l.qty * u.factor) AS product_qty,
                    SUM(l.qty * (l.price_unit - l.sky_discount_fix_price)) AS price_sub_total,
                    SUM((l.qty * (l.price_unit - l.sky_discount_fix_price)) * (100 - l.discount) / 100) AS price_total,
                    SUM(l.qty * l.price_unit * (l.discount / 100) + (l.qty * l.sky_discount_fix_price)) AS total_discount,
                    (SUM(l.qty*(l.price_unit-l.sky_discount_fix_price))/SUM(l.qty * u.factor))::decimal AS average_price,
                    SUM(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)) AS delay_validation,
                    s.id as order_id,
                    s.partner_id AS partner_id,
                    s.state AS state,
                    s.user_id AS user_id,
                    s.location_id AS location_id,
                    s.company_id AS company_id,
                    s.sale_journal AS journal_id,
                    l.product_id AS product_id,
                    pt.categ_id AS product_categ_id,
                    p.product_tmpl_id,
                    ps.config_id,
                    pt.pos_categ_id,
                    pc.stock_location_id,
                    s.pricelist_id,
                    s.session_id,
                    s.invoice_id IS NOT NULL AS invoiced,
                    sum(l.price_unit) AS price_unit,
                    sum(l.discount) AS discount,
                    sum(l.sky_discount_fix_price) AS fix_discount,
                    l.sky_note,
                    product_brand.id AS product_brand_id,
                    pt.supplier_id AS supplier_id
                FROM pos_order_line AS l
                    LEFT JOIN pos_order s ON (s.id=l.order_id)
                    LEFT JOIN product_product p ON (l.product_id=p.id)
                    LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                    LEFT JOIN product_brand ON (pt.product_brand_id=product_brand.id)
                    LEFT JOIN product_uom u ON (u.id=pt.uom_id)
                    LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                    LEFT JOIN pos_config pc ON (ps.config_id=pc.id)
                GROUP BY
                    s.id, s.date_order, s.partner_id,s.state, pt.categ_id,
                    s.user_id, s.location_id, s.company_id, s.sale_journal,
                    s.pricelist_id, s.invoice_id, s.create_date, s.session_id,
                    l.product_id,
                    pt.categ_id, pt.pos_categ_id,
                    p.product_tmpl_id,
                    ps.config_id,
                    pc.stock_location_id,
                    l.sky_note,
                    product_brand.id,
                    pt.supplier_id
                HAVING
                    SUM(l.qty * u.factor) != 0
            )
        """)


class PosOrderReportGroup(models.Model):
    _name = 'report.pos.order.group'

    description = "Báo cáo bán hàng theo khách hàng, sản phẩm"
    _auto = False
    _order = 'product_id desc'

    date = fields.Datetime(string='Ngày đặt hàng', readonly=True)
    order_id = fields.Many2one('pos.order', string='Đơn hàng', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Đối tác', readonly=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Mẫu sản phẩm', readonly=True)
    state = fields.Selection(
        [('draft', 'Mới'), ('paid', 'Đã thanh toán'), ('done', 'Đã vào sổ'),
         ('invoiced', 'Đã xuất hóa đơn'), ('cancel', 'Hủy')],
        string='Status')
    user_id = fields.Many2one('res.users', string='NV bán hàng', readonly=True)
    price_total = fields.Float(string='Giá tổng', readonly=True)
    price_sub_total = fields.Float(string='Tổng (chưa VAT)', readonly=True)
    total_discount = fields.Float(string='Giảm giá tổng', readonly=True)
    average_price = fields.Float(string='Giá bình quân', readonly=True, group_operator="avg")
    location_id = fields.Many2one('stock.location', string='Địa điểm', readonly=True)
    company_id = fields.Many2one('res.company', string='Công ty', readonly=True)
    nbr_lines = fields.Integer(string='# Số dòng', readonly=True, oldname='nbr')
    product_qty = fields.Integer(string='Số lượng', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Sổ nhật kí')
    delay_validation = fields.Integer(string='Delay Validation')
    product_categ_id = fields.Many2one('product.category', string='Nhóm sản phẩm', readonly=True)
    invoiced = fields.Boolean(readonly=True)
    config_id = fields.Many2one('pos.config', string='Điểm bán lẻ', readonly=True)
    pos_categ_id = fields.Many2one('pos.category', string='Public Category', readonly=True)
    stock_location_id = fields.Many2one('stock.location', string='Kho hàng', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Bảng giá', readonly=True)
    session_id = fields.Many2one('pos.session', string='Phiên', readonly=True)

    price_unit      = fields.Float(string='Đơn giá', readonly=True)
    discount        = fields.Float(string='Chiết khấu (%)')
    fix_discount    = fields.Float(string='Giảm giá')
    sky_note        = fields.Char('Ghi chú')
    product_brand_id = fields.Many2one('product.brand', string='Thương hiệu')
    supplier_id     = fields.Many2one('res.partner', 'Nhà cung cấp')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_pos_order_group')
        self._cr.execute("""
            CREATE OR REPLACE VIEW report_pos_order_group AS (
                SELECT
                    MIN(l.id) AS id,                    
                    SUM(l.qty * u.factor) AS product_qty,
                    SUM(l.qty * (l.price_unit - l.sky_discount_fix_price)) AS price_sub_total,
                    SUM((l.qty * (l.price_unit - l.sky_discount_fix_price)) * (100 - l.discount) / 100) AS price_total,
                    SUM(l.qty * l.price_unit * (l.discount / 100) + (l.qty * l.sky_discount_fix_price)) AS total_discount,
                    (SUM(l.qty*(l.price_unit-l.sky_discount_fix_price))/SUM(l.qty * u.factor))::decimal AS average_price,
                    s.partner_id AS partner_id,                    
                    l.product_id AS product_id,
                    pt.categ_id AS product_categ_id,
                    p.product_tmpl_id,                    
                    sum(l.price_unit) AS price_unit,
                    sum(l.discount) AS discount,
                    sum(l.sky_discount_fix_price) AS fix_discount,
                    product_brand.id AS product_brand_id,
                    pt.supplier_id AS supplier_id
                FROM pos_order_line AS l
                    LEFT JOIN pos_order s ON (s.id=l.order_id)
                    LEFT JOIN product_product p ON (l.product_id=p.id)
                    LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                    LEFT JOIN product_brand ON (pt.product_brand_id=product_brand.id)
                    LEFT JOIN product_uom u ON (u.id=pt.uom_id)
                    LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                    LEFT JOIN pos_config pc ON (ps.config_id=pc.id)
                GROUP BY
                    s.partner_id,                             
                    l.product_id,
                    pt.categ_id,                     
                    p.product_tmpl_id,                    
                    product_brand.id,
                    pt.supplier_id 
                HAVING
                    SUM(l.qty * u.factor) != 0
            )
        """)

class PosOrderReportSupplier(models.Model):
    _name = 'report.pos.order.supplier'

    description = "Báo cáo bán hàng cho kế toán"
    _auto = False
    _order = 'date desc'

    date = fields.Datetime(string='Ngày đặt hàng', readonly=True)
    order_id = fields.Many2one('pos.order', string='Đơn hàng', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Đối tác', readonly=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Mẫu sản phẩm', readonly=True)
    state = fields.Selection(
        [('draft', 'Mới'), ('paid', 'Đã thanh toán'), ('done', 'Đã vào sổ'),
         ('invoiced', 'Đã xuất hóa đơn'), ('cancel', 'Hủy')],
        string='Status')
    user_id = fields.Many2one('res.users', string='NV bán hàng', readonly=True)
    price_total = fields.Float(string='Gía tổng', readonly=True)
    price_sub_total = fields.Float(string='Tổng (chưa VAT)', readonly=True)
    total_discount = fields.Float(string='Giảm gía tổng', readonly=True)
    average_price = fields.Float(string='Gía bình quân', readonly=True, group_operator="avg")
    location_id = fields.Many2one('stock.location', string='Địa điểm', readonly=True)
    company_id = fields.Many2one('res.company', string='Công ty', readonly=True)
    nbr_lines = fields.Integer(string='# Số dòng', readonly=True, oldname='nbr')
    product_qty = fields.Integer(string='Số lượng', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Sổ nhật kí')
    delay_validation = fields.Integer(string='Delay Validation')
    product_categ_id = fields.Many2one('product.category', string='Nhóm sản phẩm', readonly=True)
    invoiced = fields.Boolean(readonly=True)
    config_id = fields.Many2one('pos.config', string='Điểm bán lẻ', readonly=True)
    pos_categ_id = fields.Many2one('pos.category', string='Public Category', readonly=True)
    stock_location_id = fields.Many2one('stock.location', string='Kho hàng', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Bảng gía', readonly=True)
    session_id = fields.Many2one('pos.session', string='Phiên', readonly=True)

    price_unit      = fields.Float(string='Đơn gía', readonly=True)
    discount        = fields.Float(string='Chiết khấu (%)')
    fix_discount    = fields.Float(string='Giảm gía')
    sky_note        = fields.Char('Ghi chú')
    product_brand_id = fields.Many2one('product.brand', string='Thương hiệu')
    supplier_id     = fields.Many2one('res.partner', 'Nhà cung cấp')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_pos_order_supplier')
        self._cr.execute("""
            CREATE OR REPLACE VIEW report_pos_order_supplier AS (
                SELECT
                    MIN(l.id) AS id,
                    COUNT(*) AS nbr_lines,
                    s.date_order AS date,
                    SUM(l.qty * u.factor) AS product_qty,
                    SUM(l.qty * (l.price_unit - l.sky_discount_fix_price)) AS price_sub_total,
                    SUM((l.qty * (l.price_unit - l.sky_discount_fix_price)) * (100 - l.discount) / 100) AS price_total,
                    SUM(l.qty * l.price_unit * (l.discount / 100) + (l.qty * l.sky_discount_fix_price)) AS total_discount,
                    (SUM(l.qty*(l.price_unit-l.sky_discount_fix_price))/SUM(l.qty * u.factor))::decimal AS average_price,
                    SUM(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)) AS delay_validation,
                    s.id as order_id,
                    s.partner_id AS partner_id,
                    s.state AS state,
                    s.user_id AS user_id,
                    s.location_id AS location_id,
                    s.company_id AS company_id,
                    s.sale_journal AS journal_id,
                    l.product_id AS product_id,
                    pt.categ_id AS product_categ_id,
                    p.product_tmpl_id,
                    ps.config_id,
                    pt.pos_categ_id,
                    pc.stock_location_id,
                    s.pricelist_id,
                    s.session_id,
                    s.invoice_id IS NOT NULL AS invoiced,
                    sum(l.price_unit) AS price_unit,
                    sum(l.discount) AS discount,
                    sum(l.sky_discount_fix_price) AS fix_discount,
                    l.sky_note,
                    product_brand.id AS product_brand_id,
                    pt.supplier_id AS supplier_id
                FROM pos_order_line AS l
                    LEFT JOIN pos_order s ON (s.id=l.order_id)
                    LEFT JOIN product_product p ON (l.product_id=p.id)
                    LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                    LEFT JOIN product_brand ON (pt.product_brand_id=product_brand.id)
                    LEFT JOIN product_uom u ON (u.id=pt.uom_id)
                    LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                    LEFT JOIN pos_config pc ON (ps.config_id=pc.id)
                GROUP BY
                    s.id, s.date_order, s.partner_id,s.state, pt.categ_id,
                    s.user_id, s.location_id, s.company_id, s.sale_journal,
                    s.pricelist_id, s.invoice_id, s.create_date, s.session_id,
                    l.product_id,
                    pt.categ_id, pt.pos_categ_id,
                    p.product_tmpl_id,
                    ps.config_id,
                    pc.stock_location_id,
                    l.sky_note,
                    product_brand.id,
                    pt.supplier_id
                HAVING
                    SUM(l.qty * u.factor) != 0
            )
        """)
