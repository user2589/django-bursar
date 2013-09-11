# -*- coding: utf-8 -*-
import re
from django.conf import settings

from django import forms
from django.utils.translation import ugettext as _

import utils

from common_utils.decorators import JSONP

@JSONP
def get_card_type(request):
    card_no = re.sub('\D', '', request.GET.get('card_no', ''))
    if not card_no:
        return {'error' : unicode(forms.Field.default_error_messages['required'])}

    if not utils.is_mod10(card_no):
        return {'error' : _('Invalid card number')}

    card_type = utils.get_cardtype(card_no)

    if card_type is None:
        return {'error' : _('Invalid card number')}

    return {'card_type': card_type}
