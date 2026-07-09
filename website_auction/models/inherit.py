# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#	See LICENSE file for full copyright and licensing details.
#
##########################################################################
from dateutil import relativedelta
from datetime import date, datetime
import logging
from markupsafe import Markup
from pytz import timezone
from time import localtime
from odoo import api, fields, models, _
from odoo.exceptions import  ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.http import request
_logger = logging.getLogger(__name__)
DateTimeFomat = '%Y-%m-%d %H:%M:%S'

class ProductTemplate(models.Model):
    _inherit = 'product.template'


    @api.model
    def _get_nondraft_auction(self,not_state=None):
        not_state = not_state or ['draft']
        auctions = self.sudo().tmpl_auction_ids.filtered(
            lambda auction_id:str(auction_id.state) not in not_state
        )
        if auctions:
            return auctions[0]


    def _compute_auction_product_sale(self):
        for product  in self:
            auction_product_sale  =True
            auction = product._get_nondraft_auction()
            if auction:
                auction_product_sale = auction.product_sale
            product.auction_product_sale = auction_product_sale


    auction_product_sale = fields.Boolean(
        compute = _compute_auction_product_sale
    )
    tmpl_auction_ids = fields.One2many(
        string='product auction',
        comodel_name='wk.website.auction',
        inverse_name='product_tmpl_id',
        copy=False
    )
    



class ProductProduct(models.Model):
    _inherit = 'product.product'


    product_auction_ids = fields.One2many(
        string='auction',
        comodel_name='wk.website.auction',
        inverse_name='product_id',
        copy=False
    )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"


    def _get_virtual_sources(self):
        result=super(SaleOrderLine,self)._get_virtual_sources()
        return result+[('wk_website_auction','Website Auction')]


class Website(models.Model):
    _inherit= 'website'

    def _get_website_partner(self):
        return self.env['res.partner'].sudo().search([('user_ids','=',request.uid)],limit=1)

    def _get_win_auction(self):
        result= self.env['wk.website.auction'].sudo().search(
                [('state','in',['complete','finish'])]
        )
        result=result.filtered(
            lambda r: r.winner_id== self._get_website_partner()
        )
        return result

    def _get_active_bids(self):

        domain = [
            ('partner_id','=',self._get_website_partner().id),
            ('state','=','active')
        ]
        result = self.env['wk.auction.bidder'].sudo().search(
            domain,order='auction_fk,date desc'
        )
        return result.filtered(
            lambda bid: bid.auction_fk.state in ['running','extend']
        )

    def _get_all_bids(self):
        domain =[
            ('partner_id','=',self._get_website_partner().id),
            ('state','!=','active')
        ]
        result= self.env['wk.auction.bidder'].sudo().search(
            domain,order='auction_fk,date asc'
        )
        return result


    def _get_partner_heighest_bid(self,auction_obj):
        domain = [
            ('partner_id','=',self._get_website_partner().id),
            ('bid_type','=','simple'),
            ('auction_fk','=',auction_obj.id)
        ]
        auction_bidder=self.env['wk.auction.bidder'].sudo().search(domain)
        return  auction_bidder and auction_bidder.sorted(
            key=lambda bidder: bidder.bid_offer)[-1].bid_offer or 0.0


    def _auction_subscribed(self,auction_obj):
        result =  auction_obj.get_active_subscriber().filtered(
            lambda subscriber: subscriber.partner_id==self._get_website_partner()
        )
        if len(result) > 1:
            return result[0]
        else:
            return result


    def _get_bid_state(self,bid_obj):
        result=dict(bid_obj._get_status_list())
        return result.get(bid_obj.state)


    def _get_bid_type(self,bid_obj):
        result=dict(bid_obj._get_bid_type_list())
        return result.get(bid_obj.bid_type)


    def _get_auction_state(self,auction_obj):
        result=dict(auction_obj._get_status_list())
        return result.get(auction_obj.state)

    def _get_auction_time_left_countdown(self,auction_obj):
        auction_obj.sudo().set_auction_state()
        result=""
        if auction_obj:
            current =datetime.now().replace(microsecond=0)
            wk_end=auction_obj.end_date
            if (auction_obj.extend_by and  auction_obj.extend_date
                    and auction_obj.extend_date>auction_obj.end_date
                    and auction_obj.state in ['extend']):
                wk_end=auction_obj.extend_date
            end = datetime.strptime(str(wk_end), DateTimeFomat)
            diff = relativedelta.relativedelta(end, current)

            day=diff.days >=1 and diff.days or 0
            hour=diff.hours >=1 and diff.hours or 0
            minute=diff.minutes>=1 and diff.minutes or 0
            second=diff.seconds>=1 and diff.seconds or 0
            if auction_obj.state in  ["complete","finish","close"]:
                day,hour,minute,second=0,0,0,0
            result +="<span class='span_time_digit'>{day:02d}</span><span class='span_time_unit'>d. </span>".format(day=day)
            result +="<span class='span_time_digit'>{hour:02d}</span><span class='span_time_unit'>h. </span>".format(hour=hour)
            result +="<span class='span_time_digit'>{minute:02d}</span><span class='span_time_unit'>m. </span>".format(minute=minute)
            result += "<span class='span_time_digit'>{second:02d}</span><span class='span_time_unit'>s. </span>".format(second=second)
        return Markup(result)


    def _get_auction_start_time_left_countdown(self,auction_obj):
        auction_obj.set_auction_state()
        result=""
        if auction_obj:
            current =datetime.now().replace(microsecond=0)
            start = datetime.strptime(
                str(auction_obj.start_date), DateTimeFomat
            )
            diff = relativedelta.relativedelta(start, current)   
            result +="<span class='span_time_digit'>{day:02d}</span><span class='span_time_unit'>d. </span>".format(day=diff.days >=1 and diff.days or 0)
            result +="<span class='span_time_digit'>{hour:02d}</span><span class='span_time_unit'>h. </span>".format(hour=diff.hours >=1 and diff.hours or 0)
            result +="<span class='span_time_digit'>{minute:02d}</span><span class='span_time_unit'>m. </span>".format(minute=diff.minutes>=1 and diff.minutes or 0)
            result += "<span class='span_time_digit'>{second:02d}</span><span class='span_time_unit'>s. </span>".format(second=diff.seconds>=1 and diff.seconds or 0)
        return Markup(result)
    

    def _get_next_bid(self,auction_obj):
        login_user_have_auto_bid=auction_obj.login_user_is_auto_bidder()
        if login_user_have_auto_bid and login_user_have_auto_bid.bid_offer:
            return login_user_have_auto_bid.bid_offer+auction_obj._get_next_autobid_increment()
        return auction_obj._get_next_bid()
