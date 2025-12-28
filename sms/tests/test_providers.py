import requests
from unittest.mock import Mock, patch

import pytest
from django.test import override_settings

from sms.providers import SmsIrProvider, SmsProviderError


@pytest.mark.parametrize(
    "raw_phone,expected",
    [
        ("09123456789", "09123456789"),
        ("9123456789", "09123456789"),
        ("+989123456789", "09123456789"),
        ("989123456789", "09123456789"),
        (" 09123456789 ", "09123456789"),
    ],
)
def test_normalize_phone_valid(raw_phone, expected):
    provider = SmsIrProvider()
    assert provider._normalize_phone(raw_phone) == expected


@pytest.mark.parametrize(
    "raw_phone",
    [
        "123",
        "09123",
        "08123456789",
        "09abcdefgh",
        "98912345678",
    ],
)
def test_normalize_phone_invalid_format(raw_phone):
    provider = SmsIrProvider()
    with pytest.raises(SmsProviderError):
        provider._normalize_phone(raw_phone)


@pytest.mark.parametrize("raw_phone", [None, 9123456789, ["09123456789"]])
def test_normalize_phone_invalid_type(raw_phone):
    provider = SmsIrProvider()
    with pytest.raises(SmsProviderError):
        provider._normalize_phone(raw_phone)


@override_settings(SMS_IR_API_KEY="test-key", SMS_IR_LINE_NUMBER="3000")
def test_send_otp_success():
    provider = SmsIrProvider()
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"status": 1, "data": {"message_id": "abc"}}

    with patch("sms.providers.requests.post", return_value=response) as mock_post:
        assert provider.send_otp("09123456789", "123456", 111) == {"message_id": "abc"}
        mock_post.assert_called_once()


@override_settings(SMS_IR_API_KEY="test-key", SMS_IR_LINE_NUMBER="3000")
def test_send_otp_status_not_success():
    provider = SmsIrProvider()
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"status": 0, "message": "bad request"}

    with patch("sms.providers.requests.post", return_value=response):
        with pytest.raises(SmsProviderError) as exc_info:
            provider.send_otp("09123456789", "123456", 111)

    assert exc_info.value.status_code == 0
    assert "bad request" in str(exc_info.value)


@override_settings(SMS_IR_API_KEY="test-key", SMS_IR_LINE_NUMBER="3000")
def test_send_otp_incomplete_response():
    provider = SmsIrProvider()
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {}

    with patch("sms.providers.requests.post", return_value=response):
        with pytest.raises(SmsProviderError) as exc_info:
            provider.send_otp("09123456789", "123456", 111)

    assert exc_info.value.status_code is None


@override_settings(SMS_IR_API_KEY="test-key", SMS_IR_LINE_NUMBER="3000")
def test_send_otp_network_error():
    provider = SmsIrProvider()

    with patch(
        "sms.providers.requests.post",
        side_effect=requests.exceptions.Timeout("timeout"),
    ):
        with pytest.raises(SmsProviderError) as exc_info:
            provider.send_otp("09123456789", "123456", 111)

    assert "Network error" in str(exc_info.value)


@override_settings(SMS_IR_API_KEY="test-key", SMS_IR_LINE_NUMBER="3000")
def test_send_text_success():
    provider = SmsIrProvider()
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"status": 1, "data": {"message_id": "xyz"}}

    with patch("sms.providers.requests.post", return_value=response) as mock_post:
        assert provider.send_text("09123456789", "Hello") == {"message_id": "xyz"}
        mock_post.assert_called_once()


@override_settings(SMS_IR_API_KEY="test-key", SMS_IR_LINE_NUMBER="3000")
def test_send_text_status_not_success():
    provider = SmsIrProvider()
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"status": 0, "message": "invalid"}

    with patch("sms.providers.requests.post", return_value=response):
        with pytest.raises(SmsProviderError) as exc_info:
            provider.send_text("09123456789", "Hello")

    assert exc_info.value.status_code == 0
    assert "invalid" in str(exc_info.value)


@override_settings(SMS_IR_API_KEY="test-key", SMS_IR_LINE_NUMBER="3000")
def test_send_text_incomplete_response():
    provider = SmsIrProvider()
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {}

    with patch("sms.providers.requests.post", return_value=response):
        with pytest.raises(SmsProviderError) as exc_info:
            provider.send_text("09123456789", "Hello")

    assert exc_info.value.status_code is None


@override_settings(SMS_IR_API_KEY="test-key", SMS_IR_LINE_NUMBER="3000")
def test_send_text_network_error():
    provider = SmsIrProvider()

    with patch(
        "sms.providers.requests.post",
        side_effect=requests.exceptions.ConnectionError("network down"),
    ):
        with pytest.raises(SmsProviderError) as exc_info:
            provider.send_text("09123456789", "Hello")

    assert "Network error" in str(exc_info.value)
