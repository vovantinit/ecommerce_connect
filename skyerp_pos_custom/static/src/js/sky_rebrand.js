odoo.define('skyerp_pos_custom.sky_rebrand', function (require) {
"use strict";

var core    = require('web.core');
var chrome  = require('point_of_sale.chrome');
var screens = require('point_of_sale.screens');
var models  = require('point_of_sale.models');
var devices = require('point_of_sale.devices');
var session = require('web.session');
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

chrome.Chrome.include({

    build_chrome: function() { 
        this._super.apply(this, arguments);
        this.$('.pos-logo').attr('src', '/web/binary/company_logo');
    },

});

devices.ProxyDevice.include({
    print_receipt: function(receipt) { 
        this._super(receipt);
        this.pos.old_receipt = receipt || this.pos.old_receipt;
    },
});

// Print 3 bill
screens.ReceiptScreenWidget.include({

    print_xml: function() {
        var self = this;
        this._super.apply(this, arguments);
        // return this._super.apply(this, arguments).then(function () {
        
        var cashier = '<div>--------------------------------</div>';
        var headers = ["<receipt align='center' width='42' value-thousands-separator='' >",           
                "<div font='b'>",
                "<div t-if='receipt.cashier'>",
                "<div class='cashier'>",
                "<div>--------------------------------</div>"],
            bill2 = "<div>LIÊN 2 - DÀNH CHO CỬA HÀNG</div>",
            bill3 = "<div>LIÊN 3 - DÀNH CHO KẾ TOÁN</div>";
        var header = '';
        headers.forEach( function(value, index) {
            header += value;
        });

        setTimeout(function(){            

            if (self.pos.config.print_3_receipt) {
                var env = {
                    widget:  self,
                    receipt: self.pos.get_order().export_for_printing(),
                    paymentlines: self.pos.get_order().get_paymentlines()
                };
                self.pos.get_order()._printed = false;

                if (self.pos.old_receipt.indexOf(cashier) >= 0) {
                    console.log(self.pos.old_receipt.substring(self.pos.old_receipt.indexOf(cashier) + cashier.length));
                    self.pos.old_receipt = header + bill2 + self.pos.old_receipt.substring(self.pos.old_receipt.indexOf(cashier) + cashier.length);
                    console.log(self.pos.old_receipt);
                }

                self.pos.proxy.print_receipt(self.pos.old_receipt);

                // var receipt2 = QWeb.render('XmlReceiptPrint2',env);
                // self.pos.proxy.print_receipt(receipt2);
                // var receipt3 = QWeb.render('XmlReceiptPrint3',env);

                setTimeout(function(){
                    if (self.pos.old_receipt.indexOf(cashier) >= 0) {
                        self.pos.old_receipt = header +  bill3 + self.pos.old_receipt.substring(self.pos.old_receipt.indexOf(bill2) + bill2.length);
                    }

                    self.pos.proxy.print_receipt(self.pos.old_receipt);

                    // self.pos.proxy.print_receipt(receipt3);
                    self.pos.get_order()._printed = true;
                }, 5000);
            }
        }, 5000);
    },

});


});