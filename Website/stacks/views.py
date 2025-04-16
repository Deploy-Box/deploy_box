from django.http import JsonResponse, FileResponse

from core.decorators import oauth_required, AuthHttpRequest
import stacks.handlers as handlers


@oauth_required()
def base_routing(
    request: AuthHttpRequest,
) -> JsonResponse:
    # GET: Fetch available stacks or a specific stack
    if request.method == "GET":
        pass

    # POST: Add a new stack
    elif request.method == "POST":
        return handlers.post_stack(request)

    # If the request method is not handled, return a 405 Method Not Allowed
    return JsonResponse({"error": "Method not allowed."}, status=405)


@oauth_required()
def purchasable_stack_routing(
    request: AuthHttpRequest,
) -> JsonResponse:
    # GET: Fetch available stacks or a specific stack
    if request.method == "GET":
        return handlers.get_purchasable_stack(request)

    # POST: Add a new purchasable stack
    elif request.method == "POST":
        return handlers.post_purchasable_stack(request)

    # If the request method is not handled, return a 405 Method Not Allowed
    return JsonResponse({"error": "Method not allowed."}, status=405)
