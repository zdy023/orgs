# -*- coding: utf-8 -*-
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
import datetime, time, os, string, random, sys, re, urllib
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from collections import Iterable

from aips.api import ApiError, create_api_response, json, jsonApiMiddleware
from .models import *
from . import models
from .utils import *


# Create your views here.

def api_ret_error(request):
    return NoSuchApiError


def debug_sys(request):
    user = request.user
    if not (user is not None and user.is_superuser and user.is_active and user.is_authenticated()):
        return {"error": NotPermittedError.to_dict()}
    import traceback
    try:
        import sys
        from django.views.debug import technical_500_response
        result = technical_500_response(request, *sys.exc_info())
        result.status_code = 200
    except Exception as exception:
        if isinstance(exception, ApiError):
            result = {"error": exception.to_dict()}
        else:
            result = {"error": {"code": 2, "message": repr(exception)}}
        result["error"]["trace"] = traceback.format_exc().strip().split("\n")
    return result


def get_user(request):
    user = request.user
    return {
        "id": user.id,
        "card": user.get_username(),
        "name": user.first_name,
        "login": user.is_authenticated() and user.is_active,
        "super": user.is_superuser and user.is_active,
        "job": request.session.get("job") or None
    }


def handle_uploaded_file(f, file_ext, id=1):
    today = datetime.date.today()
    prefix = today.strftime("%y%m%W")
    today_dir_path = os.path.join(settings.FILE_UPLOAD_PATH, prefix)
    if not os.path.isdir(today_dir_path):
        os.mkdir(today_dir_path)

    rand_str = ""
    choices = string.ascii_letters + string.digits
    for i in (0, 1, 2, 3):
        rand_str += random.choice(choices)
    file_name = '%d_%d_%s.%s' % (today.day, id % 10000, rand_str, file_ext or "bin")
    file_path = os.path.join(today_dir_path, file_name)

    with open(file_path, 'wb') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    return prefix + '/'+ file_name


def save_form_file(form_file):
    file_obj = form_file
    if not file_obj: return None
    ext = file_obj.name.split('.')[-1]
    i = len(file_obj.name)
    file_path = handle_uploaded_file(file_obj, ext, i)
    return file_path


@login_required
def save_form_files(request, field):
    job_id = request.session.get("job") or None
    file_obj = request.FILES.get("file")
    if file_obj is None: return ''
    path = save_form_file(file_obj)
    file_type = FileHistory.TYPE_L1 if field == "l1" \
        else FileHistory.TYPE_L2 if field == "l2" \
        else FileHistory.TYPE_L3 if field == "l3" \
        else FileHistory.TYPE_UNKNOWN
    desp = request.POST.get("desp") or None
    history = FileHistory(title=file_obj.name[:127],
                          type=file_type, file=path,
                          creator_id=request.user.id, job_id=job_id,
                          description=desp)
    history.save()
    return {
        'id': history.id,
        'path': path,
    }


def to_camelcase(s):
    return re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)


def to_list(obj):
    return None if obj is None else \
        obj if isinstance(obj, Iterable) and not isinstance(obj, basestring) \
        else [obj]


def query_list(request, collection):
    argv = dict(request.GET.iteritems())
    return _query_list(request, argv, collection)


def _query_list(request, argv, collection):
    Model = getattr(models, to_camelcase(collection.title()))
    if not Model:
        return ApiError("no such collection", 400)
    list_all = int(argv.pop('all', '') or 0) > 0
    reverse = int(argv.pop('reverse', '') or 0) > 0
    to_prefetch_related = to_list(argv.pop('prefetch[]', None))
    to_select_related = to_list(argv.pop('select[]', None))
    to_select_values = to_list(argv.pop('values[]', None))
    if list_all:
        want_count = False
        count, page = 0, 0
    else:
        count = int(argv.pop('size', '') or 0) or 10
        page = int(argv.pop('page', '') or 0) or 1
        want_count = int(argv.pop('count', '') or 0) > 0
        page = page if page > 0 else 1
        count = count if count > 0 else 10

    order = ""
    need_order = reverse
    if need_order:
        order = (getattr(Model._meta, "ordering") or [""])[0]
        if reverse:
            order = order[1:] if order[:1] == "-" else "-" + (order or "pk")

    query = Model.objects.all()

    if argv:
        query = query.filter(**argv)

    total = query.count() if want_count else -1
    complicated = False
    if to_select_values:
        query = query.values(*to_select_values)
    else:
        if to_select_related:
            query = query.select_related(*to_select_related)
            complicated = True
        if to_prefetch_related:
            query = query.prefetch_related(*to_prefetch_related)
            complicated = True
    if not list_all:
        if order:
            query = query.order_by(order)
        if count > 0 and page > 0:
            query = query[count * (page - 1):count * page]

    return {
        "list": [i.to_dict() for i in query] if complicated else query.values(),
        "count": total,
    }


