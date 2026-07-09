# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Website Extra Order Line",
  "summary"              :  """Add an extra line on Website Sales Order, this module is used by other modules like loyalty module, etc.""",
  "category"             :  "Website",
  "version"              :  "19.0.1.0.0",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "maintainer"           :  "Prakash Kumar",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo.html",
  "description"          :  """Add an extra line on Website Sales Order, this module is used by other modules like loyalty module, etc.""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=website_virtual_product",
  "depends"              :  ['website_sale'],
  "data"                 :  [
                              'views/website_virtual_product.xml',
                              'security/ir.model.access.csv',
                            ],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "pre_init_hook"        :  "pre_init_check",
}
