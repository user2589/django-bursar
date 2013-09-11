# -*- coding: utf-8 -*-
"""
Stores details about the available payment options.
Also stores credit card info in an encrypted format.
"""

from datetime import datetime
from django.conf import settings
from django.db import models
from django.core.cache import cache
from django.utils.translation import ugettext as _

from Crypto.Cipher import Blowfish
import base64
import logging

from bursar import utils
from bursar.errors import GatewayError
from bursar import settings as bursar_settings

log = logging.getLogger('bursar.models')

class PurchaseBase(models.Model):
    """ class all purchase models should inherit from
        Note that Purchase object might not have shipping information (as eg
        for digital products) and might not have billing information (eg Paypal
        or Google Checkout). So, it does not have mandatory fields except .total
    """
    class Meta:
        abstract = True

    @property
    def shipping_address(self):
        """ Interface to get shipping address from your model
            Output:
            {
                'first_name' : 'John',          #optional
                'last_name'  : 'Smith',         #optional
                'street_address1' : 'Baker st, 221b',
                'street_address2' : 'apt 4',    #optional
                'city'       : 'London',
                'state'      : 'Greater London',#optional
                'postal_code': 'NW1',
                'country'    : 'GB',
                'phone'      : '7935-8866',     #optional
            }
            .. or None if not applicable
        """
        return None

    def __iter__(self):
        """  if your Purchase model is a conventional order, with list of items and quantities,
        please make it iterable, eg:
            return self.lineitems.all() # no tax/shipping
        or, by implementing .next() method to add tax/shipping etc
        """
        return iter([])

    @property
    def total(self):
        """ Descendant objects should override this with property """
        raise NotImplementedError('You should define .total property in Purchase model ')

    @property
    def authorizations(self):
        return self.payments.filter(status='A')

    @property
    def captures(self):
        return self.payments.filter(status__in =('CD', 'S'))

    @property
    def authorized_amount(self):
        return reduce(lambda x,y: x+y.amount, self.authorizations, 0)

    @property
    def captured_amount(self):
        return reduce(lambda x,y: x+y.amount, self.captures, 0)

    def authorize(self, method, form_data, amount=None):
        max_amount = self.total - self.captured_amount - self.authorized_amount
        if amount is None:
            amount = max_amount
        elif amount > max_amount:
            pass #in some cases, it is ok
        elif amount <= 0:
            raise ValueError('Invalid amount')

        payment = Payment(method=method, purchase=self, amount=amount)
        return payment.authorize(form_data)

    def capture(self, method, form_data, amount=None):
        max_amount = self.total - self.captured_amount
        if amount is None:
            amount = max_amount
        elif amount > max_amount:
            raise ValueError('Can not capture more than order total')
        elif amount <= 0:
            raise ValueError('Invalid amount')

        amount2capture = amount

        #First, try to capture authorized payments
        for p in self.authorizations:
            if p.capture(min(amount2capture, p.amount)).success:
                amount2capture -= p.amount
                if amount2capture <= 0:
                    return p

        payment = Payment(method=method, purchase=self, amount=amount2capture)
        return payment.capture(form_data)

    def capture_authorized(self, amount=None):
        max_amount = self.authorized_amount
        if amount is None:
            amount = max_amount
        elif amount > max_amount:
            raise ValueError('Can not capture above authorized amount')
        elif amount <= 0:
            raise ValueError('Invalid amount')

        ids = []
        amount2capture = amount
        for p in self.authorizations:
            if p.capture_authorized(min(amount2capture, p.amount)).success:
                amount2capture -= p.amount
                ids.append(p.id)
                if amount2capture <= 0:
                    break
        return self.payments.filter(id__in=ids)

    def cancel(self):
        ids = [p.id for p in self.authorizations|self.captures if not p.cancel().success ]
        return self.payments.filter(id__in=ids)

    def refund(self, amount=None):
        max_refund = self.captured_amount
        if amount is None:
            amount = max_refund
        elif amount > max_refund:
            raise ValueError('Can not refund above charged amount')
        elif amount < 0:
            raise ValueError('Can not capture negative amount')

        ids = []
        amount2refund = amount
        for p in self.captures:
            amount2refund -= p.amount - p.refund(min(amount2refund, p.amount)).amount
            ids.append(p.id)
            if amount2refund <= 0:
                break
        return self.payments.filter(id__in=ids)

    def auto_authorize(self, method, form_data):
        amount = self.total - self.captured_amount - self.authorized_amount
        if amount > 0:
            return self.authorize(method, form_data, amount)
        return None

    def auto_capture(self, method, form_data):
        """ depending on purchase amount, issues (partial) refund or captures necessary amount """
        captured_amount  = self.captured_amount
        authorized_amount= self.authorized_amount
        if self.total <= captured_amount: # captured too much, issue refund
            [p.cancel() for p in self.authorizations]
            return self.refund(captured_amount - self.total)
        elif captured_amount < self.total <= authorized_amount:
            p = self.capture_authorized(self.total-captured_amount)
            [p.cancel() for p in self.authorizations]
            return p

        # self.total > (captured_amount + authorized_amount):
        self.capture_authorized()
        return self.capture(method, form_data, self.total - self.captured_amount)

