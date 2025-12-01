# Test Coverage Report

This report outlines the areas of the codebase that require testing to achieve 100% test coverage.

## `account` app

### `models.py`
- `Profile` model:
  - Test the `__str__` method.
- `UserManager` model manager:
  - `create_user`: Test user creation with valid and invalid data.
  - `create_superuser`: Test superuser creation with valid and invalid data.
- `UserAccount` model:
  - Test the `name` property.
  - Test the `__str__` method.
  - Test the validators for `username` and `phone_number`.
- `Address` model:
  - Test the `__str__` method.

### `views.py`
- `UserViewSet`:
  - `me`: Test GET, PUT, PATCH, and DELETE methods for the authenticated user's profile.
  - `create`: Test user registration with valid and invalid data.
  - `activation`: Test account activation with a valid and invalid key.
  - `set_password`: Test setting a new password for the authenticated user.
  - `reset_password`: Test initiating a password reset.
  - `reset_password_confirm`: Test confirming a password reset with a valid and invalid token.
  - `staff_check`: Test checking the staff status of a user.
- `TokenObtainPairView`:
  - Test obtaining a token pair with valid and invalid credentials.
- `TokenRefreshView`:
  - Test refreshing a token with a valid and invalid refresh token.
- `TokenVerifyView`:
  - Test verifying a token with a valid and invalid token.
- `TokenDestroyView`:
  - Test logging out a user by blacklisting their refresh token.
- `ActivateView`:
  - Test that the activation view renders the correct template.
- `RequestOTP`:
  - Test requesting an OTP with a valid and invalid phone number.
- `VerifyOTP`:
  - Test verifying an OTP with a valid and invalid code.
  - Test user creation when a user with the given phone number does not exist.

## `cart` app

### `cart.py`
- `Cart` class:
  - `__init__`: Test cart initialization for authenticated and anonymous users.
  - `merge_session_cart`: Test merging the session cart into the database cart upon user login.
  - `add`: Test adding a product to the cart and updating its quantity.
  - `remove`: Test removing a product from the cart.
  - `__iter__`: Test iterating over the items in the cart.
  - `__len__`: Test getting the total number of items in the cart.
  - `get_total_price`: Test calculating the total price of all items in the cart.
  - `save`: Test saving the cart to the session.
  - `clear`: Test clearing the cart.
  - `coupon`: Test retrieving the currently applied coupon.
  - `get_discount`: Test calculating the discount amount.
  - `get_total_price_after_discount`: Test calculating the total price after applying the discount.

### `views.py`
- `CartViewSet`:
  - `list`: Test retrieving the cart details.
  - `add_to_cart`: Test adding a product to the cart with valid and invalid data.
  - `remove_from_cart`: Test removing a product from the cart.
  - `clear_cart`: Test clearing the cart.

## `chat` app

### `models.py`
- `Message` model:
  - Test the `__str__` method.

### `consumers.py`
- `ChatConsumer`:
  - `connect`: Test WebSocket connection with authenticated and unauthenticated users, and with valid and invalid product IDs.
  - `disconnect`: Test WebSocket disconnection.
  - `receive`: Test receiving a WebSocket message with valid and invalid data.
  - `chat_message`: Test sending a chat message to the WebSocket.

### `views.py`
- `ProductChatAPIView`:
  - `get`: Test retrieving chat messages for a product with a valid and invalid product ID, and with authenticated and unauthenticated users.

## `coupons` app

### `models.py`
- `Coupon` model:
  - `clean`: Test that `valid_from` is earlier than `valid_to`.
  - `is_valid`: Test checking the validity of a coupon.
  - `increment_usage_count`: Test atomically incrementing the usage count of the coupon.
  - `__str__`: Test the `__str__` method.

### `views.py`
- `CouponViewSet`:
  - `update`: Test updating a coupon, and preventing the modification of the `code` field.
  - `destroy`: Test deactivating a coupon.
  - `apply`: Test applying a coupon with a valid and invalid code.

## `orders` app

### `models.py`
- `Order` model:
  - `get_total_cost_before_discount`: Test calculating the total cost before discount.
  - `get_discount`: Test calculating the discount amount.
  - `total_price`: Test calculating the total price after discount.
  - `calculate_total_payable`: Test calculating the final amount to be paid.
  - `__str__`: Test the `__str__` method.
- `OrderItem` model:
  - `price`: Test calculating the price of an order item.
  - `__str__`: Test the `__str__` method.

