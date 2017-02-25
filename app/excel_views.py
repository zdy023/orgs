# coding=utf-8
from django.db.models import F
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
import datetime, time, os, string, random, sys, re
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required
from collections import Iterable
from .models import *
from aips.api import ApiError, create_api_response, json
import pyexcel

from .utils import *

ABS_BASE_DIR = os.path.join(settings.BASE_DIR, settings.FILE_UPLOAD_PATH)

#@login_required
def parse_file(request):
    args = request.POST
    file_id = int(args["id"])
    file = FileHistory.objects.get(id=file_id)
    if file.creator_id != request.user.id:
        return ApiError("只能导入您自己上传的文件", 403)
    cur_job_id = request.session.get("job") or None
    job_type = Job.objects.values("type").get(id=cur_job_id)["type"] if cur_job_id else None
    count = 0
    if file.type in FileHistory.JobTypes:
        if job_type is None or job_type < Job.TYPE_ADMIN or job_type > Job.TYPE_EMPLOYEE:
            if request.user.is_superuser:
                return ApiError("您需要把自己设为一级管理员后才能导入数据", 403)
            else:
                return NotPermittedError
        if file.type == FileHistory.TYPE_L1:
            if job_type != Job.TYPE_ADMIN:
                return ApiError("您当前的身份不能导入此表格：%d / 1" % job_type, 400)
        elif file.type == FileHistory.TYPE_L2:
            if job_type != Job.TYPE_DEPART:
                return ApiError("您当前的身份不能导入此表格：%d / 2" % job_type, 400)
            if not Job.objects.filter(user_id=request.user.id, type=Job.TYPE_DEPART).exists():
                return ApiError("助手不可以批量重置同级别其他负责人", 403)
        elif file.type == FileHistory.TYPE_L3:
            if job_type == Job.TYPE_GROUP:
                pass
            elif job_type == Job.TYPE_DEPART:
                pass
            else:
                return ApiError("您当前的身份不能导入此表格：%d / 3" % job_type, 400)

        first_sheet, other_sheets, contacts = parse_jobs(file)
        if first_sheet is None and not other_sheets:
            raise ApiError("缺少总表", 400)
        elif first_sheet is None:
            first_sheet = []
        all_sheets = [first_sheet] + list(other_sheets)
        first_type = job_type + 1
        if first_type > Job.TYPE_DEPART:
            start = set(line[7] for sheet in all_sheets for line in sheet)
            if len(start) > 1:
                raise ApiError("此类级别下所有人任命时间应当完全一致", 400)
        ensure_users(all_sheets, contacts)
        count = import_jobs(first_sheet, other_sheets, first_type , cur_job_id, job_type)
    return {
        "new_count": count,
    }


def parse_jobs(file_item):
    """
        NOTE: branch, title, card, nick, flat, cell, email, start = line[:8]
    """
    # file_history.type
    book = pyexcel.get_book(file_name=ABS_BASE_DIR + file_item.file)
    cur_sheet_ind, first_sheet, other_sheets, contacts = 0, None, [], None
    for sheet in book:
        if sheet.name == "数据源": continue
        arr = sheet.to_array()
        if len(arr) <= 0 and cur_sheet_ind > 0: continue
        if sheet.name == "个人信息" or sheet.name == "个人信息汇总":
            start = 1 if arr[0] and arr[0][0] == "姓名" else 0
            contacts = arr[start:]
            continue
        start = 1 if arr[0] and arr[0][0] == "部门名" else 0
        arr = arr[start:]
        for line in arr:
            branch, title, card_no, nick, flat, cell, email, start = line[:8]
            err = "学号" if not card_no else "姓名" if not nick else \
                "部门名" if not branch else "职务名" if not title else \
                "任命时间" if not start else ""
            if err:
                raise ApiError("某行数据缺少" + err + "：" + " ".join(line))
        if cur_sheet_ind == 0:
            first_sheet = arr
        elif arr:
            other_sheets.append(arr)
        cur_sheet_ind += 1
    return first_sheet, other_sheets, contacts


def ensure_users(all_sheets, contacts):
    card_dict = {}
    for sheet in all_sheets:
        for line in sheet:
            card_no, nick, flat, cell, email = line[2:7]
            card_no = str(card_no)
            card_dict[card_no] = [nick, flat, cell, email]
    if not card_dict:
        return
    existing_users = CustomUser.objects.filter(username__in=card_dict.keys())
    to_update_user_dict, to_add_users = {}, []
    print card_dict
    for user in existing_users:
        new_info = card_dict.pop(user.username)
        to_update = {}
        if new_info[0] != user.first_name:
            to_update["first_name"] = new_info[0]
        if new_info[1] != user.flat and user.flat:
            to_update["flat"] = new_info[1]
        if new_info[2] != user.cell and user.cell:
            to_update["cell"] = new_info[2]
        if new_info[3] != user.email and user.email:
            to_update["email"] = new_info[3]
        if to_update:
            to_update_user_dict[user.id] = to_update
    for card_no, new_info in card_dict.iteritems():
        nick, flat, cell, email = new_info
        user = CustomUser(username=card_no, flat=flat, cell=cell, email=email, first_name=nick)
        to_add_users.append(user)
    with transaction.atomic():
        for user_id, to_update in to_update_user_dict.iteritems():
            CustomUser.objects.filter(id=user_id).update(**to_update)
        if to_add_users:
            CustomUser.objects.bulk_create(to_add_users)


