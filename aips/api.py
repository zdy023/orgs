# coding=utf-8
from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError

DEBUG = settings.DEBUG

# ==================== Api Error ====================

RET_OK = 1
RET_ERR = 2
HTTP_STATUS_ERR = None


class ApiError(Exception):
    code = RET_OK

    def __init__(self, message, code=None, http_status=None):
        self.message = str(message)
        self.code = int(code) if code is not None else RET_ERR
        # if not http_status and self.code >= 100 and self.code <= 999:
        #     http_status = self.code
        self.http_status = http_status

    def __str__(self):
        code = "" if self.code == RET_ERR else (" (%d)" % self.code)
        return "ApiError: %s%s" % (self.message, code)

    def __repr__(self):
        status = "" if self.http_status is None else ", " + str(self.http_status)
        return 'ApiError("%s", %d%s)' % (self.message, self.code, status)

    def to_dict(self):
        return {"code": self.code, "message": self.message}

    def get_http_status_code(self):
        return self.http_status or HTTP_STATUS_ERR

# ================== JSON Encoders ==================

from json import JSONEncoder
from datetime import date
from collections import Iterable
import time

_basic_encode = JSONEncoder.default


def _encode(obj):
    # ERROR: returned string not works
    if isinstance(obj, ApiError):
        return obj.to_dict()
    elif isinstance(obj, date):
        return int(time.mktime(obj.timetuple()) * 1000)
    elif isinstance(obj, Iterable):
        return list(obj)
    return _basic_encode(ApiEncoder, obj)

ApiEncoderWithoutBlank = JSONEncoder(
    skipkeys=False,
    check_circular=False,
    allow_nan=True,
    indent=None,
    separators=(',', ':'),
    ensure_ascii=False,
    encoding=settings.DEFAULT_CHARSET,
    default=_encode,
)

ApiEncoder = JSONEncoder(
    skipkeys=False,
    check_circular=True,
    allow_nan=True,
    indent=2,
    separators=(', ', ': '),
    ensure_ascii=False,
    encoding=settings.DEFAULT_CHARSET,
    default=_encode,
) if DEBUG else ApiEncoderWithoutBlank

del JSONEncoder

# =================== Api Wrapper ===================

API_SUCCESS = ApiError("ok", RET_OK).to_dict()
API_CONTENT_TYPE = "application/json; charset=" + settings.DEFAULT_CHARSET
JAVASCRIPT_TYPE = "application/javascript; charset=" + settings.DEFAULT_CHARSET

from django.http.response import HttpResponse, HttpResponseBase


class JsonApiMiddleware:
    if DEBUG:
        import traceback
    JSON_API_PREFIX = getattr(settings, "JSON_API_PREFIX", "/api/")

    def __init__(self):
        pass

    def process_response(self, request, response):
        if request.path_info.startswith(self.JSON_API_PREFIX):
            return self.handle_response(response)
        return response

    def handle_response(self, response):
        if not isinstance(response, HttpResponseBase):
            content, status = self.handle_content(response)
            response = HttpResponse(content, content_type=API_CONTENT_TYPE, status=status)
        return response

    def handle_content(self, content):
        status = None
        if not isinstance(content, basestring):
            if isinstance(content, dict):
                error = content.get('error')
                if error is None:
                    content['error'] = API_SUCCESS
                elif isinstance(error, ApiError):
                    status = error.get_http_status_code()
            elif isinstance(content, ApiError):
                status = content.get_http_status_code()
                content = {"error": content.to_dict()}
            try:
                content = ApiEncoder.encode(content)
            except Exception as exception:
                return self.handle_exception_content(exception)
        return content, status

    def process_exception(self, request, exception):
        if request.path_info.startswith(self.JSON_API_PREFIX):
            return self.handle_exception(exception)
        return None

    def handle_exception(self, exception):
        result, status = self.handle_exception_content(exception)
        return HttpResponse(result, content_type=API_CONTENT_TYPE, status=status)

    def handle_exception_content(self, exception, jsonify=True):
        status = None
        if isinstance(exception, ApiError):
            status = exception.get_http_status_code()
            result = {"error": exception.to_dict()}
        elif isinstance(exception, MultiValueDictKeyError):
            # status = 400
            result = {"error": {"code": 400, "message": "missing arg: %s" % exception.args[0]}}
        else:
            result = {"error": {"code": RET_ERR, "message": repr(exception)}}
        if DEBUG:
            self.traceback.print_exc()
            result["error"]["trace"] = self.traceback.format_exc().strip().split("\n")
        return ApiEncoder.encode(result) if jsonify else result, status


# from functools import wraps as _wraps
jsonApiMiddleware = JsonApiMiddleware()


def wrap_json_api(func):
    # @_wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return jsonApiMiddleware.handle_response(result)
        except Exception as e:
            return jsonApiMiddleware.handle_exception(e)
    return wrapper


def create_api_response(content, response_class=HttpResponse, content_type=None, status=None, **kwargs):
    content, status2 = jsonApiMiddleware.handle_content(content)
    content_type = content_type or API_CONTENT_TYPE
    status = status or status2
    return response_class(content=content, content_type=content_type, status=status, **kwargs)

# =================== json module ===================

from json import _default_decoder as ApiDecoder


class JsonFactory:
    decoder = ApiDecoder
    encoder = ApiEncoder

    def __init__(self):
        pass

    def dumps(self, obj):
        return self.encoder.encode(obj)

    def dumps_no_blank(self, obj):
        return ApiEncoderWithoutBlank.encode(obj)

    FailureError = ApiError("Can not parse json body")
    EmptyBodyError = ApiError("Empty json body")

    def loads(self, body):
        if not body:
            raise self.EmptyBodyError
        try:
            return self.decoder.decode(body)
        except ValueError:
            raise self.FailureError

json = JsonFactory()

# =================== Date & Time ===================

from datetime import datetime

DEFAULT_TIME_FORMAT = "%Y-%m-%d %X"
DEFAULT_DATE_FORMAT = "%Y-%m-%d"


def to_datetime(date_str):
    return datetime.strptime(date_str, DEFAULT_TIME_FORMAT)


def from_datetime(date_obj):
    return date_obj.strftime(DEFAULT_TIME_FORMAT)


def from_date(date_obj):
    return date_obj.strftime(DEFAULT_DATE_FORMAT)
