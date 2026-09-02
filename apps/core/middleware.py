from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.http.response import HttpResponseRedirectBase


class PreserveEmbedMiddleware:
    """Se la richiesta è in modalità embed, propaga embed=1 sui redirect."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.is_embed = (
            request.GET.get("embed") == "1" or request.POST.get("embed") == "1"
        )
        response = self.get_response(request)
        if request.is_embed and isinstance(response, HttpResponseRedirectBase):
            response["Location"] = self._with_embed(response["Location"])
        return response

    @staticmethod
    def _with_embed(location: str) -> str:
        if not location or location.startswith("//"):
            return location
        parts = urlsplit(location)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        if query.get("embed") == "1":
            return location
        query["embed"] = "1"
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )
