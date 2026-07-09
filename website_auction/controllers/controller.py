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
from odoo.addons.website_sale.controllers.main import WebsiteSale, TableCompute
from odoo.addons.website_virtual_product.controllers.main import website_virtual_product
from odoo.addons.website_auction.models.website_auction_exception import *
from odoo.tools import lazy
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.http_routing.models.ir_http import slug
import datetime


import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

from odoo.addons.payment.controllers import portal as payment_portal



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
    def product_on_auction(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0
            
        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        website = request.env['website'].get_current_website()
        website_domain = website.website_domain()
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = website.shop_ppg or 20

        ppr = website.shop_ppr or 4
        
        request_args = request.httprequest.args
        attrib_list = request_args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        keep = QueryURL('/products-on-auction', **self._shop_get_query_url_kwargs(category and int(category), search, min_price, max_price, **post))

        now = datetime.datetime.timestamp(datetime.datetime.now())
        pricelist = website.pricelist_id
        if 'website_sale_pricelist_time' in request.session:
            # Check if we need to refresh the cached pricelist
            pricelist_save_time = request.session['website_sale_pricelist_time']
            if pricelist_save_time < now - 60*60:
                request.session.pop('website_sale_current_pl', None)
                website.invalidate_recordset(['pricelist_id'])
                pricelist = website.pricelist_id
                request.session['website_sale_pricelist_time'] = now
                request.session['website_sale_current_pl'] = pricelist.id
        else:
            request.session['website_sale_pricelist_time'] = now
            request.session['website_sale_current_pl'] = pricelist.id

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            company_currency = website.company_id.currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency, website.currency_id, request.website.company_id, fields.Date.today())
        else:
            conversion_rate = 1

        url = "/products-on-auction"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list

        options = self._get_search_options(
            category=category,
            attrib_values=attrib_values,
            pricelist=pricelist,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            **post
        )
        live = True
        website.sudo().auction_default_sort = "live"
        if post.get("auction"):
            live =  post.get("auction") == "live"
            if live:
                website.sudo().auction_default_sort = "live"
            else:
                website.sudo().auction_default_sort = "upcoming"
                
                
        request.update_context(**{"auction":True,"live":live})
        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(attrib_set, options, post, search, website)

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            # TODO Find an alternative way to obtain the domain through the search metadata.
            Product = request.env['product.template'].with_context(bin_size=True)
            # domain = self._get_search_domain(search, category, attrib_values)
            domain = []

            # This is ~4 times more efficient than a search for the cheapest and most expensive products
            query = Product._where_calc(domain)
            Product._apply_ir_rules(query, 'read')
            from_clause, where_clause, where_params = query.get_sql()
            query = f"""
                SELECT COALESCE(MIN(list_price), 0) * {conversion_rate}, COALESCE(MAX(list_price), 0) * {conversion_rate}
                  FROM {from_clause}
                 WHERE {where_clause}
            """
            request.env.cr.execute(query, where_params)
            available_min_price, available_max_price = request.env.cr.fetchone()

            if min_price or max_price:
                # The if/else condition in the min_price / max_price value assignment
                # tackles the case where we switch to a list of products with different
                # available min / max prices than the ones set in the previous page.
                # In order to have logical results and not yield empty product lists, the
                # price filter is set to their respective available prices when the specified
                # min exceeds the max, and / or the specified max is lower than the available min.
                if min_price:
                    min_price = min_price if min_price <= available_max_price else available_min_price
                    post['min_price'] = min_price
                if max_price:
                    max_price = max_price if max_price >= available_min_price else available_max_price
                    post['max_price'] = max_price

        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search(
                [('product_tmpl_ids', 'in', search_product.ids)] + website_domain
            ).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = lazy(lambda: Category.search(categs_domain))

        if category:
            url = "/shop/category/%s" % slug(category)

        pager = website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset:offset + ppg]
        
        

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            attributes = lazy(lambda: ProductAttribute.search([
                ('product_tmpl_ids', 'in', search_product.ids),
                ('visibility', '=', 'visible'),
            ]))
        else:
            attributes = lazy(lambda: ProductAttribute.browse(attributes_ids))

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'
            request.session['website_sale_shop_layout_mode'] = layout_mode

        products_prices = lazy(lambda: products._get_sales_prices(pricelist))
        fiscal_position_sudo = website.fiscal_position_id.sudo()
        products_prices = lazy(lambda: products._get_sales_prices(pricelist, fiscal_position_sudo))

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'fiscal_position': fiscal_position_sudo,
            'add_qty': add_qty,
            'products': products,
            'search_product': search_product,
            'search_count': product_count,  # common for all searchbox
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            'products_prices': products_prices,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
            'float_round': tools.float_round,
        }
        if filter_by_price_enabled:
            values['min_price'] = min_price or available_min_price
            values['max_price'] = max_price or available_max_price
            values['available_min_price'] = tools.float_round(available_min_price, 2)
            values['available_max_price'] = tools.float_round(available_max_price, 2)
        if category:
            values['main_object'] = category
        values.update(self._get_additional_shop_values(values))

        return request.render("website_auction.product_on_auction", values)


    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True,csrf=False)
    def confirm_order(self, **post):
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection


        order._onchange_partner_shipping_id()
        order.order_line._compute_tax_id()
        request.session['sale_last_order_id'] = order.id
        request.website.sale_get_order(update_pricelist=False)
        extra_step = request.env.ref('website_sale.extra_info_option').sudo()
        if extra_step.active:
            return request.redirect("/shop/extra_info")

        return request.redirect("/shop/payment")

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        r = super(WebsiteSale, self).product(product, category, search, **kwargs)
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
        post['bid_offer'] = round(request.website.pricelist_id.currency_id._convert(float(post.get('bid_offer')),auction_obj.currency_id,request.env.company,datetime.datetime.now()))
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
        order = request.website.sale_get_order(force_create=1)
        # res = request.env['website.virtual.product'].sudo().add_virtual_product(
        #     order_id=order.id,
        #     product_id=auction_obj.product_id,
        #     product_price=auction_obj.buynow_price,
        #     virtual_source='wk_website_auction',
        # )
        price_unit = auction_obj.product_id.currency_id._convert(auction_obj.buynow_price,request.website.pricelist_id.currency_id,request.env.company,fields.datetime.now())
        values = {
            'price_unit':price_unit,
            'virtual_source':'wk_website_auction',
            'is_virtual':True,
            'auction_product_direct_buy':True
            }
        response = order._cart_update(product_id=auction_obj.product_id.id, line_id=None, add_qty=1, set_qty=1, **post)
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
            order = request.website.sale_get_order(force_create=1)
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
