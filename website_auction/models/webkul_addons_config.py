# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

class WebkulWebsiteAddons(models.TransientModel):
    _inherit = 'res.config.settings'

    def get_auction_config_view(self):
        auction_config_ids = self.env['website.auction.config.settings'].search([])
        imd = self.env['ir.model.data']
        action = self.env.ref('website_auction.action_website_auction_configuration')
        list_view_id = imd._xmlid_to_res_id('website_auction.view_website_auction_config_settings_tree')
        form_view_id = imd._xmlid_to_res_id('website_auction.view_website_auction_config_settings_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'list'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(auction_config_ids) == 0:
            result['views'] = [(form_view_id, 'form')]
        if len(auction_config_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = auction_config_ids[0].id
        if len(auction_config_ids) > 1:
            result['views'] = [(form_view_id, 'form')]
            for auc in auction_config_ids:
                if auc.website_id:
                    result['res_id'] = auc.id
                    break
        return result
