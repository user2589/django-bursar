# -*- coding: utf-8 -*-

PROCESSOR_KEY = __name__.rsplit(".", 1)[-1].upper()

DEFAULT_SETTINGS = {
    'MERCHANT_ID'     : '',
    'XML_PASSWORD'    : '',
    'CURRENCY'        : 'GBP',
    'SERVICE_URL'     : 'https://secure.wp3.rbsworldpay.com/jsp/merchant/xml/paymentService.jsp',
    'TEST_SERVICE_URL': 'https://secure-test.wp3.rbsworldpay.com/jsp/merchant/xml/paymentService.jsp',
    'CREDITCHOICES': (
        ('AMEX',    'American Express'),
        ('VISA',    'Visa'),
        ('MASTERCARD','MasterCard'),
        ('DC',      'Diners Club'),
        ('DISCOVER','Discover'),
        ('JCB',     'JCB'),
        ('MAESTRO', 'Maestro'),
    ),
    'PREFIX'          : '',
}