"""
General payment status diagram:

   NEW (aka PendingPayment in original bursar; this is not a real status)
    |
<auth request> -> REFUSED or ERROR
    |
AUTHORIZED ---> CANCELLED
    |     \
CAPTURED    ---> EXPIRED
    |    \
SETTLED ------> REFUNDED
       \
         ---> CHARGED_BACK

Please keep in mind:
 - some gateways don't have Authorized, Cancelled, or Expired state(s)
 - authorized payment can be captured only once, at amount up to authorized.
 - some processors support change of authorized amount, but it is quite uncommon
 - authorized payment can be cancelled only all at once. No way to decrease amount
 - .. except partial capture
 - Partial refund possible on captured and settled payments, until full amount refunded

"""

states = (
    ('',   'New'),
    ('A',  'Authorized'),
    ('R',  'Refused'),
    ('E',  'Error'),
    ('C',  'Cancelled'),
    ('EX', 'Authorization expired'),
    ('CD', 'Captured'),
    ('S',  'Settled'),
    ('RF', 'Refunded'),
    ('CB', 'Charged back'),
)

class Payment(models.Model):
    """ A payment attempt on a purchase. """
    time_stamp = models.DateTimeField(_("timestamp"), db_index=True, editable=False, auto_now_add=True)
    method = models.CharField(_("Payment method"), choices=bursar_settings.ACTIVE_GATEWAYS, max_length=25)
    amount = models.FloatField(_("amount"), default=0)
    status = models.CharField(_("Payment status"), db_index=True, choices=states, max_length=2, default='')
    details = models.CharField(_("Payment details"), max_length=255, blank=True, default="")
    transaction_id = models.CharField(_("Transaction ID"), max_length=45, blank=True, null=True)
    reason = models.CharField(_('Reason'),  max_length=255, default="")

    purchase = models.ForeignKey(bursar_settings.PURCHASE_MODEL, related_name="payments")

    def __init__(self, *args, **kwargs):
        super(Payment, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u"Payment #%(id)s: amount=%(amount)s (%(state)s)" % {
                'id'    :self.id,
                'amount':self.amount,
                'state' :self.status_name,
            }

    def _update(self, data_dict):
        changes = []
        for property, new_value in data_dict.items():
            if hasattr(self, property):
                old_value = getattr(self, property)
                if old_value != new_value:
                    setattr(self, property, new_value)
                    if property == 'status':
                        changes.append((property, dict(states)[old_value], dict(states)[new_value]))
                    else:
                        changes.append((property, old_value, new_value))
        if changes:
            self.save()
            self.notes.create(payment=self, note="\n".join(("%s: %s => %s"%change for change in changes))).save()

        return self

    _processor = None
    @property
    def processor(self):
        if self._processor is None:
            try:
                processor_class = utils.get_processor(self.method)
            except:
                raise ImportError('You have to specify method for Payment instance')
            self._processor = processor_class(self)
        return self._processor

    @property
    def status_name(self):
        return dict(states).get(self.status)

    @property
    def success(self):
        return self.status in ('A', 'CD', 'S')

    def authorize(self, form_data):
        if self.amount != 0 and not self.status: #authorization available only for new payments
            if not self.id:
                self.save()
            return self._update(self.processor.authorize(form_data))
        if self.amount < 0:
            raise ValueError('Can not authorize negative amount')
        return self

    def capture(self, form_data):
        if self.amount > 0 and not self.status: #new payment
            if not self.id:
                self.save()
            return self._update(self.processor.capture(form_data))
        if self.amount <= 0:
            raise ValueError('Invalid amount')
        return self

    def capture_authorized(self, amount=None):
        if self.status == 'A':
            if amount is None:
                amount = self.amount
            if amount > self.amount:
                raise ValueError('Can not capture above authorized amount')
            return self._update(self.processor.capture_authorized(amount))
        return self

    def cancel(self):
        """ cancel auth or refund at full """
        if self.status == 'A': #authorized: cancel
            return self._update(self.processor.release_authorized())
        elif self.status in ('CD', 'S'): #captured, settled: refund
            return self._update(self.processor.refund(self.amount))
        return self

    def refund(self, amount):
        """ Partial refund """
        if self.status in ('CD', 'S') and amount > 0: #refundable states: captured, settled
            if amount > self.amount:
                raise ValueError('Can not refund above authorized amount')
            return self._update(self.processor.refund(amount))
        return self

    def update_status(self):
        if self.status in ('', 'A', 'CD', 'S'): #transitional states: authorized, captured, settled
            return self._update(self.processor.get_payment_status())
        return self

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

class PaymentNote(models.Model):
    time_stamp = models.DateTimeField(_("timestamp"), editable=False, auto_now_add=True)
    payment = models.ForeignKey(Payment, related_name="notes", editable=False)
    note    = models.TextField(_('Note'))

    def __unicode__(self):
        return u"Payment  #%(payment_id)s note, %(date)s" % {
                'payment_id' :self.payment.id,
                'date'       :self.time_stamp,
            }

"""
As many processors use credit card data, here is a helper model to store sensitive data.
For other forms of payment to be stored, please create a similar model in gateway models
or in .details property of the Payment
"""

class CreditCardDetail(models.Model):
    """ Stores an encrypted CC number, its information, and its displayable number.
        Payment processor responsible for storing this data """
    payment     = models.OneToOneField(Payment, related_name="creditcard", editable=False)
    card_type   = models.CharField(_("Credit Card Type"), max_length=16, editable=False)
    display_cc  = models.CharField(_("CC Number (Last 4 digits)"), default="", max_length=4, editable=False)
    encrypted_cc= models.CharField(_("Encrypted Credit Card"), max_length=40, blank=True, null=True, editable=False)
    expiry      = models.DateField(_("Expiration date"), editable=False)
    name        = models.CharField(_('Name on card'), max_length=60, default="", editable=False)
    start_date  = models.DateField(_("Start date"), blank=True, null=True, editable=False)
    issue_num   = models.CharField(default="", max_length=2, editable=False)

     #temporary storage for values to be encrypted
    _card_no = ""
    _ccv     = ""

    def _key(self, type='card'):
        raw_key = ":".join((str(self.id), self.card_type, self.name, self.display_cc, self.expirationDate, type))
        return _encrypt_code(raw_key)

    def setCCV(self, ccv):
        """ Put the CCV in the cache, don't save it for security/legal reasons. """
        self._ccv = ccv

    def getCCV(self):
        """Get the CCV from cache"""
        return self._ccv or cache.get(self._key('ccv')) or ""

    ccv = property(fget=getCCV, fset=setCCV)

    def storeCC(self, ccnum):
        """ Take as input a valid cc, encrypt it and store the last 4 digits in a visible form """
        self._card_no  = ccnum
        self.card_type = utils.get_cardtype(ccnum)
        self.display_cc= ccnum[-4:]

    def decryptedCC(self):
        if self._card_no: # we're in the same session
            return self._card_no

        encrypted = None
        if self.encrypted_cc:
            encrypted = _decrypt_code(self.encrypted_cc)
        elif self.id:
            encrypted = cache.get(self._key())

        if encrypted is not None:
            return _decrypt_code(encrypted)

        return '*'*12 + self.display_cc

    card_no = property(fget=decryptedCC, fset=storeCC)

    @property
    def expirationDate(self):
        return(self.expiry.strftime('%m/%y'))

    def save(self, *args, **kwargs):
        if bursar_settings.STORE_CREDIT_NUMBERS and self._card_no and not self.encrypted_cc:
            self.encrypted_cc = _encrypt_code(self._card_no)

        super(CreditCardDetail, self).save(*args, **kwargs)

        if self._ccv:
            cache.add(self._key("ccv"), self._ccv, bursar_settings.CACHE_TIMEOUT)
        if not bursar_settings.STORE_CREDIT_NUMBERS and self._card_no:
            cache.add(self._key(), _encrypt_code(self._card_no), bursar_settings.CACHE_TIMEOUT)

    def delete(self, *args, **kwargs):
        #reset cache
        self.card_no = ''
        self.ccv = ''
        super(CreditCardDetail, self).delete(*args, **kwargs)

    class Meta:
        verbose_name = _("Credit Card")
        verbose_name_plural = _("Credit Cards")


def _decrypt_code(code):
    """Decrypt code encrypted by _encrypt_code"""
    secret_key = settings.SECRET_KEY
    encryption_object = Blowfish.new(secret_key)
    # strip padding from decrypted credit card number
    return encryption_object.decrypt(base64.b64decode(code)).rstrip('X')

def _encrypt_code(code):
    """Quick encrypter for CC codes or code fragments"""
    code = code.encode('utf8')
    secret_key = settings.SECRET_KEY
    encryption_object = Blowfish.new(secret_key)
    # block cipher length must be a multiple of 8
    padding = ''
    if (len(code) % 8) <> 0:
        padding = 'X' * (8 - (len(code) % 8))
    return base64.b64encode(encryption_object.encrypt(code + padding))
