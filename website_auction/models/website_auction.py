# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
from lxml import etree
from dateutil.relativedelta import relativedelta
from datetime import date, datetime,timedelta
from pytz import timezone
import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.website_auction.models.website_auction_exception import *
from odoo.exceptions import  ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
DateTimeFormat = '%Y-%m-%d %H:%M:%S'
StartEndForamt = "%dth-%b-%Y, %I:%M%p"
DateTimeWeekFormat = "%A %dth-%b-%Y,%I:%M%p"


_logger = logging.getLogger(__name__)
name_list=[
    ('full','Full name'),
    ('cross','Crossed name')
]
notify_list=[
    ('last','Only Last'),
    ('all','ALL Expect Current Bidder')
]


class WkWebsiteAuction(models.Model):

    @api.model
    def _get_status_list(self):
        status= [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('running', 'Running'),
            ('extend', 'Extended'),
            ('close', 'Closed'),
            ('complete', 'Finished'),
            ('finish', 'SoldOut')
        ]
        return status

    @api.model
    def _get_extend_by_list(self):
        return [
            ('1', '1 days'),
            ('2', '2 days'),
            ('3', '3 days'),
            ('4', '4 days'),
            ('5', '5 days'),
            ('custom_date','Custom Date')
        ]

    _name = "wk.website.auction"
    _order = 'sequence'
    _description = 'Auction'

    @api.constrains('buynow_price')
    def product_price_change(self):
        self.product_id.lst_price = self.buynow_price

    def get_admin_email(self):
        return self.env['ir.mail_server'].search([('active','=',True)],limit=1).smtp_user

    @api.model
    def get_default_end_date(self):
        def_end_date =  fields.Datetime.to_string(
            fields.Datetime.from_string(
                fields.Datetime.now()
            )
            + relativedelta(minutes = 15)
        )
        return def_end_date

    @api.model
    def get_default_start_date(self):
        def_start_date = fields.Datetime.to_string(
            fields.Datetime.from_string(
                fields.Datetime.now()
            )
            + relativedelta(minutes = 5)
        )
        return def_start_date

    @api.depends('start_date', 'end_date')
    def _set_total_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                result = ''
                start = datetime.strptime(str(rec.start_date), DateTimeFormat)
                end = datetime.strptime(str(rec.end_date), DateTimeFormat)
                diff = relativedelta(end, start)
                result = """{day} d: {hour} h: {minute} m: {second} s""".format(
                    day=diff.days and diff.days or 0, hour=diff.hours
                     and diff.hours or 0,
                    minute=diff.minutes and diff.minutes or 0, second=diff.seconds
                    and diff.seconds or 0)
                rec.total_duration = result

    name = fields.Char(
        string="Auction Name",
        required=True
    )
    active = fields.Boolean(
        default = 1
    )
    sequence = fields.Integer(
        string = 'Sequence',
        default=100,
        copy =False
    )
    product_sale = fields.Boolean(
        string = 'Product Sale',
        default = 0,
        copy =False
    )
    state = fields.Selection(
        string="Status",
        selection=_get_status_list,
        default='draft',
        required=True
    )
    intial_price = fields.Float(
        string='Initial Price',
        help='Initial Price At the time Starting',
        required=True,
        default=100
    )
    reserve_price = fields.Float(
        string='Reserve Price',
         help='Reserve/Minimum price for auction at which it can be declared as complete.',
         required=True,
         default=700
     )
    buynow_price = fields.Float(
        string='BuyNow Price',
        help='Price at which an auction Product can sell in parallel.',
        default=1000
    )
    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id')
    start_date = fields.Datetime(
        string='Start DateTime',
         help='Datetime when auction starts',
         required=True,
         copy=False,
         default = get_default_start_date,
    )
    end_date = fields.Datetime(
        string='End DateTime',
        help='Datetime when auction ends',
        required=True,
        copy=False,
        default = get_default_end_date,
    )

    ###################################################################################
    extend_by = fields.Selection(
        string='Extend By',
        selection=_get_extend_by_list,
        copy=False,
    )
    extend_date = fields.Datetime(
        string='Extended Duration',
        help='Extra Allocated Time For Auction',
        copy=False,
    )
    ###################################################################################
    total_duration = fields.Char(
        string='Total Duration',
        copy=False,
        compute = _set_total_duration
    )
    bid_increment_rule_ids = fields.Many2many(
        string='Bid Increment Rules',
       comodel_name='wk.bid.increment.rule',
       relation='wk_website_auction_wk_bid_increment_rule_relation',
       column1="wk_website_auction", column2="wk_bid_increment_rule"
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Template'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )

    product_name = fields.Char(
        string='Auction Product Name'
    )
    product_description_sale = fields.Text(
        string='Auction Product Description'
    )
    product_image = fields.Binary(
        string='Auction Product Image'
    )
    winner_id = fields.Many2one(
        'res.partner',
        string='Winner' ,
        copy=False,
        compute='_get_current_winner',
        store="True"
    )
    current_price = fields.Float(
        string="Current Bid",
        copy=False,
        compute='_get_current_winner'
    )
    total_bids = fields.Integer(
        string='Total Bids',
        copy=False,
        compute='_get_total_bids'
    )
    bidder_ids = fields.One2many(
        string='Bidders',
        comodel_name='wk.auction.bidder',
        inverse_name='auction_fk',
        copy=False
    )
    subscriber_ids = fields.One2many(
        string='Subscribers',
        comodel_name='wk.auction.subscriber',
        inverse_name='wk_auction_fk',
        copy=False
    )
    order_id = fields.Many2one(
        string='Order Ref:',
        comodel_name='sale.order',
        copy=False
    )

    _sql_constraints = [
        ('non_zero_buynow_price','check(buynow_price > 0)','Error ! Buy Now Price should be greater than zero.'),
        ('non_zero_intial_price','check(intial_price > 0)','Error ! Initial Price should be greater than zero.'),
        ('non_zero_reserve_price','check(reserve_price > 0)','Error ! Reserve Price should be greater than zero.'),
    ]

    def _compute_currency_id(self):
        self.currency_id = self.env.user.company_id.currency_id.id

    @api.model
    def wk_activate_website_view(self):
        # 'website_sale.products_description' was removed in Odoo 17.2+;
        # product tile descriptions are handled by shop design options now.
        products_description = self.env.ref(
            'website_sale.products_description', raise_if_not_found=False)
        if products_description:
            products_description.write(dict(active=1))
        return True

    @api.model
    def get_bid_related_entity(self):
        auto_bidder=self.get_auto_bidder()
        next_bid = self._get_next_bid()
        return auto_bidder,next_bid

    @api.model
    def _validate_bid(self,bid_type,bid_offer):
        result = dict(message='',err_type=None)
        auto_bidder,next_bid =self.get_bid_related_entity()
        # if bid_type=='simple' and bid_offer  < next_bid :
        #     result['message'] = 'Your Bid %s Not Satisfying the  Minimum Bid Amount Criteria .\n It should be at-least %s.' % (bid_offer,next_bid)
        #     raise MinimumBidException(result['message'])
        # elif bid_type=='auto':
        #     auto_bid_offer = auto_bidder and auto_bidder.bid_offer or next_bid
        #     auto_bid_increment = auto_bid_offer+self._get_next_autobid_increment()
            # if  auto_bid_offer>=bid_offer:
            #     result['message'] = "You auto bid amount range [{0}] is already opt by some other bidder.\nPlease Increase your auto bid range to a large extent.".format(bid_offer)
            # if  bid_offer < auto_bid_increment:
            #     result['message'] = 'Your Bid Not Satisfying the  Minimum Auto Bid Amount Criteria .\n It should be at-least %s' % (next_bid)
            #     raise MinimumBidException(result['message'])

    @api.model
    def new_auto_bider(self,partner_id):
        auto_bidder,next_bid =self.get_bid_related_entity()
        if auto_bidder:
            # If auto_bidder found and autobidder partner_id not equal to partner_id(paramater) else it return True
            return auto_bidder.partner_id.id!=partner_id
        return True

    @api.model
    def inactive_auto_bid(self,bid_type,bid_offer,partner_id):
            auto_bidder,next_bid =self.get_bid_related_entity()
            a_bid_offer=auto_bidder.bid_offer

            if self.new_auto_bider(partner_id):
                if bid_type=='auto' and  a_bid_offer > self.current_price:
                    self.create_autobidder_bid(a_bid_offer)
                elif bid_type=='simple' and  a_bid_offer > self.current_price:
                    self.create_autobidder_bid(a_bid_offer)
                self.notify_auction_auto_bidder(auto_bidder.partner_id)
            auto_bidder.write({'state':'inactive'})

    @api.model
    def wk_create_bid(self,bid_type,bid_offer,partner_id):
        auto_bidder,next_bid =self.get_bid_related_entity()
        s_vals = dict(bid_type=bid_type,bid_offer=bid_offer,partner_id=partner_id,auction_fk=self.id)
        res=self.env['wk.auction.bidder'].create(s_vals)
        self.create_unique_subscriber(partner_id)#Create Subscriber
        if self._context.get('auctual_bid_type','simple')!='auto':
            self.notify_auction_bidder_subscriber(res.partner_id)#NOtify Bidder and subscriber
        return res

    @api.model
    def create_autobidder_bid(self,bid_offer=None):
        auto_bidder=self.get_auto_bidder()
        offer =  bid_offer or (auto_bidder and auto_bidder.bid_offer)
        if auto_bidder and bid_offer:
            if bid_offer > auto_bidder.bid_offer:
                res=self.wk_create_bid('simple',auto_bidder.bid_offer,auto_bidder.partner_id.id)
                if res:self.notify_auction_auto_bidder(auto_bidder.partner_id,about='auto_bid_place')
                auto_bidder.write({'state':'inactive'})
            else:
                res=self.wk_create_bid('simple',bid_offer or auto_bidder.bid_offer,auto_bidder.partner_id.id)
                if res:self.notify_auction_auto_bidder(auto_bidder.partner_id,about='auto_bid_place')
                if res.bid_offer == auto_bidder.bid_offer: #newly added
                    auto_bidder.write({'state':'inactive'})
            return res

    @api.model
    def create_bid(self,bid_type,bid_offer,partner_id):
        validate = self._validate_bid(bid_type,bid_offer)
        multiple_auto_bid = None
        prev_auto_bidder,next_bid =self.get_bid_related_entity()
        if prev_auto_bidder and (prev_auto_bidder.bid_offer <= bid_offer):
                self.inactive_auto_bid(bid_type,bid_offer,partner_id)
        result=self.with_context(
            auctual_bid_type=bid_type
            ).wk_create_bid(
            bid_type = bid_type,
            bid_offer = bid_offer,
            partner_id = partner_id
        )
        auto_bidder,next_bid =self.get_bid_related_entity()

        if auto_bidder:
            last_auto_biider = [rec for rec in auto_bidder]
        
##########################################################################################
            if len(auto_bidder) > 1:
                multiple_auto_bid = True
                highest_bidder_id = max(auto_bidder,key=lambda x : x['bid_offer'])
                last_auto_biider.remove(highest_bidder_id)
                last_bidder = max(last_auto_biider,key=lambda x : x['bid_offer'])
                for bidder in auto_bidder:
                    if bidder.id != highest_bidder_id.id:
                        bidder.bid_type = 'simple'

                auto_bidder = highest_bidder_id   
                result.bid_type = 'simple'

        if result.bid_type=='simple':
            if auto_bidder:
                bid_difference = auto_bidder.bid_offer - result.bid_offer
            if auto_bidder and self.new_auto_bider(partner_id) and auto_bidder.bid_offer >= next_bid:
                if multiple_auto_bid:
                    self.create_autobidder_bid(last_bidder.bid_offer+self._get_next_autobid_increment())
                else:
                    self.create_autobidder_bid(next_bid)
            elif auto_bidder and self.new_auto_bider(partner_id) and bid_difference <= 10: # Newly added
                self.wk_create_bid('simple', auto_bidder.bid_offer , auto_bidder.partner_id.id)
                auto_bidder.write({'state':'inactive'})


        elif result.bid_type=='auto' and auto_bidder and auto_bidder.bid_offer >= next_bid:
            res = False
            if auto_bidder:
                bid_difference = auto_bidder.bid_offer - result.bid_offer
            if prev_auto_bidder and prev_auto_bidder.partner_id != auto_bidder.partner_id:
                res=self.wk_create_bid('simple',next_bid,auto_bidder.partner_id.id)
            if not prev_auto_bidder:
                res=self.wk_create_bid('simple',next_bid,auto_bidder.partner_id.id)
                                
            if res:self.notify_auction_auto_bidder(auto_bidder.partner_id,about='auto_bid_place')
                
        elif result.bid_type=='auto' and auto_bidder and prev_auto_bidder.bid_offer < auto_bidder.bid_offer and auto_bidder.bid_offer < next_bid:
            res = False
            if auto_bidder:
                auto_bid_difference =  next_bid -  auto_bidder.bid_offer
            if auto_bid_difference <= 10 and auto_bid_difference != 0:
                res = self.wk_create_bid('simple', auto_bidder.bid_offer , auto_bidder.partner_id.id)
                auto_bidder.write({'state':'inactive'})

        elif auto_bidder.bid_type == 'auto'  and auto_bidder.bid_offer == prev_auto_bidder.bid_offer: # Newly added 
            auto_bidder.write({'state':'inactive'})

#########################################################################################

    @api.model
    def cross_name(self,partner_id,_for='bidders'):
        name = partner_id.name
        if self.env['website']._get_website_partner().id == partner_id.id:
            return name
        if (_for=='bidders' and self.env['wk.website.auction'].get_auction_config_settings_vals().get('publish_bidders_name') == 'cross'):
            wk_name,l=name,len(name)
            if l>2:astric="*"*(l//2);wk_name=astric+wk_name[l//2:-l//2+1]+astric;return wk_name
            else: return "*"*(l)
        if  (_for == 'winner' and self.env['wk.website.auction'].get_auction_config_settings_vals().get('publish_winner_name') =='cross') :
            wk_name,l=name,len(name)
            if l>2:astric="*"*(l//2);wk_name=astric+wk_name[l//2:-l//2+1]+astric;return wk_name
            else: return "*"*(l)
        return name

    @api.model
    def get_config(self):
        return  self.get_auction_config_settings_vals()

    @api.model
    def synchronize_auction_state_cron(self):
        auction_ids=self.env['wk.website.auction'].search([('state','in',['confirmed','running','extend'])])
        if auction_ids:auction_ids.mapped(lambda auction: auction.set_auction_state())



    @api.onchange('product_sale')
    def check_product_sale(self):
        if self.product_sale and self.state not in ['finish','close']:
            raise ValidationError(
                "Product Sale can't enable , auction must be in finish or close state .")

    @api.onchange('order_id')
    def check_order_id(self):
        if self.product_id and self.order_id and self.product_id not in map(lambda x: x.product_id, self.order_id.order_line):
            raise ValidationError(
                'Auction Product Not Found in the Selected Sale Order.')

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        product_variant_ids = []
        if self.product_tmpl_id and self.product_tmpl_id.product_variant_ids:
            product_variant_ids = self.product_tmpl_id.product_variant_ids.ids
            if len(product_variant_ids):
                self.product_id =product_variant_ids[0]
        return {'domain':{'product_id': [('id', 'in', product_variant_ids)]}}


    @api.onchange('product_id')
    def check_product_id(self):
        if self.product_id:
            auctions = self.env['wk.website.auction'].search(
                [('product_id', '=', self.product_id.id)])

            self.product_name=self.product_id.name
            self.product_description_sale=self.product_id.description_sale
            self.product_image=self.product_id.image_1920
            self.name='Auction For '+self.product_tmpl_id.name


    @api.constrains('state','product_tmpl_id')
    def _check_auction_state(self):
        if len(self.bid_increment_rule_ids)==0:
            raise ValidationError("""Error ! Please assign bid increment rule for auction.""")
        if self.state in ['close','complete','finish']:
            self.sequence = 1000
        domain = [('state','not in',['close','complete','finish']),
        ('product_tmpl_id','=',self.product_tmpl_id.id)]
        auctions=self.search(domain)
        for auction in auctions:
            if auction.id !=self.id :
                if self.state not in ['confirmed']:
                    if auction.state!='close':
                        raise ValidationError("""A auction is already assign for this product.
                        \n**Set the previous auction to  close !!**""")



    @api.constrains('state', 'start_date','end_date','extend_date')
    def _check_auction_date(self):

        current = datetime.now().replace(microsecond=0)
        start = datetime.strptime(str(self.start_date), DateTimeFormat)
        end = datetime.strptime(str(self.end_date), DateTimeFormat)
        if self.state in ['draft','confirmed']:
            if current>start :
                raise ValidationError("Auction Start Time should  greater than Current Time.")
            elif current>end :
                raise ValidationError("Auction End Time should  greater than Current Time.")
            elif start>end :
                raise ValidationError("Auction End Time should  greater than Auction Start Time.")

        elif self.extend_by and self.state in ['draft','confirmed','running']:
            extend=datetime.strptime(str(self.extend_date), DateTimeFormat)
            if  current>extend:
                raise ValidationError("Auction Extend Time should  greater than Current Time.")
            elif start>extend:
                raise ValidationError("Auction Extend Time should  greater than Auction Start Time.")
            elif end>extend:
                raise ValidationError("Auction Extend Time should  greater than Auction End Time.")

    @api.onchange('extend_by')
    def _set_extend_by(self):
        self.expire_note_send=False
        if self.end_date and self.extend_by!='custom_date':
            self.extend_date=datetime.strptime(
                            str(self.end_date), DateTimeFormat)+timedelta(days=int(self.extend_by))

    @api.onchange('extend_date')
    def _set_extend_date(self):
        self.expire_note_send=False



    @api.model
    def _get_next_bid(self):
        for rule in self.bid_increment_rule_ids:
            # if self.current_price == 0:
            #     return self.current_price + rule.increment_by
            if rule.from_price <= self.current_price  and rule.to_price >= self.current_price :
                return self.current_price + rule.increment_by
        if  self.bid_increment_rule_ids and self.current_price>=self.intial_price:
            return self.current_price+self.bid_increment_rule_ids[-1].increment_by
        return self.current_price >= self.intial_price and self.current_price+1 or self.intial_price


    @api.model
    def _get_next_autobid_increment(self):
        next_bid= self._get_next_bid()
        if self.current_price == 0:
            increment_rules_ids = self.bid_increment_rule_ids.ids
            increment_rule = self.env['wk.bid.increment.rule'].browse(increment_rules_ids[0])
            return increment_rule.increment_by

        return (next_bid-self.current_price) and (next_bid-self.current_price) or 1


    def _get_total_bids(self):
        for rec  in self:
            rec.total_bids = rec.bidder_ids and len(
            rec.bidder_ids.filtered(
            lambda bidder: bidder.bid_type!='auto'
            and bidder.state!='inactive')
            ) or 0

    @api.depends('bidder_ids')
    def _get_max_bidders(self):    
        for rec in self:
            bidders = rec.bidder_ids.filtered(
                lambda bidder:  bidder.bid_type != 'auto' and bidder.state != 'inactive'
            )
            bidder_dict = {bidder.partner_id: bidder.bid_offer for bidder in bidders}
            offer_bidder_dict = {bidder: bidder.bid_offer for bidder in bidders}
            if offer_bidder_dict:
                max_bid = max(offer_bidder_dict.values())
                max_bid_ids = [key for key,value in offer_bidder_dict.items() if value == max_bid]
                return max_bid_ids 
        
    @api.depends('bidder_ids')
    def _get_max_bidder(self):    
        for rec in self:
            bidders = rec.bidder_ids.filtered(
                lambda bidder:  bidder.bid_type != 'auto' and bidder.state != 'inactive'
            )
            offer_bidder_dict = {bidder: bidder.bid_offer for bidder in bidders}
            max_bid = max(offer_bidder_dict.values())
            return max_bid 
        

    @api.depends('bidder_ids')
    def _get_earliest_max_bidders(self, check_max_bidder):    
        _check_max_bidder = [bidder.id for bidder in check_max_bidder]
        earliest_max_bid = self.env['wk.auction.bidder'].browse(_check_max_bidder)
        earliest_bidder_dict = {bidder: bidder.create_date for bidder in earliest_max_bid}
        earliest_min_bid = min(earliest_bidder_dict.values())
        earliest_max_bid_ids = [key for key,value in earliest_bidder_dict.items() if value == earliest_min_bid]
        return earliest_max_bid_ids
      
    @api.depends('bidder_ids')
    def _get_earliest_auto_bidders(self):  
        max_bid = self._get_max_bidder()
        for rec in self:
            auto_bidders = rec.bidder_ids.filtered(
                lambda bidder:  bidder.bid_type == 'auto' and bidder.bid_offer == max_bid
            )
            return auto_bidders
        
    @api.depends('bidder_ids')
    def _check_early_auto_bid(self):  
        pass

    @api.depends('bidder_ids')
    def _get_current_winner(self):
        for rec in self:
            bidders = rec.bidder_ids.filtered(
                lambda bidder:  bidder.bid_type!='auto' and bidder.state != 'inactive'
            )
            if bidders:
                bidder_dict = {bidder.partner_id: bidder.bid_offer for bidder in bidders}              
                check_max_bidder = self._get_max_bidders()
                if check_max_bidder and len(check_max_bidder) > 1:
                    earliest_max_bidder = self._get_earliest_max_bidders(check_max_bidder)
                    if earliest_max_bidder and len(earliest_max_bidder) > 1:
                        earliest_auto_bidder = self._get_earliest_auto_bidders()
                        if earliest_auto_bidder and len(earliest_auto_bidder) > 1:
                            check_auto_bidder = self._check_early_auto_bid()
                            if check_auto_bidder and len(check_auto_bidder) > 1:
                                pass
                            else:
                                winner = check_auto_bidder[0].partner_id
                                rec.current_price = check_auto_bidder[0].bid_offer
                                rec.winner_id = winner
                        else:
                            winner = earliest_auto_bidder[0].partner_id
                            rec.current_price = earliest_auto_bidder[0].bid_offer
                            rec.winner_id = winner

                    else:
                        winner = earliest_max_bidder[0].partner_id
                        rec.current_price = earliest_max_bidder[0].bid_offer
                        rec.winner_id = winner

                else:
                    winner = max(bidder_dict, key=bidder_dict.get)
                    rec.current_price = bidder_dict.get(winner)
                    rec.winner_id = winner
            else:
                rec.winner_id = None
                rec.current_price = 0.00


    @api.model
    def create_unique_subscriber(self,partner_id):
        domain = [('wk_auction_fk','=',self.id),('partner_id','=',partner_id)]
        subscriber= self.env['wk.auction.subscriber'].sudo().search(domain,limit=1)
        if  not subscriber  :
            vals = {
                'partner_id':partner_id,
                'wk_auction_fk':self.id,
            }
            self.env['wk.auction.subscriber'].sudo().create(vals)
        elif subscriber and not subscriber.subscribe :
            subscriber.subscribe=True

    @api.model
    def set_auction_state(self):
        if self.state == 'draft':
            return
        current = datetime.now().replace(microsecond=0)
        start = datetime.strptime(str(self.start_date), DateTimeFormat)
        end = datetime.strptime(str(self.end_date), DateTimeFormat)
        extend =self.extend_by and  self.extend_date and datetime.strptime(
            str(self.extend_date), DateTimeFormat) or end
        wk_end = extend > end and extend or end
        if extend and self.notify_before_expire and (not self.expire_note_send) and current < wk_end and self.state in ['running', 'extend'] and (extend - current).total_seconds() / int(self.notify_time_uom) < self.notify_before:
            self.notify_admin_auction_need_to_extend()
        if (current >= start) and (current < wk_end) and (self.state != 'running') and (self.state in ['confirmed']):
            return self.action_running_auction()
        elif (current >= end) and (current < wk_end) and (self.state != 'extend') and (self.state in ['running']):
            return self.action_extend_auction()
        elif (current >= wk_end) and self.state not in ['complete',  'close', 'finish']:
            self.create_autobidder_bid()
            if self.reserve_price <= self.current_price:
                return self.action_complete_auction()
            else:
                return self.action_close_auction()



    def action_draft_auction(self):
        for record in self:
            record.state = 'draft'
            record.notify_auction_state()
        return True


    def action_confirmed_auction(self):
        if self.filtered(lambda auction: auction.state != 'draft'):
            raise ValidationError('Only draft auction can set to confirm.')
        for record in self.filtered(lambda auction: auction.state == 'draft'):
            record.state = 'confirmed'
            record.notify_auction_state()
        return True

    def action_running_auction(self):
        for record in self:
            record.state = 'running'
            record.notify_auction_state()
        return True

    def action_extend_auction(self):
        if self.filtered(lambda auction: not auction.extend_by):
            raise ValidationError('Select the extend duration.')
        if self.filtered(lambda auction: auction.state != 'running'):
            raise ValidationError('Only running auction can extend.')
        for record in self:
            record.state = 'extend'
            record.notify_auction_state()
        return True

    def action_close_auction(self):
        for record in self:
            record.state = 'close'
            record.notify_auction_state()
        return True

    # def action_complete_auction(self):
    #     self.ensure_one()
    #     self.state = 'complete'
    #     if self.current_price < self.reserve_price:
    #         raise ValidationError(
    #             'Max bid amount should at least satisfy the reserve price .\n Either extend the auction duration  or close the auction.')
    #     bidders = self.env['wk.auction.bidder'].search(
    #         [('auction_fk', '=', self.id)], order='bid_offer desc')
    #     for bidder in bidders:
    #         bidder.state = (bidder.bid_offer >=
    #                         self.current_price) and bidder.bid_type == 'simple'  and 'win' or 'loss'
    #     # for bidder in bidder.filtered(lambda b:b.bidtype == 'auto'):
    #     self.notify_auction_state()
    #     return True

    def action_complete_auction(self):
        self.ensure_one()
        self.state = 'complete'
        if self.current_price < self.reserve_price:
            raise ValidationError(
                'Max bid amount should at least satisfy the reserve price .\n Either extend the auction duration  or close the auction.')
        final_bidders = self.env['wk.auction.bidder'].search(
            [('auction_fk', '=', self.id)], order='bid_offer desc')
        check_max_bidder = self._get_max_bidders()
        if check_max_bidder and len(check_max_bidder) > 1:
            earliest_max_bidder = self._get_earliest_max_bidders(check_max_bidder)
            if earliest_max_bidder and len(earliest_max_bidder) > 1:
                earliest_auto_bidder = self._get_earliest_auto_bidders()

                if earliest_auto_bidder and len(earliest_auto_bidder) > 1:
                    check_auto_bidder = self._check_early_auto_bid()
                    if check_auto_bidder and len(check_auto_bidder) > 1:
                        pass
                    else:
                        for bidders in final_bidders:
                            if bidders == check_auto_bidder:
                                bidders.state = 'win'
                            else:
                                bidders.state = 'loss'
                else:
                    for bidders in final_bidders:
                        if bidders == earliest_auto_bidder:
                            bidders.state = 'win'
                        else:
                            bidders.state = 'loss'
            else:
                for bidders in final_bidders:
                    if bidders == earliest_max_bidder[0]:
                        bidders.state = 'win'
                    else:
                        bidders.state = 'loss'
        else:
            bidder_dict = {bidder: bidder.bid_offer for bidder in final_bidders if bidder.bid_type == 'simple'}
            winner = max(bidder_dict, key=bidder_dict.get)
            for bidder in final_bidders:
                if bidder == winner:
                    bidder.state = 'win'
                else:
                    bidder.state = 'loss'


        # if max_bid_ids and len(max_bid_ids) > 1:
        #     auto_bids = self.bidder_ids.filtered(
        #         lambda bidder:  bidder.bid_type == 'auto' and bidder.bid_offer == max_bid
        #     )
        #     if auto_bids and len(auto_bids) >1:
        #         pass

        #     else:
        #         bidders_ids = self.env['wk.auction.bidder'].browse(max_bid_ids)
        #         for bidder in bidders_ids:
        #             if bidder.partner_id.id == auto_bids.partner_id.id and bidder.bid_offer == auto_bids.bid_offer:
        #                 winner_bidder = bidder
        #                 for bidder in final_bidders:
        #                     if bidder == winner_bidder:
        #                         bidder.state = 'win'
        #                     else:
        #                         bidder.state = 'loss'

        self.notify_auction_state()
        return True


    def action_finish_auction(self):
        if not self.order_id:
            raise ValidationError(
                'Please Attach the Order Reference with Auction to mark it Sold Out.')
        self.state = 'finish'
        self.sequence = self.sequence-1
        bidder = self.env['wk.auction.bidder'].search(
            [('auction_fk', '=', self.id), ('bid_offer', '=', self.current_price)], limit=1)
        if bidder:
            bidder.state = 'finish'
        # self.product_id.website_published=False
        # self.product_tmpl_id.website_published=False
        self.notify_auction_state()
        return True

    def get_auction_week_left(self, wk_timezone=None):
        result = False
        if self and self.end_date:
            current = datetime.now().replace(microsecond=0)
            end = datetime.strptime(str(self.end_date), DateTimeFormat)
            extend = self.extend_date and datetime.strptime(
                str(self.extend_date), DateTimeFormat) or end
            week_left = extend > end and extend or end
            now_pacific = week_left.replace(tzinfo=timezone('UTC'))
            week = now_pacific.astimezone(
                timezone(self._context.get('tz') or "UTC"))
            result = week.strftime(DateTimeWeekFormat)
            if not self._context.get('tz'):
                result = week_left.strftime('%Y-%m-%d %H:%M:%S')
        return result

    def get_auction_start_week_left(self,  wk_timezone=None):
        local_tz = timezone(self._context.get('tz') or 'UTC')
        result = False
        if self and self.end_date:
            start = datetime.strptime(
                str(self.start_date), DateTimeFormat)
            now_pacific = start.replace(tzinfo=timezone('UTC'))
            week = now_pacific.astimezone(
                timezone(self._context.get('tz') or "UTC"))
            result = week.strftime(DateTimeWeekFormat)
            if not self._context.get('tz'):
                result = start.strftime('%Y-%m-%d %H:%M:%S')
        return result

    def get_publish_fields(self):
        config = self.get_config() or {}
        vals = {'auction_running_extend': self.state in ['running', 'extend'] and True or False,
                'auction_yet_not_running': self.state == 'confirmed' and True or False,
                'auction_yet_not_finish': self.state not in ['draft', 'confirmed', 'finish','close'],
                'auction_start_week_left': self.get_auction_start_week_left(),
                'auction_week_left': self.get_auction_week_left(),
                'auction_start_date': self.get_auction_start_date(),
                'auction_end_date': self.get_auction_end_date(),
                'wk_auction': self,
                'login_user_is_winner': self.login_user_is_winner(),
                'login_user_is_losser': self.login_user_is_losser(),
                'login_user_have_auto_bid':  self.login_user_is_auto_bidder(),
                'login_user_was_auto_bidder': self.login_user_was_auto_bidder(),
                'test_start_date': datetime.strptime(str(self.start_date), DEFAULT_SERVER_DATETIME_FORMAT),
                'test_end_date': datetime.strptime(str(self.end_date), DEFAULT_SERVER_DATETIME_FORMAT)

                }
        vals.update(config)
        return vals

    def get_base_url(self):
        return self.env['ir.config_parameter'].get_param('web.base.url')

    def get_product_url(self):
        return ('{0}/product/auction/{1}'.format(self.get_base_url(), self.id))

    def notify_auction_state(self):
        if self.state not in ['draft']:
            if hasattr(self, 'notify_auction_in_%s_state' % self.state):
                return getattr(self, 'notify_auction_in_%s_state' % self.state)()

    def get_auction_start_date(self):
        start_date = datetime.strptime(str(self.start_date), DateTimeFormat)
        now_pacific = start_date.replace(tzinfo=timezone('UTC')).astimezone(
            timezone(self._context.get('tz') or "UTC"))
        return now_pacific.strftime(StartEndForamt)

    def get_auction_end_date(self):
        end_date = datetime.strptime(str(self.end_date), DateTimeFormat)
        if self.state == 'extend'and self.extend_date and self.end_date < self.extend_date:
            end_date = datetime.strptime(str(self.extend_date), DateTimeFormat)
        now_pacific = end_date.replace(tzinfo=timezone('UTC')).astimezone(
            timezone(self._context.get('tz') or "UTC"))
        return now_pacific.strftime(StartEndForamt)

    def email_get_auction_end_date(self):
        end_date = self.end_date
        if self.state == 'extend'and self.extend_date and self.end_date < self.extend_date:
            end_date = self.extend_date
        return end_date

    def get_active_subscriber_partner(self):
        return self.subscriber_ids.filtered('subscribe').mapped('partner_id')

    def get_active_subscriber(self):
        return self.subscriber_ids.filtered('subscribe')


    def get_bid_record(self):
        bid_record=[]
        bidders = self.bidder_ids.filtered(lambda bidder: bidder.bid_type != 'auto'
                                           )
        if bidders:
            bid_record= bidders.sorted(lambda b: b.bid_offer, reverse=True)
        if self.publish_bid_record:bid_record= bid_record[:self.publish_bid_record]
        return bid_record




    def get_auto_bidder(self):
        bidders = self.bidder_ids.filtered(lambda bidder: bidder.bid_type == 'auto'
                                           and bidder.state == 'active'
                                           )
        if bidders:
            return bidders.sorted(lambda b: b.bid_offer, reverse=True)

    def get_unique_bidder_partners(self):
        """return non auto bidder subscribed  """
        unique_non_auto_bidders = self.bidder_ids.mapped('partner_id')
        if self.subscriber_ids:
            unique_non_auto_bidders = self.bidder_ids.filtered(
                lambda bidder: bidder.partner_id in self.get_active_subscriber_partner()).mapped('partner_id')
        if self.get_auto_bidder():
            unique_non_auto_bidders -= self.get_auto_bidder().mapped('partner_id')
        return set(unique_non_auto_bidders)

    def get_subscriber(self):
        """return the non-bidder active subscriber"""
        partner_ids = self.bidder_ids.mapped('partner_id.id')
        return self.get_active_subscriber().filtered(lambda subscriber: subscriber.partner_id.id not in partner_ids)

    def wk_notify_bidder(self, template, partners, notify_auto_bidder=False):
        """
        wk_notify_bidder(template, partners)
            sum(template, partners) -> None

            Send the mail to all the bidder which partner_id received  in partners argument ."""
        try:

            for partner in set(partners):
                vals = [('partner_id', '=', partner.id),
                        ('auction_fk', "=", self.id)]
                if notify_auto_bidder:

                    vals += [('bid_type', '=', 'auto')]
                else:
                    vals += [('bid_type', '=', 'simple')]
                bidder = self.env['wk.auction.bidder'].search(
                    vals, limit=1, order='bid_offer desc')
                res = template.sudo().send_mail(bidder.id, force_send=True)
        except Exception as e:
            _logger.info("Notify Bidder Exception %r------", e)

    def wk_notify_subscriber(self, template):
        try:
            for subscriber in self.get_subscriber():
                res = template.sudo().send_mail(subscriber.id, force_send=True)
        except Exception as e:
            _logger.info("Notify Subscriber Exception %r------", e)

    def notify_auction_in_running_state(self):
        if self.notify_s_auction_running:
            template = self.env.ref(
                'website_auction.notify_bidder_auction_in_running_state', False)
            self.wk_notify_bidder(template, self.get_unique_bidder_partners())
            subscriber_temp = self.env.ref(
                'website_auction.notify_subscriber_auction_in_running_state', False)
            self.wk_notify_subscriber(subscriber_temp)

    def notify_auction_in_extend_state(self):
        if self.notify_s_auction_extended:
            template = self.env.ref(
                'website_auction.notify_bidder_auction_in_extend_state', False)
            self.wk_notify_bidder(template, self.get_unique_bidder_partners())
            subscriber_temp = self.env.ref(
                'website_auction.notify_subscriber_auction_in_extend_state', False)
            self.wk_notify_subscriber(subscriber_temp)

    def notify_auction_in_close_state(self):
        if self.notify_s_auction_closed:
            template = self.env.ref(
                'website_auction.notify_bidder_auction_in_close_state', False)
            self.wk_notify_bidder(template, self.get_unique_bidder_partners())
            subscriber_temp = self.env.ref(
                'website_auction.notify_subscriber_auction_in_close_state', False)
            self.wk_notify_subscriber(subscriber_temp)

    def notify_auction_in_complete_state(self):
        loser_template = self.env.ref(
            'website_auction.notify_auction_losers', False)
        winner_template = self.env.ref(
            'website_auction.notify_auction_winner', False)
        partners = self.get_unique_bidder_partners()
        if self.notify_l_auction_completed:
            partners = list(set(partners) - set(self.winner_id))
            self.wk_notify_bidder(loser_template, partners)
        if self.notify_w_auction_completed:
            self.wk_notify_bidder(winner_template, self.winner_id)
        if self.notify_s_auction_completed:
            subscriber_temp = self.env.ref(
                'website_auction.notify_subscriber_auction_in_complete_state', False)
            self.wk_notify_subscriber(subscriber_temp)

    def notify_admin_auction_need_to_extend(self):
        template = self.env.ref(
            'website_auction.auction_need_to_extend', False)
        try:
            res = template.send_mail(self.id, force_send=True)
            self.expire_note_send = True
        except Exception as e:
            _logger.info("Notify Admin Auction Need To Extend %r------", e)

    def notify_auction_bidder_subscriber(self, bid_partner):
        if self.notify_s_new_bid:
            partners = list(
                set(self.get_unique_bidder_partners()) - set(bid_partner))
            if partners:
                template = self.env.ref(
                    'website_auction.new_bid_has_been_placed_bidder', False)
                self.wk_notify_bidder(template, partners=partners)
            subscriber_temp = self.env.ref(
                'website_auction.new_bid_has_been_placed_subscriber', False)
            self.wk_notify_subscriber(subscriber_temp)

    def notify_auction_auto_bidder(self, partner, about='auto_bid_end'):

        if self.notify_ab_bid_overbid or self.notify_ab_bid_placed:

            if self.notify_ab_bid_overbid and about == 'auto_bid_end':
                template = self.env.ref(
                    'website_auction.notify_auction_auto_bid_end', False)
            elif self.notify_ab_bid_placed and about == 'auto_bid_place':
                template = self.env.ref(
                    'website_auction.notify_auction_auto_bid_place', False)

            if self.get_auto_bidder() and template:
                if self.get_subscriber():
                    partner = self.get_active_subscriber_partner().filtered(
                        lambda partner_id: partner_id == partner)
                self.wk_notify_bidder(
                    template, partner, notify_auto_bidder=True)

    def login_user_is_winner(self):
        return self.env['website']._get_website_partner().id == self.winner_id.id

    def login_user_is_losser(self):
        return not self.login_user_is_winner() and self.env['website']._get_partner_heighest_bid(self)

    def login_user_is_auto_bidder(self):
        res = self.bidder_ids.filtered(lambda bidder: bidder.partner_id.id ==
                                       self.env['website']._get_website_partner().id and bidder.bid_type == 'auto' and bidder.state == 'active')
        return res and res[0] or res

    def login_user_was_auto_bidder(self):
        res = self.bidder_ids.filtered(lambda bidder: bidder.partner_id.id == self.env['website']._get_website_partner().id
                                       and bidder.bid_type == 'auto').sorted(lambda b: b.bid_offer, reverse=True)
        return res and res[0] or res
