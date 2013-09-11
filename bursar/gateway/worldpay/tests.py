# -*- coding: UTF-8 -*-
import datetime

from bursar.tests import make_test_purchase

from . import processor

"""
CVC2 for test scenarios
code, simulated situation, numeric response
blank - NOT SUPPLIED BY SHOPPER - 1
111 - NOT SENT TO ACQUIRER - 2
222 - NO RESPONSE FROM ACQUIRER - 3
333 - NOT CHECKED BY ACQUIRER - 4
444 - FAILED - 5
555 - APPROVED - 6

Cardholder for test:
REFUSED, REFERRED, FRAUD, ERROR

test card numbers:
MAESTRO: 6333333333333333336 or 6759649826438453 (these cards have no issue number but use a start date)
SOLO_GB: 6767676767676767671 (this card has no issue number but uses a start date)
         6767622222222222222 (this card has a one digit issue number)
VISA: 4111111111111111
      4444333322221111
AMEX: 3434 343434 34343 (or 3434 3434 3434 34?)
MasterCard: 5555 5555 5555 4444
            5454 5454 5454 5454
DINERS: 3670 0102 0000 00
DANKORT: 5019 7170 1010 3742
AIRPLUS: 122000000000003
         192000000000008
LASER: 6304900017740292441
CB/CARTEBLEUE: 5555 5555 5555 4444

authorize - > errors, all cases

authorize -> cancel
authorize -> capture (partial) -> cancel
authorize -> capture (full) -> cancel
authorize -> capture (over full amount) [ERROR]-> cancel

capture -> cancel
capture -> refund (partial) -> refund(partial) -> refund(over9k) [ERROR] -> cancel

+ get_status
status_update?OrderCode=DEMO_ORDER123456789&PaymentId=15390&PaymentStatus=AUTHORISED&PaymentAmount=1000&PaymentCurrency=EUR&PaymentMethod=VISA-SSL

"""

class default_request:
    class META:
        REMOTE_ADDR = '194.61.183.122'
        HTTP_ACCEPT = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        HTTP_USER_AGENT = 'Mozilla/5.0 (X11; Linux i686; rv:7.0.1) Gecko/20100101 Firefox/7.0.1'
    class session:
        session_key = '0938209340293842938492348209348'

default_form_data = {
        'name'    : 'John Smith',
        'address' : 'Baker st, 221b',
        'city'    : 'London',
        'zip'     : 'NW1',
        'country' : 'GB',
        'phone'   : '7935-8866',
        'email'   : 'testuser@test.com',
        'card_no' : '4444333322221111',
        'card_type' : 'VISA',
        'expiry'  : datetime.date.today() + datetime.timedelta(days=400),
        'cvc'     : '123',
        'request' : default_request,
    }

class TestGateway(unittest.TestCase):
    def tearUP(self):
        bursar_settings.LIVE = False

    def test_form(self):
        form_data = default_form_data

