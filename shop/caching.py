import hashlib
from typing import Dict, Any


def generate_product_list_cache_key(query_params: Dict[str, Any]) -> str:
    """
    Generates a consistent cache key for the product list endpoint
    based on query parameters.

    The parameters are sorted to ensure that the order does not affect
    the final key. A hash is used to keep the key length manageable.
    """
    # Create a copy to avoid modifying the original query_params
    params = query_params.copy()

    # Remove pagination parameters as they are handled by the view's pagination logic
    # and the entire response (for a given page) is cached.
    params.pop("page", None)
    params.pop("page_size", None)

    if not params:
        return "product_list:default"

    # Sort the query parameters by key to ensure consistency
    sorted_params = sorted(params.items())

    # Create a consistent string representation
    # Example: [['category', 'laptops'], ['ordering', '-price']] -> "category=laptops&ordering=-price"
    param_string = "&".join(
        [
            f"{key}={','.join(sorted(value)) if isinstance(value, list) else value}"
            for key, value in sorted_params
        ]
    )

    # Hash the string to create a unique and fixed-length key component
    # Using MD5 for speed as cryptographic security is not a concern here.
    hashed_params = hashlib.md5(param_string.encode("utf-8")).hexdigest()

    return f"product_list:{hashed_params}"
