# coding=utf-8
import sys

__all__ = ["static_patterns"]
static_patterns = True if 'runserver' in ' '.join(sys.argv) else []
del sys

if static_patterns:
    from django.conf import settings
    from django.views.static import serve
    from django.conf.urls import url
    from django.core.servers.basehttp import WSGIRequestHandler
    from django.http import HttpResponse

    static_patterns = []

    _STATIC_URL = settings.STATIC_URL
    if _STATIC_URL and not settings.DEBUG and settings.STATICFILES_DIRS:
        static_patterns.append(
            url(r'^' + _STATIC_URL[1:] + r'(?P<path>.*)$',
                serve,
                {'document_root': settings.STATICFILES_DIRS[0]}),
        )
    _FILE_UPLOAD_URL = getattr(settings, "FILE_UPLOAD_URL")
    if _FILE_UPLOAD_URL and getattr(settings, "FILE_UPLOAD_PATH"):
        static_patterns.append(
            url(r'^' + _FILE_UPLOAD_URL[1:] + r'(?P<path>.*)$',
                serve,
                {'document_root': settings.FILE_UPLOAD_PATH}),
        )
    _FAVICON_NAME = "/favicon.ico"
    if bool(getattr(settings, "EMPTY_FAVICON", True)):
        static_patterns.append(
            url(r'^%s$' % _FAVICON_NAME[1:], lambda request: HttpResponse("", content_type="text/plain")),
        )

    _log_any_message = WSGIRequestHandler.log_message
    if _STATIC_URL and _FILE_UPLOAD_URL:
        def log_message(self, *args, **kwargs):
            if not (self.path.startswith(_STATIC_URL) or self.path.startswith(_FILE_UPLOAD_URL)
                    or self.path == _FAVICON_NAME):
                return _log_any_message(self, *args, **kwargs)
    elif _STATIC_URL or _FILE_UPLOAD_URL:
        _STATIC_URL = _STATIC_URL or _FILE_UPLOAD_URL
        def log_message(self, *args, **kwargs):
            if not (self.path.startswith(_STATIC_URL) or self.path == _FAVICON_NAME):
                return _log_any_message(self, *args, **kwargs)
    else:
        log_message = _log_any_message
    WSGIRequestHandler.log_message = log_message

    del settings, serve, url, WSGIRequestHandler, log_message