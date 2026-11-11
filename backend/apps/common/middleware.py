"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md

Safety rule: health data must never be cached by a browser or a proxy.
"""


class NoStoreApiMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
        return response
