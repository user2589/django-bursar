# -*- coding: utf-8 -*-
import base64
import urllib2
from lxml import etree

from bursar import models as bursar_models
from bursar import settings as bursar_settings
from bursar.gateway import base

from django.template import loader as template_loader

from . import PROCESSOR_KEY, models, errors

PAYMENT_METHOD_CODES = {
    # credit cards
    'AMEX'          : 'AMEX-SSL', #international
    'VISA'          : 'VISA-SSL', #international, credit/debit/electron
    'MASTERCARD'    : 'ECMC-SSL', #international
    'carte bancaire': 'CB-SSL',         #France
    'Carte Bleue'   : 'CARTEBLEUE-SSL', #France
    'DC'            : 'DINERS-SSL',#international
    'Laser Card'    : 'LASER-SSL', #Ireland
    'DISCOVER'      : 'DISCOVER-SSL',#US
    'JCB'           : 'JCB-SSL',  #international, Japan
    'Dankort'       : 'DANKORT-SSL',#international

    #debit cards
    'Rabobank'      : 'RABO-',          #Netherlands
    'DirectBetalen' : 'DIRECTBETALEN',  #Netherlands
    'ING Homepay'   : 'HOMEPAY-SSL',    #Belgium
    #Solo & Maestro - Depending upon the issuer policy, either the issuer number or the start date must be included in the paymentDetails.
    'Solo'          : 'SOLO_GB-SSL',    #UK.
    'MAESTRO'       : 'MAESTRO-SSL',
    'WWW-Bon'       : 'ICCHEQUE-SSL',   #Netherlands. Internet voucher, 2b discontinued
    'Nordea Bank'   : 'SOLO-SSL ',      #Finland
    #'Nordea Bank'   : 'EBETALNING-SSL',  #Sweden
    'Paybox'        : 'PAYBOX-SSL',     #Germany, Austria, UK, Spain. Payment method using mobile phone
    'Elektronisches Lastschriftverfahren' : 'ELV-SSL', #Germany
}

STATUSES = {
    'AUTHORISED': 'A',
    'IN_PROCESS_AUTHORISED': 'A', #treat as authorized
    'REFUSED'   : 'R',
    'CANCELLED' : 'C',
    'EXPIRED'   : 'EX',
    'CAPTURED'  : 'CD',
    'IN_PROCESS_CAPTURED'  : 'CD',#treat as captured
    'SETTLED'   : 'S',
    'REFUNDED'  : 'RF',
    'SENT_FOR_REFUND'  : 'RF', #treat as Refunded
    'CHARGED_BACK': 'CB',
    'CHARGEBACK_REVERSED': 'S',
}

def get_first(iterable, default=None):
    if not iterable:
        return default
    try:
        return iterable[0]
    except IndexError:
        return default

def get_amount(amount_node):
    if amount_node is None:
        return None
    try:
        value = int(amount_node.attrib.get('value'))
        exp  = int(amount_node.attrib.get('exponent'))
        return value*(10**-exp)
    except ValueError:
        return None

