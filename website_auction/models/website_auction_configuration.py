# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#	See LICENSE file for full copyright and licensing details.
#
##########################################################################

from odoo import api, fields, models
from odoo.addons.website_auction.models.website_auction import name_list,notify_list

class WkWebsiteAuction(models.Model):

	_inherit = 'wk.website.auction'

	@api.model
	def get_auction_config_settings_vals(self):
		res = {}
		auction_config_values = self.env['website.auction.config.settings'].sudo().search(
			[('website_id', '!=', False)], limit=1)
		if auction_config_values:
			res = {

				'publish_total_bids' : auction_config_values.default_publish_total_bids,
				'publish_info_link' : auction_config_values.default_publish_info_link,
				'publish_subscribe_link' : auction_config_values.default_publish_subscribe_link,
				'publish_start_date' : auction_config_values.default_publish_start_date,
				'publish_end_date' : auction_config_values.default_publish_end_date,
				'publish_extend_date' : auction_config_values.default_publish_extend_date,
				'publish_intial_price' : auction_config_values.default_publish_intial_price,
				'publish_current_price' : auction_config_values.default_publish_current_price,
				'publish_simple_bid' : auction_config_values.default_publish_simple_bid,
				'publish_auto_bid' : auction_config_values.default_publish_auto_bid,
				'publish_next_bid' : auction_config_values.default_publish_next_bid,
				'publish_user_highest_bid' : auction_config_values.default_publish_user_highest_bid,
				'publish_user_auto_bid' : auction_config_values.default_publish_user_auto_bid,
				'publish_auction_complete' : auction_config_values.default_publish_auction_complete,
				'auction_complete_msz' : auction_config_values.default_auction_complete_msz,
				'publish_auction_close' : auction_config_values.default_publish_auction_close,
				'auction_close_msz' : auction_config_values.default_auction_close_msz,
				'publish_login_first' : auction_config_values.default_publish_login_first,
				'publish_login_first_msz' : auction_config_values.default_publish_login_first_msz,
				'auction_bid_submitted' : auction_config_values.default_auction_bid_submitted,
				'auction_bid_submitted_msz' : auction_config_values.default_auction_bid_submitted_msz,
				'publish_unexpected_error' : auction_config_values.default_publish_unexpected_error,
				'publish_unexpected_error_msz' : auction_config_values.default_publish_unexpected_error_msz,
				'publish_min_bid_error' : auction_config_values.default_publish_min_bid_error,
				'publish_min_bid_error_msz' : auction_config_values.default_publish_min_bid_error_msz,
				'publish_min_autobid_error' : auction_config_values.default_publish_min_autobid_error,
				'publish_min_autobid_error_msz' : auction_config_values.default_publish_min_autobid_error_msz,
				'publish_bid_subscribe' : auction_config_values.default_publish_bid_subscribe,
				'publish_bid_subscribe_msz' : auction_config_values.default_publish_bid_subscribe_msz,
				'publish_bid_unsubscribe' : auction_config_values.default_publish_bid_unsubscribe,
				'publish_bid_unsubscribe_msz' : auction_config_values.default_publish_bid_unsubscribe_msz,
				'publish_bidders_name' : auction_config_values.default_publish_bidders_name,
				'publish_bid_record' : auction_config_values.default_publish_bid_record,
				'publish_winner_name' : auction_config_values.default_publish_winner_name,



				'buynow_option' : auction_config_values.default_buynow_option,
				'notify_s_auction_running' : auction_config_values.default_notify_s_auction_running,
				'notify_s_auction_extended' : auction_config_values.default_notify_s_auction_extended,
				'notify_s_auction_closed' : auction_config_values.default_notify_s_auction_closed,
				'notify_s_auction_completed' : auction_config_values.default_notify_s_auction_completed,
				'notify_s_new_bid' : auction_config_values.default_notify_s_new_bid,
				'notify_before_expire' : auction_config_values.default_notify_before_expire,
				'notify_before' : auction_config_values.default_notify_before,
				'notify_time_uom' : auction_config_values.default_notify_time_uom,
				'notify_w_auction_completed' : auction_config_values.default_notify_w_auction_completed,
				'notify_l_auction_completed' : auction_config_values.default_notify_l_auction_completed,
				'notify_ab_bid_placed' : auction_config_values.default_notify_ab_bid_placed,
				'notify_ab_bid_overbid' : auction_config_values.default_notify_ab_bid_overbid,
			}
		else:
			res = {
				'publish_total_bids' : 1,
				'publish_info_link' : 1,
				'publish_subscribe_link' : 1,
				'publish_start_date' : 1,
				'publish_end_date' : 1,
				'publish_extend_date' : 1,
				'publish_intial_price' : 1,
				'publish_current_price' : 1,
				'publish_simple_bid' : 1,
				'publish_auto_bid' : 1,
				'publish_next_bid' : 1,
				'publish_user_highest_bid' : 1,
				'publish_user_auto_bid' : 1,
				'publish_auction_complete' : 1,
				'auction_complete_msz' : 'Auction has been Finished on this Product.',
				'publish_auction_close' : 1,
				'auction_close_msz' : 'Auction has been Closed on this Product.',
				'publish_login_first' : 1,
				'publish_login_first_msz' : 'Please Login First.',
				'auction_bid_submitted' : 1,
				'auction_bid_submitted_msz' : 'You bid had been successfully submitted.',
				'publish_unexpected_error' : 1,
				'publish_unexpected_error_msz' : 'Something Wrong happen ,Please Try again.',
				'publish_min_bid_error' : 1,
				'publish_min_bid_error_msz' : 'Bid Amount is less than next minimum acceptable bid amount.',
				'publish_min_autobid_error' : 1,
				'publish_min_autobid_error_msz' : 'Auto Bid Amount is less than Next Minimum Acceptable Auto Bid Amount. Please make higher Amount of Auto Bid.',
				'publish_bid_subscribe' : 1,
				'publish_bid_subscribe_msz' : 'Notification For Auction Subscribed.',
				'publish_bid_unsubscribe' : 1,
				'publish_bid_unsubscribe_msz' : 'Notification For Auction Un-Subscribed.',
				'publish_bidders_name' : 'cross',
				'publish_bid_record' : 10,
				'publish_winner_name' : 'cross',
				'buynow_option' : 1,
				'notify_s_auction_running' : 1,
				'notify_s_auction_extended' : 1,
				'notify_s_auction_closed' : 1,
				'notify_s_auction_completed' : 1,
				'notify_s_new_bid' : 1,
				'notify_before_expire' : 1,
				'notify_before' : 10,
				'notify_time_uom' : '60',
				'notify_w_auction_completed' : 1,
				'notify_l_auction_completed' : 1,
				'notify_ab_bid_placed' : 1,
				'notify_ab_bid_overbid' : 1,
			}
		return res

	buynow_option = fields.Boolean(string='Provide BuyNow Option',
								help="Provide BuyNow Option On Auction Product",
								default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('buynow_option'))

	################### Notify Subscriber #######################
	notify_s_auction_running = fields.Boolean(string='Bidding Start',
								 help='Notify  Subscriber On Auction Set To Run/Bidding Start',
								 default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_s_auction_running'))
	notify_s_auction_extended = fields.Boolean(string='Auction Extended',
		 						help='Notify  Subscriber On Auction Extended',
								default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_s_auction_extended'))
	notify_s_auction_closed = fields.Boolean(string='Auction Closed',
								help='Notify  Subscriber On Auction Closed',
								default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_s_auction_closed'))
	notify_s_auction_completed = fields.Boolean(string='Auction Finished',
	                            help="Notify  Subscriber On Auction Finished" ,
								default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_s_auction_completed'))
	notify_s_new_bid = fields.Boolean(string='New Bid Placed',
								help='Notify  Subscriber On New Bid Placed',
								default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_s_new_bid'))
	################### Notify Admin ###########################
	notify_before_expire = fields.Boolean(string='Enable Expire Notification',
								help="Notify  Admin On Auction Reach it End Date",
								default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_before_expire'))
	notify_before = fields.Integer(string='Notify Admin Before',
								default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_before'))
	notify_time_uom = fields.Selection(selection=[('3600','hours'),('60','minutes'),('1','seconds')],
	                            default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_time_uom'))

	expire_note_send = fields.Boolean(string='Notification Send', default=1)
	################### Notify Result ########################
	notify_w_auction_completed = fields.Boolean(string='Notify Auction Result To Winner',
	                        help="Notify  Winner On Auction Finished",default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_w_auction_completed'))
	notify_l_auction_completed = fields.Boolean(string='Notify Auction Result To Loser',
	                        help="Notify  Loser On Auction Finished",default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_l_auction_completed'))

	##################### Auction Bidder ###########################
	notify_ab_bid_placed = fields.Boolean(string='Bid Placed on Your Behalf',default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_ab_bid_placed'))
	notify_ab_bid_overbid = fields.Boolean(string='An overbid Placed by SomeOne',default= lambda self: self.env['wk.website.auction'].get_auction_config_settings_vals().get('notify_ab_bid_overbid'))
