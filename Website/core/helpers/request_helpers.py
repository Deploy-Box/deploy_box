import json
from typing import Literal
from urllib.parse import parse_qs
from django.http import HttpRequest, JsonResponse


class MissingFieldError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.message = message
        self.status = status
        super().__init__(message)

    def to_response(self) -> JsonResponse:
        return JsonResponse({"error": self.message}, status=self.status)


def assertRequestFields(
    request: HttpRequest,
    required_fields: list[str] = [],
    optional_fields: list[str] = [],
    body_or_header: Literal["body", "header"] = "body",
    mimetype: Literal[
        "application/json", "application/x-www-form-urlencoded"
    ] = "application/json",
) -> tuple[str, ...]:
    """
    Check if the request contains all required fields.

    Args:
        request (HttpRequest): The HTTP request object.
        required_fields (list[str]): A list of required field names.
        optional_fields (list[str], optional): A list of optional field names. Defaults to an empty list.
        body_or_header (Literal["body", "header"]): Whether to check the body or headers of the request.
        mimetype (Literal["application/json", "application/x-www-form-urlencoded"]): The expected content type of the request body.

    Returns:
        tuple[str, ...]: Returns a tuple of string values for all fields. Optional fields will return empty strings if not present.
    """
    return_fields = ()

    if body_or_header == "header":
        data = dict(request.headers)
    elif mimetype == "application/json":
        try:
            # If body is already a string, try to parse it
            if isinstance(request.body, str):
                data = json.loads(request.body)
            else:
                # If body is bytes, decode it first
                body_str = (
                    request.body.decode("utf-8")
                    if isinstance(request.body, bytes)
                    else str(request.body)
                )
                data = json.loads(body_str)
        except json.JSONDecodeError:
            raise MissingFieldError("Invalid JSON", status=400)

    elif mimetype == "application/x-www-form-urlencoded":
        data = parse_qs(request.body.decode("utf-8"))
        data = {key: value[0] for key, value in data.items()}

    assert isinstance(data, dict)

    for field in required_fields:
        if field not in data.keys():
            raise MissingFieldError(f"Missing required field: {field}", status=400)

        value = data.get(field)
        return_fields += (str(value) if value is not None else "",)

    for field in optional_fields:
        if field in data.keys():
            value = data.get(field)
            return_fields += (str(value) if value is not None else "",)
        else:
            return_fields += (
                "",
            )  # Return empty string instead of None for optional fields

    return return_fields
