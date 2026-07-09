# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
from . import models
from . import controllers

def pre_init_check(env):
    from odoo.service import common
    from odoo.exceptions import ValidationError
    version_info = common.exp_version()
    server_serie =version_info.get('server_serie')
    if server_serie!='19.0':raise ValidationError('Module support Odoo series 19.0 found {}.'.format(server_serie))
    return True