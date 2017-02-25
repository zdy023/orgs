# coding=utf-8

from .models import Job, CustomUser
from django.db.models import F, Q
from aips.api import ApiError, create_api_response, json

NoSuchApiError = ApiError("No such Api", 4, http_status=404)
NotPermittedError = ApiError("Not permitted", 3)


def get_all_children(job_ids, direct_next_job_type=0):
    query = Job.objects.filter(type__gte=direct_next_job_type)
    if len(job_ids) == 1:
        query = query.filter(boss_id=job_ids[0])
    else:
        query = query.filter(boss_id__in=job_ids)
    sub_job_ids = list(query.values_list("id", flat=True))
    if sub_job_ids:
        return sub_job_ids + get_all_children(sub_job_ids)
    else:
        return []


def ensure_one_user(card, **kwargs):
    user = CustomUser.objects.filter(username=card).first()
    if not user:
        user = CustomUser.objects.create_user(card, None, card, **kwargs)
        user.save()
    return user


def get_all_jobs(user):
    user_id = user.id
    is_superuser = user.is_superuser
    main_job = Job.objects.filter(type__gt=0, user_id=user_id).values_list("id", "type", "boss_id").first()
    if not main_job:
        return [], 0
    jobs = [main_job[0]]
    if main_job[1] == Job.TYPE_ADMIN or main_job[1] >= Job.TYPE_SUB_GROUP:
        return jobs, main_job[1]

    if main_job[1] == Job.TYPE_DEPART:
        sub_jobs = Job.objects.filter(type=Job.TYPE_GROUP, boss_id=main_job[0]).values_list("id", flat=True)
        jobs += list(sub_jobs)
    elif main_job[1] == Job.TYPE_GROUP:
        helper_id = Job.objects.filter(type=Job.TYPE_DEPART, id=main_job[2]).values_list("helper_id", flat=True).first()
        if helper_id and helper_id == main_job[0]:
            l3_jobs = Job.objects.filter(type=Job.TYPE_GROUP, boss_id=main_job[2]).values_list("id", flat=True)
            jobs = set(l3_jobs)
            jobs.add(main_job[0])
            jobs.add(main_job[2])
            jobs = list(jobs)
        else:
            jobs = []
    else:
        raise ApiError("很抱歉，权限数据出错了，请联系管理员", code=500, http_status=500)

    return jobs, main_job[1]


def check_admin_auth(boss_user_id, employee_job_id):
    if Job.objects.filter(user_id=boss_user_id, type=Job.TYPE_ADMIN).exists():
        return True
    tick = 0
    while True:
        query = Job.objects.filter(id=employee_job_id, type__gt=0)
        job = query.values_list("user_id", "boss_id", "helper_id", "type").first()
        if not job:
            return False
        if job[0] == boss_user_id:
            return True
        if job[2] and job[2] != employee_job_id:
            if Job.objects.filter(id=job[2], user_id=boss_user_id).exists():
                return True
        if job[3] <= Job.TYPE_DEPART:
            return False
        tick += 1
        if tick > 5:
            return False
        employee_job_id = job[1]
    return False


