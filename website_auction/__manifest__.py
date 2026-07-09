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
  "name"                 :  "Website Auction",
  "summary"              :  """The admin can now host online auction for different products on his Odoo website. The buyer bid on the products and highest bid win when the timer runs out.""",
  "category"             :  "Website",
  "version"              :  "1.0.0",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
 
  "website"              :  "https://store.webkul.com/Odoo-Website-Auction.html",
  "description"          :  """Odoo website auction
Odoo Online Auction
Buyer Bid Marketplace
Ecommerce auction management
Manage online auction
Take bids from buyers
Odoo online bidding
Sale by bid
Sell by bid
Simple bid
Advanced auction
Online car auction
Website auction
Host auction
Odoo auction""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=website_auction&version=14.0&custom_url=/shop",
  "depends"              :  [
                             'website_sale',
                             'sale_stock',
                             'website_mail',
                             'website_virtual_product',
                             'website_webkul_addons',
                            ],
  "data"                 :  [
                             'edi/wk_auction_bidder.xml',
                             'edi/wk_auction_subscriber.xml',
                             'edi/wk_auction_admin.xml',
                             'data/cron.xml',
                             'data/data.xml',
                             'views/website_auction.xml',
                             'views/product_template.xml',
                             'views/my_account_template.xml',
                             'views/inherited_virtual_product.xml',
                             'views/auction_res_config.xml',
                             'views/webkul_addons_config_inherit_view.xml',
                             'views/auction_product_bids_template.xml',
                             'views/products_on_auction_views.xml',
                             'security/ir.model.access.csv',
                            ],
  "demo"                 :  ['demo/demo.xml'],
  "assets"               :  {
        'web.assets_frontend':  [
          'website_auction/static/src/css/website_auction.css',
          'website_auction/static/src/css/auction.scss',
          'website_auction/static/src/js/jquery.downCount.js',
          'website_auction/static/src/js/wk_website_countdown.js',
          'website_auction/static/src/js/website_auction.js'
        ]
  },
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "price"                :  149,
  "currency"             :  "USD",
}