def list_jobs(request):
    jobs, ori_type = get_all_jobs(request.user)
    if jobs:
        query = Job.objects.filter(id__in=jobs).values("id", "type", "branch", "title")
    else:
        query = []
    return {
        "list": query,
        "ori_type": ori_type,
        "job": request.session.get("job")
    }


def select_job(request):
    job_id = int(request.POST["job"])
    allowed_jobs, ori_type = get_all_jobs(request.user)
    if job_id not in allowed_jobs:
        return ApiError("您无权选择此身份", 403)
    request.session["job"] = job_id
    return {
        "job": job_id,
    }


def set_admin(request):
    card = request.POST["card"]
    act = request.POST["act"]
    is_add = act == "1"
    if is_add:
        user = ensure_one_user(card)
    else:
        user = CustomUser.objects.filter(username=card).first()
        if not user:
            return ApiError("找不到此账号", 400)
    query = Job.objects.filter(user_id=user.id, type=Job.TYPE_ADMIN)
    cur_is_admin = query.exists()
    if is_add == cur_is_admin:
        return ApiError("现在此用户已经%s是管理员了" % ("" if cur_is_admin else "不"), 400)
    if is_add:
        job = Job(user_id=user.id, type=Job.TYPE_ADMIN,
                  branch="管理员", title=user.first_name or user.username,
                  start=datetime.date.today())
        job.save()
    else:
        query.update(type=Job.TYPE_ADMIN * Job.TYPE_REMVOED_FACTOR, end=datetime.date.today())
    return {
        "card": card,
        "id": user.id,
        "name": user.first_name,
        "is_admin": is_add,
    }


def list_admin(request):
    if not request.user.is_superuser:
        return NotPermittedError
    query = CustomUser.objects.filter(job__type=Job.TYPE_ADMIN).values_list("username", "first_name")
    result = [{
        "card": i[0],
        "name": i[1]
    } for i in query]
    return {
        "list": result,
    }


def share_job(request):
    user_id = request.user.id
    query = Job.objects.filter(type=Job.TYPE_DEPART, user_id=user_id)
    main_job = query.values_list("id", "helper_id").first()
    if not main_job:
        return ApiError("您无权指定其他负责人做您的助手", 403)
    helper_job_id = int(request.POST.get("job_id", 0))
    if helper_job_id:
        if not Job.objects.filter(type=Job.TYPE_GROUP, boss_id=main_job[0], id=helper_job_id).exists():
            return ApiError("该负责人不能成为您的助手", 403)
    else:
        if not main_job[1]:
            return ApiError("您当前没有指定助手", 403)
        helper_job_id = None
    count = Job.objects.filter(id=main_job[0]).update(helper_id=helper_job_id)
    return {
        "count": count,
        "main_job": main_job[0],
        "helper_job": helper_job_id,
    }


def list_helpers(request):
    user_id = request.user.id
    main_job = Job.objects.filter(user_id=user_id, type=Job.TYPE_DEPART).values_list("id", "helper_id").first()
    if not main_job:
        return NotPermittedError
    query = Job.objects.filter(boss_id=main_job[0], type=Job.TYPE_GROUP)
    result = query.values_list("id", "branch", "title", "user__first_name")
    return {
        "list": [
            {
                "id": i[0],
                "branch": i[1],
                "title": i[2],
                "name": i[3],
            }
            for i in result
        ],
        "helper_job": main_job[1],
    }


def list_first_level_employees(request):
    user_id = request.user.id
    main_job = Job.objects.filter(user_id=user_id, type__gt=0).values_list("id", "type", "helper_id", "branch", "title").first()
    if not main_job or main_job[1] > Job.TYPE_GROUP:
        return NotPermittedError
    is_helper = False
    boss_id = None
    type = main_job[1]
    branch, title = main_job[3:5]
    if main_job[1] == Job.TYPE_GROUP:
        boss_l2 = Job.objects.filter(type=Job.TYPE_DEPART, helper_id=main_job[0]).values_list("id", "branch", "title", "type").first()
        if boss_l2:
            is_helper = True
            boss_id, branch, title, type = boss_l2
    if not boss_id:
        boss_id = main_job[0]
    query = Job.objects.filter(boss_id=boss_id, type__gt=0)
    result = query.values_list("id", "type", "branch", "title", "user__username", "user__first_name", "start",
                               "user_id", "user__email", "user__cell", "user__flat")
    return {
        "list": [
            {
                "id": i[0],
                "type": i[1],
                "branch": i[2],
                "title": i[3],
                "card": i[4],
                "name": i[5],
                "start": i[6],
                "user_id": i[7],
                "email": i[8],
                "cell": i[9],
                "flat": i[10],
            }
            for i in result
        ],
        "job": {
            "id": boss_id,
            "type": type,
            "branch": branch,
            "title": title,
        },
        "self": main_job[0],
        "is_helper": is_helper,
        "helper_job": main_job[2],
    }


