import pytest
from django.urls import reverse, NoReverseMatch
import uuid

@pytest.mark.django_db
def test_reverse_payment_urls():
    """
    Ensures that all payment-related URLs can be reversed without errors.
    """
    # Test for the 'process' URL, which requires an order_id
    try:
        order_id = uuid.uuid4()
        url = reverse('payment:process', kwargs={'order_id': order_id})
        assert url == f'/payment/process/{order_id}/'
    except NoReverseMatch:
        pytest.fail("Failed to reverse URL for 'payment:process'")

    # Test for the 'verify' URL
    try:
        url = reverse('payment:verify')
        assert url == '/payment/verify/'
    except NoReverseMatch:
        pytest.fail("Failed to reverse URL for 'payment:verify'")
