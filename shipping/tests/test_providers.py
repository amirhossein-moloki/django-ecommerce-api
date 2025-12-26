import json

import pytest
import requests

from shipping.providers import PostexShippingProvider, ShippingProviderError


class DummyItems:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class DummyProduct:
    def __init__(self, *, weight, length, width, height, is_fragile, is_liquid):
        self.weight = weight
        self.length = length
        self.width = width
        self.height = height
        self.is_fragile = is_fragile
        self.is_liquid = is_liquid


class DummyVariant:
    def __init__(self, product):
        self.product = product


class DummyItem:
    def __init__(self, *, variant, quantity, product_name, price):
        self.variant = variant
        self.quantity = quantity
        self.product_name = product_name
        self.price = price


class DummyAddress:
    def __init__(self, *, receiver_name, receiver_phone, full_address, city_code, postal_code):
        self.receiver_name = receiver_name
        self.receiver_phone = receiver_phone
        self.full_address = full_address
        self.city_code = city_code
        self.postal_code = postal_code


class DummyOrder:
    def __init__(self, *, order_id, address, items, total_payable):
        self.order_id = order_id
        self.address = address
        self.items = DummyItems(items)
        self.total_payable = total_payable


class RequestsSpy:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.response

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.response

    def delete(self, url, **kwargs):
        self.calls.append(("delete", url, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.response


def make_response(*, status_code=200, json_data=None, raw_content=None):
    response = requests.Response()
    response.status_code = status_code
    if raw_content is not None:
        response._content = raw_content
    elif json_data is not None:
        response._content = json.dumps(json_data).encode("utf-8")
        response.headers["Content-Type"] = "application/json"
    else:
        response._content = b""
    return response


@pytest.fixture
def order():
    product_one = DummyProduct(
        weight=2,
        length=10,
        width=5,
        height=3,
        is_fragile=True,
        is_liquid=False,
    )
    product_two = DummyProduct(
        weight=1,
        length=8,
        width=4,
        height=2,
        is_fragile=False,
        is_liquid=True,
    )
    items = [
        DummyItem(
            variant=DummyVariant(product_one),
            quantity=2,
            product_name="Widget",
            price=200,
        ),
        DummyItem(
            variant=DummyVariant(product_two),
            quantity=1,
            product_name="Gadget",
            price=150,
        ),
    ]
    address = DummyAddress(
        receiver_name="Alex",
        receiver_phone="09120000000",
        full_address="123 Main St",
        city_code=123,
        postal_code="9876543210",
    )
    return DummyOrder(
        order_id="ORD-1",
        address=address,
        items=items,
        total_payable=1000,
    )


@pytest.fixture
def postex_provider(settings):
    settings.POSTEX_API_KEY = "test-key"
    settings.POSTEX_FROM_CITY_CODE = 999
    return PostexShippingProvider()


def assert_headers(headers):
    assert headers["Content-Type"] == "application/json"
    assert headers["x-api-key"] == "test-key"


def test_postex_requires_api_key(settings):
    settings.POSTEX_API_KEY = ""
    with pytest.raises(ValueError, match="POSTEX_API_KEY"):
        PostexShippingProvider()


def test_create_shipment_success(monkeypatch, postex_provider, order):
    response = make_response(json_data={"status": "ok", "parcel": "P123"})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "post", spy.post)

    result = postex_provider.create_shipment(order)

    assert result["status"] == "ok"
    assert result["parcel"] == "P123"
    assert len(spy.calls) == 1
    method, url, kwargs = spy.calls[0]
    assert method == "post"
    assert url == "https://api.postex.ir/api/v1/parcels/bulk"
    assert_headers(kwargs["headers"])
    assert kwargs["timeout"] == 15
    expected_payload = {
        "collection_type": "pick_up",
        "parcels": [
            {
                "to": {
                    "contact": {
                        "name": "Alex",
                        "mobile": "09120000000",
                    },
                    "location": {
                        "address": "123 Main St",
                        "city_code": 123,
                        "postal_code": "9876543210",
                    },
                },
                "parcel_items": [
                    {"name": "Widget", "count": 2, "amount": 200},
                    {"name": "Gadget", "count": 1, "amount": 150},
                ],
                "parcel_properties": {
                    "total_weight": 5,
                    "total_value": 1000,
                    "length": 10,
                    "width": 5,
                    "height": 3,
                    "is_fragile": True,
                    "is_liquid": True,
                },
            }
        ],
    }
    assert kwargs["json"] == expected_payload


def test_create_shipment_timeout(monkeypatch, postex_provider, order):
    spy = RequestsSpy(exc=requests.exceptions.Timeout("timeout"))
    monkeypatch.setattr(requests, "post", spy.post)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.create_shipment(order)

    assert "Error creating Postex shipment" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_create_shipment_http_error(monkeypatch, postex_provider, order):
    response = make_response(status_code=500, json_data={"error": "fail"})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "post", spy.post)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.create_shipment(order)

    assert "fail" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_create_shipment_malformed_json(monkeypatch, postex_provider, order):
    response = make_response(status_code=200, raw_content=b"not-json")
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "post", spy.post)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.create_shipment(order)

    assert "Malformed JSON" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_shipment_tracking_success(monkeypatch, postex_provider):
    response = make_response(json_data={"events": ["delivered"]})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "get", spy.get)

    result = postex_provider.get_shipment_tracking("P123")

    assert result["events"] == ["delivered"]
    assert len(spy.calls) == 1
    method, url, kwargs = spy.calls[0]
    assert method == "get"
    assert url == "https://api.postex.ir/api/v1/tracking/events/P123"
    assert_headers(kwargs["headers"])
    assert kwargs["timeout"] == 10


