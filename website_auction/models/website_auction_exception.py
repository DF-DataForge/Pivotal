# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#	See LICENSE file for full copyright and licensing details.
##########################################################################

from odoo import api, fields, models
from odoo.exceptions import ValidationError
class AuctionStateException(ValidationError):
    pass
class MinimumBidException(ValidationError):
    pass
class AutoBidException(ValidationError):
    pass
