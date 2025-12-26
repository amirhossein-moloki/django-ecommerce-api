from rest_framework import renderers, status
from ecommerce_api.core.api_standard_response import ApiResponse

class ApiResponseRenderer(renderers.JSONRenderer):
    """
    Custom renderer that formats all API responses using a standardized structure.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render the response data into the standardized API response format.
        """
        response = renderer_context.get("response", None) if renderer_context else None

        if isinstance(data, dict) and "success" in data and "message" in data:
            return super().render(data, accepted_media_type, renderer_context)

        if response and status.is_success(response.status_code):
            response_data = ApiResponse.success(data=data).data
        else:
            message = "An error occurred"
            errors = None
            status_code = response.status_code if response else 500

            if isinstance(data, dict):
                if "message" in data:
                    message = data.pop("message")
                elif "error" in data:
                    message = data.pop("error")
                elif "detail" in data:
                    message = data.pop("detail")

                errors = data if data else None
            else:
                errors = {"detail": data}

            response_data = ApiResponse.error(
                message=message, status_code=status_code, errors=errors
            ).data

        return super().render(response_data, accepted_media_type, renderer_context)
