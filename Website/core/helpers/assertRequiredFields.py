import json

from django.http import HttpRequest, JsonResponse # type: ignore

def assertRequiredFields(request: HttpRequest, required_fields: list[str]) -> JsonResponse | tuple[str]:
    """
    Check if the request contains all required fields.

    Args:
        request (HttpRequest): The HTTP request object.
        required_fields (list[str]): A list of required field names.

    Returns:
        JsonResponse | None: Returns a JsonResponse with an error message if a required field is missing,
                              otherwise returns None.
    """
    return_fields = ()

    data = json.loads(request.body)

    assert isinstance(data, dict)

    for field in required_fields:
        if field not in data.keys():
            return JsonResponse({"error": f"Missing required field: {field}"}, status=400)
        return_fields += (data.get(field),)
    

    return return_fields