@transaction.atomic
def import_jobs(first_sheet, other_sheets, first_type, boss_id, boss_type):
    cards = set()
    for line in first_sheet:
        cards.add(str(line[2]))
    for sheet in other_sheets:
        cards.update(str(line[2]) for line in sheet)
    users = CustomUser.objects.filter(username__in=list(cards)).values_list("id", "username")
    users = {card_no: user_id for user_id, card_no in users}

    if first_type == Job.TYPE_GROUP:
        Job.objects.filter(id=boss_id).update(helper_id=None)
    if first_type <= Job.TYPE_DEPART:
        if other_sheets:
            raise ApiError("后续分表：未能识别！", 400)
        return replace_jobs(first_sheet, users, first_type, boss_id)
    """
    if False:
        new_job_type = Job.TYPE_EMPLOYEE
        first_sheet = []
        for sheet in other_sheets:
            first_sheet += sheet
        other_sheets = []
    else:
    """
    direct_next_job_type = first_type
    if boss_type == Job.TYPE_DEPART and not first_sheet:
        direct_next_job_type = Job.TYPE_EMPLOYEE
    sub_job_ids = get_all_children([boss_id], direct_next_job_type)
    if sub_job_ids:
        query = Job.objects.filter(id__in=sub_job_ids)
        query.update(end=datetime.date.today(), type=F("type") * Job.TYPE_REMVOED_FACTOR)
    del direct_next_job_type, sub_job_ids

    new_job_type = first_type
    new_jobs = []
    for line in first_sheet:
        branch, title, card, nick, flat, cell, email, start = line[:8]
        job = Job(user_id=users[str(card)], boss_id=boss_id, type=new_job_type,
                  branch=branch, title=title, start=start)
        new_jobs.append(job)
    if new_jobs:
        Job.objects.bulk_create(new_jobs)
    first_new_count = len(new_jobs)
    if (not other_sheets) or new_job_type >= Job.TYPE_EMPLOYEE:
        return first_new_count

    has_first = bool(new_jobs)
    new_jobs, second_users = [], {}
    if has_first:
        query = Job.objects.filter(boss_id=boss_id, type=new_job_type).values_list("id", "user__username")
        second_users = { card: id for id, card in query }
    new_job_type += 1
    for sheet in other_sheets:
        sub_boss_id = None
        if has_first:
            for line in sheet:
                sub_boss_id = second_users.get(str(line[2]))
                if sub_boss_id: break
            if not sub_boss_id:
                raise ApiError(
    """有一张表里没有发现该组织的负责人，请检查学号拼写和总表是否一致。
    分表的第一行：""" + (" ".join(sheet[0]) if sheet else "（无）")
                    , 400)
        else:
            sub_boss_id = boss_id
        for line in sheet:
            branch, title, card, nick, flat, cell, email, start = line[:8]
            card = str(card)
            if card in second_users: continue
            job = Job(user_id=users[card], boss_id=sub_boss_id, type=new_job_type,
                      branch=branch, title=title, start=start)
            new_jobs.append(job)
    Job.objects.bulk_create(new_jobs)
    return first_new_count + len(new_jobs)


def replace_jobs(sheet, user_card_to_id, job_type, boss_id=None):
    query = Job.objects.filter(type=job_type)
    if job_type > Job.TYPE_DEPART:
        assert boss_id, "lack boss_id in replace_jobs"
        query = query.filter(boss_id=boss_id)
    else:
        boss_id = None
    old_job_ids = list(query.values_list("id", flat=True))
    # can not update `end` here

    # write new jobs
    # NOTE: branch, title, card, nick, flat, cell, email, start = line[:8]
    new_jobs = []
    for line in sheet:
        branch, title, card, nick, flat, cell, email, start = line[:8]
        job = Job(user_id=user_card_to_id[str(card)], boss_id=boss_id, type=job_type,
                  branch=branch, title=title, start=start)
        new_jobs.append(job)
    Job.objects.bulk_create(new_jobs)

    # get ids
    query = query.values_list("id", "branch", "title")
    old_jobs = {branch + '/' + title: id
                for id, branch, title in query
                if id in old_job_ids}
    updated_count = 0
    for id, branch, title in query:
        if id in old_job_ids: continue
        old_id = old_jobs.get(branch + '/' + title)
        if old_id:
            Job.objects.filter(boss_id=old_id).update(boss_id=id)
            updated_count += 1

    end_data_map = {}
    for line in sheet:
        branch, title = line[:2]
        new_start = line[7]
        old_id = old_jobs.pop(branch + '/' + title, None)
        if old_id:
            end_data_map.setdefault(new_start, []).append(old_id)
    end_on_today = end_data_map.setdefault(datetime.date.today(), [])
    if old_jobs:
        end_on_today += old_jobs.values()
    for end_data, old_ids in end_data_map.iteritems():
        Job.objects.filter(id__in=old_ids).update(end=end_data, type=F("type") * Job.TYPE_REMVOED_FACTOR)
    return len(new_jobs) + updated_count