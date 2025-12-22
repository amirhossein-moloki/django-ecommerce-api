
import pytest
import requests
from unittest.mock import patch
from django.test import override_settings

from ..providers import SmsIrProvider, SmsProviderError


@pytest.fixture
def provider():
    """Provides an instance of SmsIrProvider with mocked settings."""
    with override_settings(SMS_IR_API_KEY="test_api_key", SMS_IR_LINE_NUMBER="12345"):
        yield SmsIrProvider()


class TestSmsIrProvider:
    def test_missing_api_key_raises_error(self):
        with override_settings(SMS_IR_API_KEY=None):
            with pytest.raises(SmsProviderError, match="SMS.ir API key is not configured."):
                p = SmsIrProvider()
                p._get_headers()

    def test_missing_line_number_raises_error(self, provider):
        provider.line_number = None
        with pytest.raises(SmsProviderError, match="SMS.ir line number is not configured."):
            provider.send_text("09123456789", "test")

    @pytest.mark.parametrize("input_phone, expected_phone", [
        ("+989123456789", "09123456789"),
        ("989123456789", "09123456789"),
        ("9123456789", "09123456789"),
        ("09123456789", "09123456789"),
    ])
    def test_phone_number_normalization(self, provider, input_phone, expected_phone):
        assert provider._normalize_phone(input_phone) == expected_phone

    @pytest.mark.parametrize("invalid_phone", [
        "123",
        "0912345678",
        "091234567890",
        "08123456789",
        "not-a-number",
    ])
    def test_invalid_phone_number_raises_error(self, provider, invalid_phone):
        with pytest.raises(SmsProviderError):
            provider._normalize_phone(invalid_phone)

    @patch("sms.providers.requests.post")
    def test_send_otp_success(self, mock_post, provider):
        mock_post.return_value.json.return_value = {
            "status": 1,
            "message": "موفق",
            "data": {"messageId": 12345},
        }
        mock_post.return_value.raise_for_status = lambda: None

        response = provider.send_otp("09123456789", "12345", 101)
        assert response["messageId"] == 12345
        sent_data = mock_post.call_args.kwargs["json"]
        assert sent_data["mobile"] == "09123456789"

    @patch("sms.providers.requests.post")
    def test_send_otp_api_error(self, mock_post, provider):
        mock_post.return_value.json.return_value = {
            "status": 113,
            "message": "قالب یافت نشد",
        }
        mock_post.return_value.raise_for_status = lambda: None

        with pytest.raises(SmsProviderError, match="قالب یافت نشد") as excinfo:
            provider.send_otp("09123456789", "12345", 999)
        assert excinfo.value.status_code == 113

    @patch("sms.providers.requests.post")
    def test_send_text_success(self, mock_post, provider):
        mock_post.return_value.json.return_value = {
            "status": 1,
            "message": "موفق",
            "data": {"packId": "some-uuid"},
        }
        mock_post.return_value.raise_for_status = lambda: None

        response = provider.send_text("09123456789", "Hello World")
        assert response["packId"] == "some-uuid"

    @patch("sms.providers.requests.post")
    def test_network_error_raises_sms_provider_error(self, mock_post, provider):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        with pytest.raises(SmsProviderError, match="Network error"):
            provider.send_otp("09123456789", "12345", 101)
