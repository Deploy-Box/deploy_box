import json
from typing import Literal
from django.http import HttpRequest, JsonResponse  # type: ignore


def assertRequiredFields(
    request: HttpRequest, required_fields: list[str], body_or_header: Literal["body", "header"] = "body"
) -> JsonResponse | tuple:
    """
    Check if the request contains all required fields.

    Args:
        request (HttpRequest): The HTTP request object.
        required_fields (list[str]): A list of required field names.
        body_or_header (Literal["body", "header"]): Whether to check the body or headers of the request.

    Returns:
        JsonResponse | tuple: Returns a JsonResponse with an error message if a required field is missing,
                              otherwise returns a tuple of the field values.
    """
    return_fields = ()

    if body_or_header == "header":
        data = request.headers
    else:
        data = json.loads(request.body)

    assert isinstance(data, dict)

    for field in required_fields:
        if field not in data.keys():
            return JsonResponse(
                {"error": f"Missing required field: {field}"}, status=400
            )
        return_fields += (data.get(field),)

    return return_fields
