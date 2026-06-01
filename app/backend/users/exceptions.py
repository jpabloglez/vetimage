"""
Custom exception handler for better error responses
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error format
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Customize error response format
        custom_response_data = {
            'error': True,
            'message': None,
            'details': response.data
        }

        # Extract primary error message
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                custom_response_data['message'] = response.data['detail']
            else:
                # Get first error message
                for key, value in response.data.items():
                    if isinstance(value, list) and len(value) > 0:
                        custom_response_data['message'] = f"{key}: {value[0]}"
                        break

        response.data = custom_response_data

    return response
