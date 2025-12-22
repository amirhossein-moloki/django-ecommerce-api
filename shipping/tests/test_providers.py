
import pytest
import requests
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import override_settings
from shipping.providers import PostexShippingProvider, ShippingProviderError

pytestmark = pytest.mark.django_db


class TestPostexShippingProvider:
    @pytest.fixture
    def provider(self):
        with override_settings(POSTEX_API_KEY="test-key", POSTEX_FROM_CITY_CODE=1):
            return PostexShippingProvider()

    @pytest.fixture
    def mock_order(self):
        """
        Creates a completely mocked order object to isolate shipping tests
        from the complexities of the database and other app's factories.
        """
        order = MagicMock()
        order.order_id = "mock-order-123"
        order.address.receiver_name = "Test User"
        order.address.receiver_phone = "09123456789"
        order.address.full_address = "123 Test St"
        order.address.city_code = 1
        order.address.postal_code = "1234567890"
        order.total_payable = Decimal("550.00")

        # Mock order items
        item1 = MagicMock()
        item1.variant.product.weight = Decimal("1.2")
        item1.variant.product.length = Decimal("10")
        item1.variant.product.width = Decimal("10")
        item1.variant.product.height = Decimal("5")
        item1.variant.product.is_fragile = False
        item1.variant.product.is_liquid = False
        item1.product_name = "Product A"
        item1.quantity = 1
        item1.price = Decimal("250.00")

        item2 = MagicMock()
        item2.variant.product.weight = Decimal("0.8")
        item2.variant.product.length = Decimal("20")
        item2.variant.product.width = Decimal("15")
        item2.variant.product.height = Decimal("10")
        item2.variant.product.is_fragile = True
        item2.variant.product.is_liquid = True
        item2.product_name = "Product B"
        item2.quantity = 2
        item2.price = Decimal("150.00")

        order.items.all.return_value = [item1, item2]
        return order

    def test_create_shipment_success(self, provider, mock_order, requests_mock):
        mock_url = f"{provider.api_url}/api/v1/parcels/bulk"
        mock_response = {"status": "success", "parcels": [{"parcel_no": "12345"}]}
        requests_mock.post(mock_url, json=mock_response, status_code=201)
        response = provider.create_shipment(mock_order)
        assert response == mock_response

    @pytest.mark.parametrize("method_name, http_method, url_path, method_args", [
        ("create_shipment", "POST", "/api/v1/parcels/bulk", ["mock_order"]),
        ("get_shipment_tracking", "GET", "/api/v1/tracking/events/123", ["123"]),
        ("cancel_shipment", "DELETE", "/api/v1/parcels/123", ["123"]),
        ("get_shipping_quote", "POST", "/api/v1/shipping/quotes", ["mock_order"]),
        ("get_cities", "GET", "/api/v1/locality/cities/all", []),
    ])
    def test_network_errors_are_handled(self, provider, mock_order, requests_mock, method_name, http_method, url_path, method_args):
        mock_url = f"{provider.api_url}{url_path}"
        requests_mock.register_uri(http_method, mock_url, exc=requests.exceptions.ConnectTimeout)
        with pytest.raises(ShippingProviderError):
            method_to_call = getattr(provider, method_name)
            final_args = [mock_order if arg == "mock_order" else arg for arg in method_args]
            method_to_call(*final_args)

    @pytest.mark.parametrize("method_name, http_method, url_path, method_args, status_code", [
        ("create_shipment", "POST", "/api/v1/parcels/bulk", ["mock_order"], 400),
        ("get_shipment_tracking", "GET", "/api/v1/tracking/events/123", ["123"], 404),
        ("cancel_shipment", "DELETE", "/api/v1/parcels/123", ["123"], 500),
        ("get_shipping_quote", "POST", "/api/v1/shipping/quotes", ["mock_order"], 503),
        ("get_cities", "GET", "/api/v1/locality/cities/all", [], 401),
    ])
    def test_http_errors_are_handled(self, provider, mock_order, requests_mock, method_name, http_method, url_path, method_args, status_code):
        mock_url = f"{provider.api_url}{url_path}"
        requests_mock.register_uri(http_method, mock_url, text="Error", status_code=status_code)
        with pytest.raises(ShippingProviderError) as excinfo:
            method_to_call = getattr(provider, method_name)
            final_args = [mock_order if arg == "mock_order" else arg for arg in method_args]
            method_to_call(*final_args)
        assert excinfo.value.status_code == status_code

    @pytest.mark.parametrize("method_name, http_method, url_path, method_args", [
        ("create_shipment", "POST", "/api/v1/parcels/bulk", ["mock_order"]),
        ("get_cities", "GET", "/api/v1/locality/cities/all", []),
    ])
    def test_malformed_json_response_is_handled(self, provider, mock_order, requests_mock, method_name, http_method, url_path, method_args):
        mock_url = f"{provider.api_url}{url_path}"
        requests_mock.register_uri(http_method, mock_url, text="<not_json>", status_code=200)
        with pytest.raises(ShippingProviderError):
            method_to_call = getattr(provider, method_name)
            final_args = [mock_order if arg == "mock_order" else arg for arg in method_args]
            method_to_call(*final_args)
