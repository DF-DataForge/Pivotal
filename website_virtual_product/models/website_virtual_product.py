# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import models, api

from logging import getLogger
_logger = getLogger(__name__)

class WebsiteVirtualProduct(models.Model):
	_name="website.virtual.product"
	_description = "website_virtual_product Class"

	@api.model
	def add_virtual_product(self,order_id,product_id, **kwags):
		"""This method create a virtual product in sale order line entry !	"""
		vals = {
			'order_id':order_id,
			'product_id':product_id.id,
			'name':kwags.get('name') or product_id.name,
			'product_uom':product_id.uom_id.id,
			'product_uom_qty': kwags.get('product_uom_qty',1),
			'price_unit':kwags.get('product_price'),
			'redeem_points':kwags.get('redeem_points',0),
			'reward_amount':kwags.get('product_price'),
			'virtual_source':kwags.get('virtual_source'),
			'is_virtual':True,
		}
		return self.env['sale.order.line'].sudo().create(vals)


	def remove_virtual_product(self, line_id):
		"""	This method remove the virtual product from sale orde line entry !	"""
		virtual_sol_obj=self.env['sale.order.line'].sudo().search([('id', '=', line_id),('is_virtual','=',True)])
		return virtual_sol_obj.unlink()


class Website(models.Model):
	_inherit='website'

	def get_virtual_image(self):
		"""	The image fields must have the name virtual_product_image"""
		return False