class PaymentProcessor(base.BasePaymentProcessor):
    key = PROCESSOR_KEY
    require_settings = ('MERCHANT_ID', 'XML_PASSWORD')
    can_authorize = True

    def __init__(self, payment):
        super(PaymentProcessor, self).__init__(payment)
        self.connection = self.settings['SERVICE_URL' if bursar_settings.LIVE else 'TEST_SERVICE_URL']

    def authorize(self, form_data):
        self.log.debug('Authorize request: %s', form_data)
        if not self.payment.transaction_id:
            self.payment.transaction_id = self.settings['PREFIX'] + str(self.payment.id)

        if form_data['card_type'] not in PAYMENT_METHOD_CODES:
            raise errors.WorldpayError('Invalid payment method')

        payment_node = self._acme('worldpay/authorize.xml', {
                'form_data' : form_data,
                'request'   : form_data.get('request'),
                'payment_method'  : PAYMENT_METHOD_CODES[form_data['card_type']],
                'shipping_address': self.payment.purchase.shipping_address,
            }, './orderStatus/payment')

        result = self.parse_payment_node(payment_node)

        if True: #'reason' not in result:
            bursar_models.CreditCardDetail(
                    payment= self.payment,
                    ccv    = form_data['cvc'],
                    card_no= form_data['card_no'],
                    expiry = form_data['expiry'],
                    name   = form_data['name']
                ).save()

        self.log.debug('Authorize result: %s', result)
        return result

    def capture(self, form_data):
        if not self.payment.transaction_id:
            self.payment.transaction_id = self.settings['PREFIX'] + str(self.payment.id)

        raise NotImplementedErorr

    def capture_authorized(self, amount):
        self.log.debug('Capture authorized request: %s, %s', self.payment, amount)

        amount_node = self._acme('worldpay/capture_authorized.xml', {'amount': amount}, './ok/captureReceived/amount')
        captured_amount = get_amount(amount_node)
        if captured_amount is None:
            raise errors.WorldpayError('Invalid amount node in response')

        result = {
            'status' : 'CD',
            'amount' : captured_amount,
        }

        self.log.debug('Capture authorized result: %s', result)
        return result

    def release_authorized(self):
        self.log.debug('Release authorized request: %s', self.payment)
        self._acme('worldpay/release_authorized.xml', None, './ok/cancelReceived')
        return { 'status' : 'C' }

    def refund(self, amount):
        assert(amount <= self.payment.amount)
        self.log.debug('Refund request: %s, %s', self.payment, amount)

        amount_node = self._acme('worldpay/refund.xml', {'amount': amount }, './ok/refundReceived/amount')

        refunded_amount = get_amount(amount_node)
        if not refunded_amount:
            raise errors.WorldpayError('Missing refund amount node in modification response')

        result = {
            'amount' : self.payment.amount - refunded_amount,
        }
        if result['amount'] <= 0:
            result['status'] = 'RF'

        self.log.debug('Refund result: %s', result)
        return result

    def get_payment_status(self):
        self.log.debug('Get status request for payment: %s', self.payment)
        payment_node = self._acme('worldpay/get_status.xml', None, './orderStatus/payment')
        return self.parse_payment_node(payment_node)

    def parse_payment_node(self, payment_node):
        balance_node = get_first(payment_node.xpath('./balance'))
        if balance_node:
            amount_node = get_first(balance_node.xpath('./amount'))
            status_code = balance_node.attrib.get('accountType')
        else:
            amount_node = get_first(payment_node.xpath('./amount'))
            status_code = get_first(payment_node.xpath('./lastEvent/text()'))

        amount = get_amount(amount_node)
        if amount is None:
            raise errors.WorldpayError('Invalid amount node in response')

        if status_code not in STATUSES:
            raise errors.WorldpayError('Invalid payment status received')

        result = {
                'amount' : amount,
                'status' : STATUSES[status_code],
            }

        reason = get_first(payment_node.xpath('./ISO8583ReturnCode/@description'))
        if reason:
            result['reason'] = reason

        return result

    def _acme(self, template, vars, xpath):
        reply_node = self.request_by_template(template, vars)

        main_node = get_first(reply_node.xpath(xpath))
        if main_node is None:
            raise errors.WorldpayError('Missing %s node in response'%xpath)

        return main_node

    def request_by_template(self, template, variables=None):
        """ creates a request basing on template and data passed """
        template_vars = {
                'payment'  : self.payment,
                'currency' : self.settings['CURRENCY'],
                'MERCHANT_ID' : self.settings['MERCHANT_ID'],
            }
        if variables:
            template_vars.update(variables)
        request_text = template_loader.render_to_string(template, template_vars)

        return self.send_post(request_text)

    def send_post(self, request_text):
        """ Helper method to make POST request and return parsed response """
        self.log.debug("About to send a request to worldpay: %(connection)s\n%(content)s"%{'connection':self.connection, 'content':request_text})

        headers = {
                "Authorization" : "Basic %s"%base64.b64encode(":".join([self.settings['MERCHANT_ID'], self.settings['XML_PASSWORD']])),
                "Content-Type": "text/xml; charset=utf-8",
            }
        request = urllib2.Request(self.connection, request_text, headers)

        rqrs = models.RequestResponse(
                request = request_text.encode('utf8'),
                https   = bursar_settings.LIVE,
            )

        result = urllib2.urlopen(request)

        response_text = result.read()
        self.log.debug('Worldpay response: %s', response_text)

        try:
            XML = etree.fromstring(response_text)
        except:
            rqrs.response= response_text
            raise
        else:
            rqrs.response= etree.tostring(XML, pretty_print=True)
        finally:
            if not bursar_settings.LIVE:
                rqrs.save()

        reply_node = get_first(XML.xpath('/paymentService/reply'))
        if reply_node is not None:
            errs = dict((int(node.attrib.get('code')), node.text)
                            for node in reply_node.xpath('./error'))
            if errs:
                raise errors.WorldpayError('Errors in response', errs)
        else:
            raise errors.WorldpayError('Invalid request')

        return reply_node
