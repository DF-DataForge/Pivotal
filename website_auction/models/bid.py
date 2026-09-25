# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import  ValidationError
import uuid


class WkBidIncrementRule(models.Model):

    _name = 'wk.bid.increment.rule'
    _description = 'Auction Increment Rule'
    name = fields.Char(
        required=1
    )
    active = fields.Boolean(
        default=1
    )
    from_price = fields.Float(
        required=1
    )
    to_price = fields.Float(
        required=1
    )
    increment_by = fields.Float(
        required=1
    )

    @api.constrains('from_price','to_price','increment_by')
    def _check_point_range(self):
        if self.increment_by<= 0.0:
            raise ValidationError(
                _('Error ! Increment by should be greater than zero.'))
        if self.from_price <= 0.0:
            raise ValidationError(
                _("From price should be positive."))
        if self.from_price == self.to_price:
            raise ValidationError(
                _("From price and To price must be different."))
        elif self.from_price > self.to_price:
            raise ValidationError(_(
                "From price must be smaller  than  To price."))
        else:
            price_rule_ids = self.search([('id', '!=', self.id)])
            for price_rule_id in price_rule_ids:
                if (self.from_price <= price_rule_id.from_price and self.to_price >= price_rule_id.to_price) or \
                        (self.from_price >= price_rule_id.from_price and self.to_price <= price_rule_id.to_price) or\
                        (self.from_price >= price_rule_id.from_price and self.from_price <= price_rule_id.to_price):
                    raise ValidationError(
                        _("This Price range is already assign to another price Rule !"))


class WkAuctionSubscriber(models.Model):

    _name = 'wk.auction.subscriber'
    _description = 'Auction Subscriber '
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Subscriber',
        required=1
    )
    name = fields.Char(
        related='partner_id.name',
        required=1
    )
    email = fields.Char(
        related='partner_id.email',
        required=1
    )
    wk_auction_fk = fields.Many2one(
        comodel_name='wk.website.auction',
        string='Auction',
        ondelete="cascade",
        required=1
    )
    deactivate_token =fields.Char(
        string='Deactivate Token'
    )
    subscribe = fields.Boolean(
        string='Subscribe',
        default=1
    )

    def get_admin_email(self):
        return self.env['ir.mail_server'].search([('active','=',True)],limit=1).smtp_user

    @api.constrains('partner_id', 'wk_auction_fk')
    def _unique_subscriber(self):
        domain = [
            ('subscribe','=',True),
            ('wk_auction_fk','=',self.wk_auction_fk.id)
        ]
        subscribers=self.search(domain)
        for subscriber in subscribers:
            if (subscriber.id !=self.id
                and subscriber.partner_id==self.partner_id):
                raise ValidationError(
                    "A Subscriber already exists with the same partner id .\n**A single subscriber can't subscribe an Auction more than one times!!**"
                )


    @api.model_create_multi
    def create(self, vals_list):
        results = super(WkAuctionSubscriber, self).create(vals_list)
        for result in results:
            result.deactivate_token = str(uuid.uuid4())+str(result.id)
        return results

    @api.depends('subscribe')
    def change_deactivate_token(self):
        self.deactivate_token = str(uuid.uuid4())+str(self.id)


class WkAuctionBidder(models.Model):
    _name = 'wk.auction.bidder'
    _description = 'Auction Bidder'

    @api.model
    def _get_status_list(self):
        vals = [
            ('inactive', 'Inactive'),
            ('active', 'Active'),
            ('loss', 'Lost'),
            ('win', 'Won'),
            ('finish', 'SoldOut')
        ]
        return vals

    def get_admin_email(self):
        return self.env['ir.mail_server'].search([('active', '=', True)], limit=1).smtp_user

    @api.model
    def _get_bid_type_list(self):
        return [
            ('simple', 'Simple Bid'),
            ('auto', 'Auto Bid')
        ]


    @api.model
    def get_deactivate_token(self):
        token = ''
        subscriber = self.auction_fk.subscriber_ids.filtered(
            lambda subscriber: subscriber.partner_id == self.partner_id
        )
        if subscriber:
            token = subscriber.deactivate_token
        return token


    partner_id = fields.Many2one(
        'res.partner',
        string='Bidder',
        required=True
     )
    name = fields.Char(
        related='partner_id.name',
        required=1
    )
    bid_offer = fields.Float(
        string='Bid Offer',
        required=1
    )
    date = fields.Datetime(
        string='Offer DateTime',
        help='Datetime when user made the Last Bids',
        required=True,
        default=fields.Datetime.now
    )
    bid_type = fields.Selection(
        string='Bid Type',
        selection=_get_bid_type_list,
        default='simple',
        required=True
    )
    state = fields.Selection(
        string='Status',
        selection=lambda self: self._get_status_list(),
        default='active',
        required=True
    )
    auction_fk = fields.Many2one(
        'wk.website.auction',
        string='Auction',
        ondelete="cascade"
    )
