from django.http import JsonResponse

def bad_method() -> JsonResponse:
    """
    Handle requests with unsupported HTTP methods.
    This function returns a 405 Method Not Allowed response.
    """

    return JsonResponse(
        {"error": "Method not allowed."},
        status=405
    )