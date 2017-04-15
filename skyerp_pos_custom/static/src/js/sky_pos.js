odoo.define('skyerp_pos_custom.main', function (require) {
"use strict";

var core    = require('web.core');
var chrome  = require('point_of_sale.chrome');
var screens = require('point_of_sale.screens');
var models  = require('point_of_sale.models');
var session = require('web.session');
var utils = require('web.utils');
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

var round_di = utils.round_decimals;
var round_pr = utils.round_precision;

var Model = require('web.DataModel');

screens.OrderWidget.include({
    set_value: function(val) {
        var order = this.pos.get_order();
        if (order.get_selected_orderline()) {
            var mode = this.numpad_state.get('mode');
            if( mode === 'price'){
                order.get_selected_orderline().set_discount(0)
                return order.get_selected_orderline().set_fix_discount(val);
            } else if ( mode === 'discount') {
                order.get_selected_orderline().set_fix_discount(0)
            }
        }
        this._super.apply(this, arguments);
    },
    
});

var _super_orderline = models.Orderline.prototype;

models.Orderline = models.Orderline.extend({
    initialize: function(attr, options) {
        _super_orderline.initialize.call(this,attr,options);
        this.sky_note = this.sky_note || "";
        this.sky_discount_fix_price = this.sky_discount_fix_price || 0.0;
    },

    set_sky_note: function(sky_note){
        this.sky_note = sky_note;
        this.trigger('change',this);
    },
    get_sky_note: function(){
        return this.sky_note;
    },  

    set_fix_discount: function(fix_discount) {        
        this.sky_discount_fix_price = Math.min(Math.max(parseFloat(fix_discount) || 0, 0), this.get_unit_display_price());
        this.trigger('change',this);
    },
    get_fix_discount: function(){
        return round_di(this.sky_discount_fix_price || 0, this.pos.dp['Product Price'])
    },
    get_fix_discount_display(){
        return round_pr(this.get_fix_discount() * this.get_quantity())
    },
    get_base_price:    function(){
        var rounding = this.pos.currency.rounding;
        var base_prise = _super_orderline.get_base_price.apply(this,arguments);
        return round_pr(base_prise - (this.get_fix_discount() * this.get_quantity()) );
    },
    compute_all: function(taxes, price_unit, quantity, currency_rounding) {
        var res = _super_orderline.compute_all.apply(this,arguments);
        res.total_excluded -= (this.get_fix_discount() * this.get_quantity());
        res.total_included -= (this.get_fix_discount() * this.get_quantity());
        return res;
    },

    can_be_merged_with: function(orderline) {
        if (orderline.get_sky_note() !== this.get_sky_note()) {
            return false;
        } else if (orderline.get_fix_discount() !== this.get_fix_discount()) {
            return false;
        } else {
            return _super_orderline.can_be_merged_with.apply(this,arguments);
        }
    },
    clone: function(){
        var orderline = _super_orderline.clone.call(this);
        orderline.sky_note = this.sky_note;
        orderline.sky_discount_fix_price = this.sky_discount_fix_price;
        return orderline;
    },
    export_as_JSON: function(){
        var json = _super_orderline.export_as_JSON.call(this);
        json.sky_note = this.sky_note;
        json.sky_discount_fix_price = this.sky_discount_fix_price;
        return json;
    },
    init_from_JSON: function(json){
        _super_orderline.init_from_JSON.apply(this,arguments);
        this.sky_note = json.sky_note;
        this.sky_discount_fix_price = json.sky_discount_fix_price;
    },
    export_for_printing: function(){
        var res = _super_orderline.export_for_printing.apply(this,arguments);
        res.fix_discount = this.get_fix_discount();        
        return res;
    },
    generate_wrapped_product_name: function() {
        var MAX_LENGTH = 24; // 40 * line ratio of .6
        var wrapped = [];
        var name = this.get_product().display_name;
        var current_line = "";

        if (this.get_product().default_code) {
            name = '[' + this.get_product().default_code + ']' + name;
        }

        while (name.length > 0) {
            var space_index = name.indexOf(" ");

            if (space_index === -1) {
                space_index = name.length;
            }

            if (current_line.length + space_index > MAX_LENGTH) {
                if (current_line.length) {
                    wrapped.push(current_line);
                }
                current_line = "";
            }

            current_line += name.slice(0, space_index + 1);
            name = name.slice(space_index + 1);
        }

        if (current_line.length) {
            wrapped.push(current_line);
        }

        return wrapped;
    },
});


var _super_order = models.Order.prototype;

models.Order = models.Order.extend({

    get_total_discount: function() {
        var res = _super_order.get_total_discount.apply(this,arguments);
        return res + round_pr(this.orderlines.reduce((function(sum, orderLine) {
            return sum + (orderLine.get_fix_discount() * orderLine.get_quantity());
        }), 0), this.pos.currency.rounding);
    },
    initialize: function() {
        _super_order.initialize.apply(this,arguments);
        this.old_order_name = this.old_order_name || 1;
        this.reason = this.reason || 1;
        this.save_to_db();
    },
    export_as_JSON: function() {
        var json = _super_order.export_as_JSON.apply(this,arguments);
        json.old_order_name = this.old_order_name;
        json.reason = this.reason;
        return json;
    },
    init_from_JSON: function(json) {
        _super_order.init_from_JSON.apply(this,arguments);
        this.old_order_name = json.old_order_name || 1;
        this.reason = json.reason || 1;
    },
    export_for_printing: function() {
        var json = _super_order.export_for_printing.apply(this,arguments);
        json.old_order_name = this.get_old_order_name();
        json.reason = this.get_tgl_reason();
        return json;
    },
    get_old_order_name: function(){
        return this.old_order_name;
    },    
    set_old_order_name: function(old_order_name) {
        this.old_order_name = old_order_name;
    },
    get_tgl_reason: function(){
        return this.reason;
    },
    set_tgl_reason: function(reason) {
        this.reason = reason;
    },
    // add_product: function(product, options){
    //     if (product.qty_available <= 0 && product.type == 'product') {
    //         return this.pos.gui.show_popup('error-traceback',{
    //             'title': _t('Thông báo lỗi'),
    //             'body': _t('Không đủ số lượng sản phẩm trong kho!'),
    //         });
    //     }
    //     _super_order.add_product.apply(this,arguments);
    // },

});

screens.ActionpadWidget.include({

    renderElement: function() {
        var self = this;
        this._super();
        this.$('.pay').click(function(){
            var order                   = self.pos.get_order(),
                orderlines              =  order.get_orderlines(),
                tgl_client              = order.get_client(),
                amount_line_negative    = 0,
                datas                   = [],
                negative_data           = null,
                client_id               = null;


            // Kiem tra san pham co trong kho
            _.each(orderlines, function(for_line){

                var sum_quatity = 0;
                _.each(orderlines, function(line){
                    if (line.get_product() === for_line.get_product()) {
                        sum_quatity += line.get_quantity();
                    }
                });
                // console.log(for_line.get_product().display_name, sum_quatity);

                if (sum_quatity > for_line.get_product().qty_available && for_line.get_product().type == 'product') {
                    self.gui.show_screen('products');
                    self.gui.show_popup('error',{
                        'title': _t('Thông báo lỗi'),
                        'body': _t('Số lượng sản phẩm ' + for_line.get_product().display_name + ' không đủ.'),
                    });
                }

            });    

            if (tgl_client) {
                client_id = tgl_client.id;
            }     

            _.each(orderlines, function(for_line) {
                datas.push({
                    'product_id':       for_line.get_product().id,
                    'qty':              for_line.get_quantity(),
                    'price':            for_line.get_price_without_tax(),
                });
            });

            var negative_qty = _.filter(datas, function(value, key, list){
                return value.qty < 0;
            }).length;

            // Neu khach tra hang, phai mua mon co gia tri cao hon
            if (order.get_total_with_tax() < 0) {
                self.gui.show_screen('products');
                self.gui.show_popup('alert',{
                    'title': _t('Thông báo lỗi'),
                    'body': _t('Tổng tiển không thể âm! \n\n Nếu khách trả hàng, phải mua lại đơn hàng có giá trị tương đương hoặc cao hơn.'),
                });
            } else if(negative_qty > 0) {
                self.gui.show_screen('products');
                var old_name = $('#tgl_old_order_name').val();
                order.set_old_order_name(old_name);

                new Model('pos.order').call('tgl_check_refund', {
                    'data': datas,
                    'partner_id': client_id || false,
                    'order_name': old_name,
                    'session_id': self.pos.pos_session.id,
                }).then(function (result) {
                    if (result.error) {
                        self.gui.show_popup('alert',{
                            'title': _t('Thông báo lỗi'),
                            'body': _t(result.error),
                        });
                    } else {
                        if (result.notify) {
                            console.log(result.notify);
                            order.set_tgl_reason(result.notify);
                            self.gui.show_popup('alert',{
                                'title': _t('Thông báo'),
                                'body': _t(result.notify),
                            });
                        }
                        self.gui.show_screen('payment');
                    }
                }, function () {
                    self.gui.show_popup('alert',{
                        'title': _t('Thông báo'),
                        'body': _t('Bạn phải kết nối với hệ thống để thực hiện được hành động này, vui lòng kiểm tra lại đường truyền.'),
                    });
                });
            }            
                   
        });
    }

});


var Orderlinesky_noteButton = screens.ActionButtonWidget.extend({
    template: 'SkyOrderlineNoteButton',
    button_click: function(){
        var line = this.pos.get_order().get_selected_orderline();
        if (line) {
            this.gui.show_popup('textarea',{
                title: _t('Add note'),
                value:   line.get_sky_note(),
                confirm: function(sky_note) {
                    line.set_sky_note(sky_note);
                },
            });
        }
    },
});

screens.define_action_button({
    'name': 'orderline_sky_note',
    'widget': Orderlinesky_noteButton,
    'condition': function(){
        return this.pos.config.iface_orderline_sky_notes;
    },
});

});