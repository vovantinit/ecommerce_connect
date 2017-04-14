# -*- coding: utf-8 -*-
##############################################################################
#
#    @package sky_xxx Ten Module Odoo 10.0
#    @copyright Copyright (C) 2016 Sky ERP Company Limited. All rights reserved.#
#    @license http://www.gnu.org/licenses GNU Affero General Public License version 3 or later; see LICENSE.txt
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'POS Custom',
    'version': '1.0.1',
    'category': 'skyERP',
    "sequence": 5,
    'summary': 'POS Custom',
    'complexity': "easy",
    'description': """
POS custom
===========

In 3 liên
----------

Ghi chú trên dòng đơn hàng
---------------------------

Đơn hàng
---------

    Thên trường: tổng tiền mặt, tổng ngân hàng

    Giảm giá cố định trên dòng đơn hàng

    Không cho bán hàng khi số lượng trong kho không đủ

Màn hình POS
-------------

    Thay logo

    Thay nút "Giá" thành nút "Giảm giá"

    Thêm mã sản phẩm trước tên sản phẩm

    """,
    'author': 'SkyERP team',
    'website': 'https://www.skyerp.net',
    'images': [],
    'depends': ['pos_product_available', 'product_brand'],
    'data': [
        'data/data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sky_template.xml',
        'views/sky_view.xml',
        'views/sky_pos_report_view.xml',
    ],
    'demo': [],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'test': [],
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
