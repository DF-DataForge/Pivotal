# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from odoo.http import route,request
from odoo import http,SUPERUSER_ID 

import logging
_logger = logging.getLogger(__name__)


class website_virtual_product(http.Controller):



	@http.route(['/remove/virtualproduct/<temp>'], type='http', auth="public",  website=True)
	def virtual_product_remove(self,temp):

		"""
		Input Parameter : sale_order_line_id  
		Output : Redirect To Cart Page Of User
		Work: 
		This Method is called when user want to delete the current virtual  product,
		It task is to delete the sale_order_line_id as well as deposit the appropriate amount of points in user accounts

		"""		
		sale_order_line=request.env['sale.order.line'].sudo().search([('id', '=', temp),('is_virtual','=',True)])
		if sale_order_line:	
			if hasattr(self, '%s_product_remove' % sale_order_line.virtual_source):
				getattr(self, '%s_product_remove' % sale_order_line.virtual_source)(temp)
		return request.redirect("/shop/cart/")
	