def list_employees_under_job(request):
    job_id = int(request.GET["id"])
    if not check_admin_auth(request.user.id, job_id):
        return NotPermittedError
    branch, title, type = Job.objects.filter(id=job_id).values_list("branch", "title", "type").first()
    query = Job.objects.filter(boss_id=job_id, type__gt=0)
    result = query.values_list("id", "type", "branch", "title", "user__username", "user__first_name", "start",
                               "user_id", "user__email", "user__cell", "user__flat")
    return {
        "list": [
            {
                "id": i[0],
                "type": i[1],
                "branch": i[2],
                "title": i[3],
                "card": i[4],
                "name": i[5],
                "start": i[6],
                "user_id": i[7],
                "email": i[8],
                "cell": i[9],
                "flat": i[10],
            }
            for i in result
        ],
        "job": {
            "id": job_id,
            "type": type,
            "branch": branch,
            "title": title,
        },
    }


import requests
STHUAPP_TOKEN = "http://student.tsinghua.edu.cn/api/user/session/token"
STHUAPP_LOGOUT = "http://student.tsinghua.edu.cn/logout"


def do_logout(request):
    request.session.clear()
    logout(request)
    return HttpResponseRedirect(STHUAPP_LOGOUT)


def do_login(request):
    token = request.GET.get("token")
    if not token:
        return ApiError("want a token", 400)
    resp = requests.post(STHUAPP_TOKEN, {
        "token": token
    })
    resp = json.loads(resp.content)
    if resp["error"]["code"] != 1:
        return HttpResponse("拉取学生清华网站身份信息：失败！", status=400)
    card_no = str(resp["card"])
    first_name = str(resp["name"])
    cell = resp.get("cell") or None
    user = authenticate(username=card_no, password=card_no)
    if not user:
        user = CustomUser.objects.create_user(card_no, None, card_no, first_name=first_name, cell=cell)
        user.save()
        user = authenticate(username=card_no, password=card_no)
    elif user.first_name != first_name and first_name:
        CustomUser.objects.filter(id=user.id).update(first_name=first_name)
        user.first_name = first_name
    login(request, user)

    # add session
    user_id = user.id
    job_id = Job.objects.filter(type__gt=0, user_id=user_id).values_list("id", flat=True).first()
    request.session["job"] = job_id

    url = request.GET.get("url")
    return HttpResponseRedirect(url or "/")


def redirect_to_login_if_needed(request):
    if request.user.is_authenticated():
        return None
    cur_path = urllib.quote(request.get_full_path())
    cur_path = "&url=" + cur_path if cur_path != "/" else ""
    callback = request.build_absolute_uri("/login?token=TOKEN" + cur_path)
    url = STHUAPP_TOKEN + "?redirect_uri=" + urllib.quote(callback)
    return HttpResponseRedirect(url)


def index(request):
    red = redirect_to_login_if_needed(request)
    if red:
        return red
    #request.META["CSRF_COOKIE_USED"] = True
    user = get_user(request)
    cur_job = request.session.get("job")
    path = request.path_info.strip("/")
    if "/" in path or not path:
        path = "index"
    elif path == "admin":
        print request.path, cur_job
        if user["super"]:
            allowed = True
        elif not cur_job:
            allowed = False
        else:
            main_type = Job.objects.filter(id=cur_job, type__gt=0).values_list("type", flat=True).first()
            if not main_type:
                allowed = False
            elif main_type > Job.TYPE_GROUP:
                return HttpResponseRedirect("/home")
            else:
                allowed = True
        if not allowed:
            return jsonApiMiddleware.handle_response(NotPermittedError)
    context = {
        'user': json.dumps_no_blank(user)
    }
    return render_to_response(path + '.html', context)


def show_user_home(request):
    red = redirect_to_login_if_needed(request)
    if red:
        return red
    if request.path_info[:5] == "/home":
        user = request.user
    else:
        card = request.path_info[1:]
        user = CustomUser.objects.filter(username=card).defer("password").first()
        if not user:
            return jsonApiMiddleware.handle_response(ApiError("没有找到此用户", 404, 404))
        if user.id != request.user.id and not request.user.is_superuser:
            job = Job.objects.filter(user_id=user).values_list("id", "type").first()
            if not job or job[1] <= 0 or not check_admin_auth(request.user.id, job[0]):
                return jsonApiMiddleware.handle_response(NotPermittedError)
    context = {
        'user': json.dumps_no_blank(get_user(request)),
        "user2": json.dumps_no_blank(user.to_dict()),
    }
    return render_to_response('user_home.html', context)