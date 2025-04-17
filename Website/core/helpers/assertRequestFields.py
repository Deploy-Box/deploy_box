import json
from typing import Literal
from urllib.parse import parse_qs
from django.http import HttpRequest, JsonResponse  # type: ignore


def assertRequestFields(
    request: HttpRequest, required_fields: list[str], optional_fields: list[str] = [], body_or_header: Literal["body", "header"] = "body", mimetype: Literal["application/json", "application/x-www-form-urlencoded"] = "application/json"
) -> JsonResponse | tuple:
    """
    Check if the request contains all required fields.

    Args:
        request (HttpRequest): The HTTP request object.
        required_fields (list[str]): A list of required field names.
        optional_fields (list[str], optional): A list of optional field names. Defaults to an empty list.
        body_or_header (Literal["body", "header"]): Whether to check the body or headers of the request.
        mimetype (Literal["application/json", "application/x-www-form-urlencoded"]): The expected content type of the request body.

    Returns:
        JsonResponse | tuple: Returns a JsonResponse with an error message if a required field is missing,
                              otherwise returns a tuple of the field values.
    """
    return_fields = ()

    if body_or_header == "header":
        data = request.headers
    elif mimetype == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON", "data": str(request.body)}, status=400
            )
    elif mimetype == "application/x-www-form-urlencoded":
        data = parse_qs(request.body.decode("utf-8"))
        data = {key: value[0] for key, value in data.items()}
        print(f"Data: {data}")
    else:
        return JsonResponse(
            {"error": "Unsupported"}, status=400
        )

    assert isinstance(data, dict)

    for field in required_fields:
        if field not in data.keys():
            return JsonResponse(
                {"error": f"Missing required field: {field}"}, status=400
            )
        return_fields += (data.get(field),)

    for field in optional_fields:
        if field in data.keys():
            return_fields += (data.get(field),)
        else:
            return_fields += (None,)

    return return_fields
