from django.utils.deprecation import MiddlewareMixin


class JWTCompatibleHistoryMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if hasattr(request, "user") and request.user.is_authenticated:
            request._history_user = request.user
