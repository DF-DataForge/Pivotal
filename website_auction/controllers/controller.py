# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#################################################################################
import werkzeug
from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound
from odoo.addons.website_sale.controllers.main import WebsiteSale as  website_sale
from odoo.addons.website_virtual_product.controllers.main import website_virtual_product
from odoo.addons.website_auction.models.website_auction_exception import *
from odoo.addons.website.controllers.main import QueryURL
import datetime


import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager



class CustomerPortalInherit(CustomerPortal):


    def _prepare_home_portal_values(self, counters):
        values = super(CustomerPortalInherit, self)._prepare_home_portal_values(counters)
        website = request.env['website'].get_current_website()
        if 'win_auction_count' in counters:
            Auction = request.env['wk.website.auction']
            domain = [
            ('state','in',['complete','finish']),
            # ('winner_id', '=', partner_id)
            ]
            auctions = Auction.search(domain)
            partner_id = request.website._get_website_partner().id
            auctions = auctions.filtered(lambda auction:auction.winner_id.id==partner_id)
            values['win_auction_count'] = len(auctions)
        return values

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortalInherit, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        partner_id = request.website._get_website_partner().id

        Auction = request.env['wk.website.auction']

        domain = [
            ('state','in',['complete','finish']),
            # ('winner_id', '=', partner_id)
        ]
        auctions = Auction.search(domain)
        auctions = auctions.filtered(lambda auction:auction.winner_id.id==partner_id)
        values.update({
            'win_auction_count': len(auctions),
        })
        return values

    @http.route(
        [
        '/my/auctions',
        '/my/auctions/page/<int:page>',
        ],
         type='http', auth="user", website=True)
    def portal_my_auctions(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        partner_id = request.website._get_website_partner().id

        Auction = request.env['wk.website.auction']
        domain = [
            ('state','in',['complete','finish']),
            # ('winner_id', '=', partner_id)
        ]
        auction_count = Auction.search_count(domain)
        pager = request.website.pager(
            url='/my/auctions',
            total=auction_count,
            page=page,
            step=5
        )
        auctions = Auction.search(domain, limit=5, offset=pager['offset'],order='id desc')
        auctions = auctions.filtered(lambda auction:auction.winner_id.id==partner_id)

        if not len(auctions):
            values['no_auctions']=1
        values['won_auctions'] = auctions
        values['pager'] = pager
        values['page_name'] = 'auctions'
        values['default_url'] ='/my/auctions'
        return  request.render("website_auction.my_auction", values)
    @http.route(
        [
            '/my/bids',
            '/my/bids/page/<int:page>',
        ],
         type='http', auth="user", website=True)
    def portal_my_bids(self, page=1, state=None,**kwargs):
        partner_id = request.website._get_website_partner().id
        values = self._prepare_portal_layout_values()
        Bidder = request.env['wk.auction.bidder'].sudo()
        domain = [('partner_id','=',partner_id)]
        if state=='active':
            domain+= [('state', '=', 'active')]
        else:
            domain+= [('state', '!=', 'active')]
        bid_count = Bidder.search_count(domain)
        pager = request.website.pager(
            url='/my/bids',
            total=bid_count,
            page=page,
            url_args={'state': state},

            step=5
        )
        # search the count to display, according to the pager data
        bids = Bidder.search(domain, limit=5, offset=pager['offset'],order='id desc')
        if state=='active' :
            values['no_active_bids']=not len(bids)
            values['active_bids'] = bids
        else:
            values['no_bids']=not len(bids)
            values['all_bids'] = bids
        values['pager'] = pager
        values['page_name'] = 'auctions'
        return  request.render("website_auction.my_auction", values)

class WebsiteSale(website_sale):

    @http.route(['/products-on-auction',
                 '/products-on-auction/page/<int:page>',
                 ],
        type='http', auth="public", website=True)
    def product_on_auction(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, tags='', **post):
        website = request.env['website'].get_current_website()
        live = True
        website.sudo().auction_default_sort = "live"
        if post.get("auction"):
            live = post.get("auction") == "live"
            website.sudo().auction_default_sort = "live" if live else "upcoming"

        request.update_context(**{"auction": True, "live": live})

        # Delegate the whole product lookup / filtering / layout computation to
        # the standard shop controller (the auction filter is injected through
        # the request context, see website._product_domain()) and only swap the
        # rendered template and the page URLs.
        response = self.shop(page=page, category=category, search=search,
                             min_price=min_price, max_price=max_price, tags=tags, **post)
        if not hasattr(response, 'qcontext'):
            # The shop controller returned a redirection.
            return response
        values = response.qcontext

        url = "/products-on-auction"
        url_args = dict(post)
        if search:
            url_args['search'] = search
        if min_price:
            url_args['min_price'] = min_price
        if max_price:
            url_args['max_price'] = max_price
        values['pager'] = website.pager(
            url=url, total=values['search_count'], page=page,
            step=values['ppg'], scope=5, url_args=url_args)
        values['keep'] = QueryURL(
            url, auction=post.get('auction'),
            **self._shop_get_query_url_kwargs(search, min_price, max_price, **post))

        return request.render("website_auction.product_on_auction", values)

    @http.route()
    def product(self, product, **kwargs):
        r = super(WebsiteSale, self).product(product, **kwargs)
        if not hasattr(r, 'qcontext'):
            return r
        wk_auction = product.sudo()._get_nondraft_auction()
        if wk_auction and not(wk_auction.product_sale):
            wk_auction.sudo().set_auction_state()
            r.qcontext.update(wk_auction.get_publish_fields())
        return r

    @http.route(
        ['/auction/place/bid'],
        type='http', auth="public", website=True,csrf=False)
    def auction_place_bid(self,**post):
        auction_obj=request.env['wk.website.auction'].sudo().browse(int(post.get('auction_fk')))
        post['bid_offer'] = round(request.pricelist.currency_id._convert(float(post.get('bid_offer')),auction_obj.currency_id,request.env.company,datetime.datetime.now()))
        referrer  =request.httprequest.referrer and request.httprequest.referrer or '/shop/product/%s'%(auction_obj.product_tmpl_id.id)
        website_partner=request.website._get_website_partner()
        if not website_partner:
            return werkzeug.utils.redirect(referrer+ "#loginfirst")
        if auction_obj.state not in ['running', 'extend']:
            return werkzeug.utils.redirect(referrer+ "#bid_notallow")
        try:
            res = auction_obj.create_bid(post.get('bid_type'),float(post.get('bid_offer')),website_partner.id)
            return werkzeug.utils.redirect(referrer + "#bidsubmit" )
        except MinimumBidException as e:
            return werkzeug.utils.redirect(referrer + "#minbid" )
        except AutoBidException as e:
            return werkzeug.utils.redirect(referrer + "#autobid" )
        except Exception as e:
            _logger.info("Auction Error %r",e)
            return werkzeug.utils.redirect(referrer + "#biderr" )
        return werkzeug.utils.redirect(referrer)

    @http.route(
        ['/auction/buy/now/<model("wk.website.auction"):auction_obj>'],
        type='http', auth="public", website=True)
    def auction_buy_now(self,auction_obj,**post):
        order = request.cart or request.website._create_cart()
        price_unit = auction_obj.product_id.currency_id._convert(auction_obj.buynow_price,request.pricelist.currency_id,request.env.company,fields.Datetime.now())
        values = {
            'price_unit':price_unit,
            'virtual_source':'wk_website_auction',
            'is_virtual':True,
            'auction_product_direct_buy':True
            }
        response = order._cart_add(product_id=auction_obj.product_id.id, quantity=1)
        sale_line_id = request.env['sale.order.line'].sudo().browse(response.get('line_id'))
        sale_line_id.write(values)
        return werkzeug.utils.redirect('/shop/cart' + "#create" )


    @http.route(
        ['/auction/cart/create/<model("wk.website.auction"):auction_obj>',
        '/auction/cart/update/<model("wk.website.auction"):auction_obj>'],
        type='http', auth="public", website=True)
    def auction_cart_create(self,auction_obj,**post):
        auction_obj = auction_obj.sudo()
        referrer  =request.httprequest.referrer and request.httprequest.referrer or '/shop/product/%s'%(auction_obj.product_tmpl_id.id)
        if auction_obj.state=='complete':
            order = request.cart or request.website._create_cart()
            res = request.env['website.virtual.product'].sudo().add_virtual_product(
                order_id=order.id,
                product_id=auction_obj.product_id,
                product_price=auction_obj.current_price,
                virtual_source='wk_website_auction',
            )
            if res:
                auction_obj.order_id=order.id
                auction_obj.action_finish_auction()
        return werkzeug.utils.redirect(referrer + "#create" )

    @http.route(
        ['''/auction/unsubscribe/<model("wk.website.auction"):auction_obj>/<string:deactivate_token>'''],
        type='http', auth="public", website=True,csrf=False)
    def auction_unsubscribe(self,auction_obj,deactivate_token=None,**post):
        referrer  =request.httprequest.referrer and request.httprequest.referrer or '/shop/product/%s'%(auction_obj.product_tmpl_id.id)
        partner = request.website._get_website_partner()
        if not partner:
            return werkzeug.utils.redirect(referrer+ "#loginfirst")
        subscriber_obj =  request.env['wk.auction.subscriber']
        template_unsubscribe =request.env.ref('website_auction.notify_subscriber_unsubscribe', False)
        try:
            subscriber= auction_obj.sudo().get_active_subscriber().filtered(lambda subscriber: subscriber.deactivate_token==deactivate_token)
            if subscriber:
                subscriber.sudo().write({'subscribe':False})
                template_unsubscribe.sudo().send_mail(subscriber.id, force_send=True)
            return werkzeug.utils.redirect(referrer+ "#unsubscribed")
        except Exception as e:
            return werkzeug.utils.redirect(referrer + "#biderr" )


        return werkzeug.utils.redirect(referrer)




    @http.route(
        ['''/auction/subscribe/<model("wk.website.auction","[('state','!=','close')]"):auction_obj>'''],
        type='http', auth="public", website=True)
    def auction_subscribe(self,auction_obj,deactivate_token=None,**post):
        referrer  =request.httprequest.referrer and request.httprequest.referrer or '/shop/product/%s'%(auction_obj.product_tmpl_id.id)
        partner = request.website._get_website_partner()
        if not partner:
            return werkzeug.utils.redirect(referrer+ "#loginfirst")
        subscriber_obj =  request.env['wk.auction.subscriber']
        template_subscribe =request.env.ref('website_auction.notify_subscriber_subscribe', False)
        try:
            if partner not in auction_obj.subscriber_ids.mapped('partner_id'):
                subscriber=subscriber_obj.sudo().create(
                            {'partner_id':partner.id,
                            'wk_auction_fk':auction_obj.id,
                            })
                if subscriber:template_subscribe.sudo().send_mail(subscriber.id, force_send=True)

                return werkzeug.utils.redirect(referrer+ "#subscribe")

            elif partner in auction_obj.subscriber_ids.filtered(lambda s: not s.subscribe).mapped('partner_id'):
                subscriber=subscriber_obj.sudo().search(
                            [('partner_id','=',partner.id),
                            ('wk_auction_fk','=',auction_obj.id)],order='create_date desc')

                if subscriber:
                    subscriber.sudo().write({'subscribe':True})
                    template_subscribe.sudo().send_mail(subscriber.id, force_send=True)
                return werkzeug.utils.redirect(referrer+ "#subscribe")
        except Exception as e:
            return werkzeug.utils.redirect(referrer + "#biderr" )


        return werkzeug.utils.redirect(referrer)


    @http.route(
        ['/product/auction/<model("wk.website.auction"):auction_obj>',
         '/product/auction/<model("wk.website.auction"):auction_obj>/page/<int:page>'
        ],
        type='http', auth="public", website=True,csrf=False)
    def auction_product_bids(self,auction_obj,page=1,**post):
        values={}
        values.update(auction_obj.sudo().get_publish_fields())
        bid_record=[]
        Bidder = request.env['wk.auction.bidder'].sudo()
        domain = [('bid_type','!=','auto'),('auction_fk', '=', auction_obj.id)]
        bid_count = Bidder.search_count(domain)
        pager = request.website.pager(
            url='/product/auction/%s'%(auction_obj.id),
            # url_args={'date_begin': date_begin, 'date_end': date_end},
            total=bid_count,
            page=page,
            step=5
        )
        # search the count to display, according to the pager data
        bidders = Bidder.search(domain, limit=5, offset=pager['offset'],order='id desc')
        values['bidders'] = bidders
        values['pager'] = pager
        return request.render("website_auction.product_auction",values )


class website_virtual_productInherit(website_virtual_product):
    def wk_website_auction_product_remove(self,temp):
        sale_order_line=request.env['sale.order.line'].sudo().search(
            [('id', '=', temp),('virtual_source','=','wk_website_auction')]
        )
        if sale_order_line:
            auction_ids=request.env['wk.website.auction'].search([
                ('winner_id','=',request.website._get_website_partner().id),
                ('order_id','=',sale_order_line.order_id.id),
                ('state','in',['complete','finish']),
            ])
            if auction_ids:
                for auction_obj in auction_ids:
                    auction_obj.order_id=None
                    auction_obj.action_complete_auction()#='complete'
        return sale_order_line.unlink()
