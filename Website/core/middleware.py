from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt

# class DisableCSRFMiddleware(MiddlewareMixin):
#     def process_view(self, request, view_func, view_args, view_kwargs):
#         setattr(request, '_dont_enforce_csrf_checks', True) 