# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError

name_list=[('full','Full name'),('cross','Crossed name')]
notify_list=[('last','Only Last'),('all','ALL Expect Current Bidder')]

class WebsiteAuctionConfigSettings(models.Model):
	_name = 'website.auction.config.settings'
	_description = "Website Auction Configuration"

	###################### Auction Info  #################################

	def _default_website(self):
		return self.env['website'].search([], limit=1)

	name= fields.Char(string="Nme", default="Auction Configuration")

	website_id = fields.Many2one('website', string="website", default=_default_website, required=True)

	default_publish_total_bids = fields.Boolean(string='Total Bids',
								help="Publish Total Bids  On Auction Product" ,
								related= "website_id.publish_total_bids", readonly=False)
	default_publish_info_link = fields.Boolean(string='Auction Details Link',
								help="Publish Auction More Info Link  On Auction Product" ,
								related= "website_id.publish_info_link", readonly=False)
	default_publish_subscribe_link = fields.Boolean(string='Subscribe Link',
								help="Publish Auction Subscribe Link  On Auction Product" ,
								related= "website_id.publish_subscribe_link", readonly=False)
	default_publish_start_date = fields.Boolean(string='Starts Date',
								help="Publish Auction Starts Date  On Auction Product" ,
								related= "website_id.publish_start_date", readonly=False)
	default_publish_end_date = fields.Boolean(string='Ends Date',
								help="Publish Auction Time Left  On Auction Product" ,
								related= "website_id.publish_end_date", readonly=False)
	default_publish_extend_date = fields.Boolean(string='Extend Date',
								help="Publish Extend Date  On Auction Product" ,
								related= "website_id.publish_extend_date", readonly=False)
	default_publish_intial_price = fields.Boolean(string='Initial Price',
								help="Publish Initial Price On  Auction Product" ,
								related= "website_id.publish_intial_price", readonly=False)
	default_publish_current_price = fields.Boolean(string='Current Price',
								help="Publish Current Price/Bid Amount On  Auction Product" ,
								related= "website_id.publish_current_price", readonly=False)
	default_publish_simple_bid = fields.Boolean(string='Simple Bid Option',
								help="Allow Bidder to bid as Simple Bid " ,
								related= "website_id.publish_simple_bid", readonly=False)
	default_publish_auto_bid = fields.Boolean(string='Auto Bid Option',
								help="Allow Bidder to bid as  Auto Bid " ,
								related= "website_id.publish_auto_bid", readonly=False)
	default_publish_next_bid = fields.Boolean(string='Next Bid Amount',
								help="Publish Next Minimum Bid On  Auction " ,
								related= "website_id.publish_next_bid", readonly=False)
	default_publish_user_highest_bid = fields.Boolean(string='User Highest Bid Amount',
								help="Show Highest Bid  made by  Bidders to them-self " ,
								related= "website_id.publish_user_highest_bid", readonly=False)
	default_publish_user_auto_bid = fields.Boolean(string='User Auto Bid Amount',
								help="Show Auto Bid made by  Auto Bidder to them-self " ,
								related= "website_id.publish_user_auto_bid", readonly=False)
	remove_cart_derect_buy_bid_product = fields.Boolean(string="Remove Direct Buy Bid Product")
	###################### Message for complete cancel close  #################################
	default_publish_auction_complete = fields.Boolean(string='Auction Complete',
								help="Show Auction Complete Message " ,
								related= "website_id.publish_auction_complete", readonly=False)
	default_auction_complete_msz = fields.Text(string='Auction Complete Message',
								help="Auction Complete Message Content ",
								related= "website_id.auction_complete_msz", translate=True, readonly=False)
	default_publish_auction_close = fields.Boolean(string='Auction Close',
								help="Show Auction Close Message " ,
								related= "website_id.publish_user_auto_bid", readonly=False)
	default_auction_close_msz = fields.Text(string='Auction Close  Message',
								help="Auction Close Message Content ",
								related= "website_id.auction_close_msz",
								translate=True, readonly=False)

	default_publish_login_first = fields.Boolean(string='Login First',
								help="Show Login First Message if user is not login ." ,
								related= "website_id.publish_login_first", readonly=False)
	default_publish_login_first_msz = fields.Text(string='Login First Message',
								default='Please Login First.', translate=True,
								related= "website_id.publish_login_first_msz", readonly=False)
	default_auction_bid_submitted = fields.Boolean(string='Bid Placed ',
								help="Show Bid Place Message on Bid Placed. " ,
								related= "website_id.auction_bid_submitted", readonly=False)

	default_auction_bid_submitted_msz = fields.Text(string='Bid Submitted Message',
								default='Your bid had been successfully submitted.', translate=True,
								related="website_id.auction_bid_submitted_msz", readonly=False)
	default_publish_unexpected_error = fields.Boolean(string='Unexpected Error',
								help="Show Unexpected Error Message on unknown Error. " ,
								related="website_id.publish_unexpected_error", readonly=False)
	default_publish_unexpected_error_msz = fields.Text(string='Unexpected Error Message',
								translate=True,
								related="website_id.publish_unexpected_error_msz", readonly=False)

	default_publish_min_bid_error = fields.Boolean(string='Minimum Bid Error',
								help="Show Minimum Bid Error Message if bid offer is less than next minimum bid. " ,
								related="website_id.publish_min_bid_error", readonly=False)
	default_publish_min_bid_error_msz = fields.Text(string='Minimum Bid Error Message',
								related="website_id.publish_min_bid_error_msz", translate=True, readonly=False)

	default_publish_min_autobid_error = fields.Boolean(string='Minimum Auto Bid Error',
								help="Show Minimum Auto Bid Error Message if Auto bid offer is less than next minimum auto bid. " ,
								related="website_id.publish_min_autobid_error", readonly=False)
	default_publish_min_autobid_error_msz = fields.Text(string='Minimum Auto Bid Message', translate=True,
								related="website_id.publish_min_autobid_error_msz", readonly=False)

	#################### Auction Result  ############################
	default_publish_bidders_name=fields.Selection(
								help="""Select "Full Name" if your want to publish full name of Bidders\n
								Select "Crossed name" if your want to publish Crossed name (Admin-> **m**) of Bidders\n
								Select Blank if your not want to publish name of Bidders  """,

								string = "Bidders ",related="website_id.publish_bidders_name", translate=True, readonly=False)

	default_publish_bid_record = fields.Integer(string='Publish Bid Records',related="website_id.publish_bid_record",required=1, readonly=False)

	default_publish_winner_name=fields.Selection(
								help="""Select "Full Name" if your want to publish full name of Winner\n
								Select "Crossed name" if your want to publish Crossed name (Admin-> **m**) of Winner\n
								Select Blank if your not want to publish name of Winner  """,

								string = "Winner ",related="website_id.publish_winner_name", translate=True, readonly=False)

	#################### Notification on Bid  ####################
	# notify_on_bid=fields.Selection(selection=notify_list,
	# 				string = "Send Bid Notification To",default='all')
	# notify_auction_loser = fields.Boolean(string='Notify loser on auction complete',default=1)
	##################### Auction Default ##########################
	default_buynow_option = fields.Boolean(string='Enable BuyNow Option',
								help="Provide BuyNow Option On Auction Product" ,
								 default=1)
	default_notify_before_expire = fields.Boolean(string='Enable Expire Notification',
								help="Notify  Admin On Auction Reach it End Date",
								default=1)
	default_notify_before = fields.Integer(string='Notify Admin Before',
								default=10)
	default_notify_time_uom = fields.Selection(selection=[('3600','hours'),('60','minutes'),('1','seconds')],
								 default='60')
	################### Auction Subscriber ############################
	default_notify_s_auction_running = fields.Boolean(string='Bidding Start',
									help='Notify  Subscriber On Auction Set To Run/Bidding Start',
									default=1)
	default_notify_s_auction_extended = fields.Boolean(string='Auction Extended',
									help='Notify  Subscriber On Auction Extended',
									default=1)
	default_notify_s_auction_closed = fields.Boolean(string='Auction Closed',
									help='Notify  Subscriber On Auction Closed',
									default=1)
	default_notify_s_new_bid = fields.Boolean(string='New Bid Placed',
									help='Notify  Subscriber On New Bid Placed',
									default=1)
	default_notify_s_auction_completed = fields.Boolean(string='Auction Finished',
									help="Notify Auction Subscriber On Auction Finished" ,
									default=1)
	################### Auction Result ########################
	default_notify_w_auction_completed = fields.Boolean(string='Notify Auction Result To Winner',
									help="Notify Auction Winner On Auction Finished",
									default=1)
	default_notify_l_auction_completed = fields.Boolean(string='Notify Auction Result To Loser',
									help="Notify Auction Loser On Auction Finished",default=1)
	##################### Auction Bidder ###########################
	default_notify_ab_bid_placed = fields.Boolean(string='Bid Placed on Your Behalf',
									default=1)
	default_notify_ab_bid_overbid = fields.Boolean(string='An overbid Placed by SomeOne',
									default=1)

	default_publish_bid_subscribe = fields.Boolean(string='Subscribed Message',
								default=1,
								related="website_id.publish_bid_subscribe", readonly=False)
	default_publish_bid_unsubscribe = fields.Boolean(string='Un-Subscribed Message',
								default=1,
								related="website_id.publish_bid_unsubscribe", readonly=False)
	default_publish_bid_subscribe_msz = fields.Text(string='Bid Placed on Your Behalf Message',
									default='Notification For Auction Subscribed.', translate=True,
									related="website_id.publish_bid_subscribe_msz", readonly=False)
	default_publish_bid_unsubscribe_msz = fields.Text(string='An overbid Placed by SomeOne',
									default='Notification For Auction Un-Subscribed.', translate=True,
									related="website_id.publish_bid_unsubscribe_msz", readonly=False)

	@api.constrains('default_publish_auto_bid', 'default_publish_simple_bid')
	def simple_bid(self):
		if not self.default_publish_auto_bid and not self.default_publish_simple_bid:

			raise UserError("Atleast On Bid option is mandatory")
