from rest_framework.authentication import BaseAuthentication


class WorkOSSessionAuthentication(BaseAuthentication):
    """
    DRF authentication class that reads request.user populated by
    WorkOSSessionMiddleware. Replaces DRF's built-in SessionAuthentication.
    """

    def authenticate(self, request):
        user = getattr(request._request, "user", None)
        if not user or not user.is_authenticated:
            return None
        return (user, None)