### `views.py`
- `OrderViewSet`:
  - `get_serializer_class`: Test that the correct serializer is returned for each action.
  - `get_permissions`: Test that the correct permissions are returned for each action.
  - `get_queryset`: Test that the correct queryset is returned for staff and non-staff users.
  - `create`: Test creating a new order.

### `serializers.py`
- `OrderCreateSerializer`:
  - `validate_address_id`: Test validating the address ID.
  - `validate`: Test validating the coupon code.
  - `save`: Test creating and saving the order and its items.

## `payment` app

### `gateways.py`
- `ZibalGateway`:
  - `create_payment_request`: Test creating a payment request with mock API calls.
  - `verify_payment`: Test verifying a payment with mock API calls.

### `views.py`
- `PaymentProcessAPIView`:
  - `post`: Test processing a payment with a valid and invalid order ID.
- `PaymentVerifyAPIView`:
  - `get`: Test verifying a payment with a valid and invalid track ID.

### `services.py`
- `process_payment`: Test processing a payment, including stock checks and interactions with the payment gateway.
- `verify_payment`: Test verifying a payment, including stock updates and order status changes.

## `shipping` app

### `providers.py`
- `PostexShippingProvider`:
  - `create_shipment`: Test creating a shipment with mock API calls.
  - `get_shipment_tracking`: Test getting shipment tracking information with mock API calls.
  - `get_shipping_quote`: Test getting a shipping quote with mock API calls.
  - `cancel_shipment`: Test canceling a shipment with mock API calls.
  - `get_cities`: Test getting a list of cities with mock API calls.

### `views.py`
- `CityListAPIView`:
  - `get`: Test retrieving the list of cities.
- `CalculateShippingCostAPIView`:
  - `post`: Test calculating the shipping cost for an order.

## `shop` app

### `models.py`
- `Category` model:
  - `save`: Test that the slug is auto-generated from the name.
  - `get_absolute_url`: Test getting the absolute URL for a category.
  - `__str__`: Test the `__str__` method.
- `InStockManager`:
  - `get_queryset`: Test that only products in stock are returned.
- `Product` model:
  - `save`: Test that a unique slug is auto-generated.
  - `get_absolute_url`: Test getting the absolute URL for a product.
  - `update_rating_and_reviews_count`: Test updating the rating and reviews count.
  - `__str__`: Test the `__str__` method.
- `Review` model:
  - `save`: Test that the business logic for checking if a user has purchased the product is called.
  - `__str__`: Test the `__str__` method.

### `services.py`
- `get_product_detail`: Test getting a product's details, including caching.
- `get_user_products`: Test getting a user's products.
- `get_reviews_for_product`: Test getting the reviews for a product.
- `create_review`: Test creating a review, including the purchase validation.
- `get_category_list`: Test getting the list of categories.
- `create_category`: Test creating a category.

### `views.py`
- `ReviewViewSet`:
  - `get_permissions`: Test that the correct permissions are returned for each action.
  - `get_queryset`: Test that the correct queryset is returned.
  - `create`: Test creating a new review.
- `ProductViewSet`:
  - `get_permissions`: Test that the correct permissions are returned for each action.
  - `get_serializer_class`: Test that the correct serializer is returned for each action.
  - `perform_create`: Test creating a new product.
  - `perform_update`: Test updating a product.
  - `perform_destroy`: Test deleting a product.
  - `list`: Test listing all products, including caching.
  - `retrieve`: Test retrieving a single product, including caching.
  - `list_user_products`: Test listing a user's products.
- `CategoryViewSet`:
  - `get_permissions`: Test that the correct permissions are returned for each action.
  - `list`: Test listing all categories, including caching.
  - `perform_create`: Test creating a new category.
  - `perform_update`: Test updating a category.
  - `perform_destroy`: Test deleting a category.

## `sms` app

### `models.py`
- `OTPCode` model:
  - `is_expired`: Test checking if an OTP code is expired.
  - `__str__`: Test the `__str__` method.

### `providers.py`
- `SmsIrProvider`:
  - `send_otp`: Test sending an OTP with mock API calls.
  - `send_text`: Test sending a text message with mock API calls.

### `views.py`
- `RequestOTP`:
  - `post`: Test requesting an OTP.
- `VerifyOTP`:
  - `post`: Test verifying an OTP and creating a user if one does not exist.
