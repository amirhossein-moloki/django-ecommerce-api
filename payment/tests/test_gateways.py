import pytest
import requests
from payment.gateways import ZibalGateway, ZibalGatewayError


@pytest.fixture
def zibal_gateway():
    """Provides a ZibalGateway instance for testing."""
    return ZibalGateway()


def test_create_payment_request_success(requests_mock, zibal_gateway):
    """
    Tests successful payment request creation.
    """
    requests_mock.post(
        "https://gateway.zibal.ir/v1/request",
        json={"result": 100, "trackId": 12345},
    )
    response = zibal_gateway.create_payment_request(
        amount=10000,
        order_id="some-order-id",
        callback_url="http://example.com/callback",
    )
    assert response["result"] == 100
    assert response["trackId"] == 12345


def test_create_payment_request_failure_from_zibal(requests_mock, zibal_gateway):
    """
    Tests handling of a failed payment request from Zibal (e.g., result code is not 100).
    """
    requests_mock.post(
        "https://gateway.zibal.ir/v1/request",
        json={"result": 102, "message": "merchant not found"},
    )
    with pytest.raises(ZibalGatewayError) as excinfo:
        zibal_gateway.create_payment_request(
            amount=10000,
            order_id="some-order-id",
            callback_url="http://example.com/callback",
        )
    assert "Zibal request failed with result 102" in str(excinfo.value)


def test_create_payment_request_network_error(requests_mock, zibal_gateway):
    """
    Tests handling of a network error during payment request.
    """
    requests_mock.post(
        "https://gateway.zibal.ir/v1/request", exc=requests.exceptions.ConnectTimeout
    )
    with pytest.raises(ZibalGatewayError) as excinfo:
        zibal_gateway.create_payment_request(
            amount=10000,
            order_id="some-order-id",
            callback_url="http://example.com/callback",
        )
    assert "Network error creating payment request" in str(excinfo.value)


def test_create_payment_request_http_error(requests_mock, zibal_gateway):
    """
    Tests handling of an HTTP error (e.g., 500 Internal Server Error) during payment request.
    """
    requests_mock.post("https://gateway.zibal.ir/v1/request", status_code=500)
    with pytest.raises(ZibalGatewayError):
        zibal_gateway.create_payment_request(
            amount=10000,
            order_id="some-order-id",
            callback_url="http://example.com/callback",
        )


def test_verify_payment_success(requests_mock, zibal_gateway):
    """
    Tests successful payment verification.
    """
    requests_mock.post(
        "https://gateway.zibal.ir/v1/verify",
        json={"result": 100, "refNumber": "abcdef"},
    )
    response = zibal_gateway.verify_payment(payload_or_authority=12345)
    assert response["result"] == 100
    assert response["refNumber"] == "abcdef"


def test_verify_payment_failure_from_zibal(requests_mock, zibal_gateway):
    """
    Tests handling of a failed payment verification from Zibal.
    """
    requests_mock.post(
        "https://gateway.zibal.ir/v1/verify",
        json={"result": 202, "message": "Order not found"},
    )
    response = zibal_gateway.verify_payment(payload_or_authority=12345)
    assert response["result"] == 202
    assert "Order not found" in response["message"]


def test_verify_payment_network_error(requests_mock, zibal_gateway):
    """
    Tests handling of a network error during payment verification.
    """
    requests_mock.post(
        "https://gateway.zibal.ir/v1/verify", exc=requests.exceptions.ConnectTimeout
    )
    with pytest.raises(ZibalGatewayError) as excinfo:
        zibal_gateway.verify_payment(payload_or_authority=12345)
    assert "Network error verifying payment" in str(excinfo.value)


def test_verify_payment_http_error(requests_mock, zibal_gateway):
    """
    Tests handling of an HTTP error (e.g., 500 Internal Server Error) during payment verification.
    """
    requests_mock.post("https://gateway.zibal.ir/v1/verify", status_code=500)
    with pytest.raises(ZibalGatewayError):
        zibal_gateway.verify_payment(payload_or_authority=12345)