def test_get_shipment_tracking_timeout(monkeypatch, postex_provider):
    spy = RequestsSpy(exc=requests.exceptions.ConnectionError("network"))
    monkeypatch.setattr(requests, "get", spy.get)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_shipment_tracking("P123")

    assert "Error getting Postex tracking" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_shipment_tracking_http_error(monkeypatch, postex_provider):
    response = make_response(status_code=404, json_data={"error": "missing"})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "get", spy.get)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_shipment_tracking("P123")

    assert "missing" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_shipment_tracking_malformed_json(monkeypatch, postex_provider):
    response = make_response(status_code=200, raw_content=b"not-json")
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "get", spy.get)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_shipment_tracking("P123")

    assert "Malformed JSON" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_shipping_quote_success(monkeypatch, postex_provider, order):
    response = make_response(json_data={"quotes": [{"price": 2500}]})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "post", spy.post)

    result = postex_provider.get_shipping_quote(order)

    assert result["quotes"][0]["price"] == 2500
    assert len(spy.calls) == 1
    method, url, kwargs = spy.calls[0]
    assert method == "post"
    assert url == "https://api.postex.ir/api/v1/shipping/quotes"
    assert_headers(kwargs["headers"])
    assert kwargs["timeout"] == 10
    expected_payload = {
        "collection_type": "pick_up",
        "from_city_code": 999,
        "parcels": [
            {
                "to_city_code": 123,
                "total_weight": 5,
                "total_value": 1000,
                "length": 10,
                "width": 5,
                "height": 3,
            }
        ],
    }
    assert kwargs["json"] == expected_payload


def test_get_shipping_quote_timeout(monkeypatch, postex_provider, order):
    spy = RequestsSpy(exc=requests.exceptions.Timeout("timeout"))
    monkeypatch.setattr(requests, "post", spy.post)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_shipping_quote(order)

    assert "Error getting Postex shipping quote" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_shipping_quote_http_error(monkeypatch, postex_provider, order):
    response = make_response(status_code=500, json_data={"error": "bad"})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "post", spy.post)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_shipping_quote(order)

    assert "bad" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_shipping_quote_malformed_json(monkeypatch, postex_provider, order):
    response = make_response(status_code=200, raw_content=b"not-json")
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "post", spy.post)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_shipping_quote(order)

    assert "Malformed JSON" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_cancel_shipment_success(monkeypatch, postex_provider):
    response = make_response(json_data={"status": "canceled"})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "delete", spy.delete)

    result = postex_provider.cancel_shipment("P123")

    assert result["status"] == "canceled"
    assert len(spy.calls) == 1
    method, url, kwargs = spy.calls[0]
    assert method == "delete"
    assert url == "https://api.postex.ir/api/v1/parcels/P123"
    assert_headers(kwargs["headers"])
    assert kwargs["timeout"] == 10


def test_cancel_shipment_timeout(monkeypatch, postex_provider):
    spy = RequestsSpy(exc=requests.exceptions.Timeout("timeout"))
    monkeypatch.setattr(requests, "delete", spy.delete)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.cancel_shipment("P123")

    assert "Error canceling Postex shipment" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_cancel_shipment_http_error(monkeypatch, postex_provider):
    response = make_response(status_code=400, json_data={"error": "cannot"})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "delete", spy.delete)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.cancel_shipment("P123")

    assert "cannot" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_cancel_shipment_malformed_json(monkeypatch, postex_provider):
    response = make_response(status_code=200, raw_content=b"not-json")
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "delete", spy.delete)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.cancel_shipment("P123")

    assert "Malformed JSON" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_cities_success(monkeypatch, postex_provider):
    response = make_response(json_data={"cities": ["Tehran"]})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "get", spy.get)

    result = postex_provider.get_cities()

    assert result["cities"] == ["Tehran"]
    assert len(spy.calls) == 1
    method, url, kwargs = spy.calls[0]
    assert method == "get"
    assert url == "https://api.postex.ir/api/v1/locality/cities/all"
    assert_headers(kwargs["headers"])
    assert kwargs["timeout"] == 10


def test_get_cities_timeout(monkeypatch, postex_provider):
    spy = RequestsSpy(exc=requests.exceptions.Timeout("timeout"))
    monkeypatch.setattr(requests, "get", spy.get)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_cities()

    assert "Error getting Postex city list" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_cities_http_error(monkeypatch, postex_provider):
    response = make_response(status_code=500, json_data={"error": "nope"})
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "get", spy.get)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_cities()

    assert "nope" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])


def test_get_cities_malformed_json(monkeypatch, postex_provider):
    response = make_response(status_code=200, raw_content=b"not-json")
    spy = RequestsSpy(response=response)
    monkeypatch.setattr(requests, "get", spy.get)

    with pytest.raises(ShippingProviderError) as excinfo:
        postex_provider.get_cities()

    assert "Malformed JSON" in str(excinfo.value)
    assert len(spy.calls) == 1
    _, _, kwargs = spy.calls[0]
    assert_headers(kwargs["headers"])
