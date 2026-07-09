# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import api, fields , models
class SaleOrderLine(models.Model):

	_inherit = "sale.order.line"
	def _get_virtual_sources(self):
		return []
	is_virtual = fields.Boolean(
		string= 'Virtual Product'
	)
	virtual_source = fields.Char(
		string = 'Virtual Source'
	)
	redeem_points = fields.Float(
		string='Redeem Virtual Points'
	)
	reward_amount = fields.Float(
		string='Redeem Amount '
	)
	auction_product_direct_buy = fields.Boolean('Auction Product Direct Buy')
