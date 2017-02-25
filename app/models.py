# -*- coding: utf-8 -*-
from django.db import models
from aips.api import json
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, UserManager
#User = get_user_model()
# from django.contrib.auth.models import Permission

class PrintableModel(models.Model):
    class Meta:
        abstract = True
    def to_dict(self, deep=True):
        d = self.__dict__
        out = {}
        for key, val in d.iteritems():
            if key[0:1] != "_":
                out[key] = val
            elif key == '_prefetched_objects_cache':
                for key, val in val.iteritems():
                    out[key + "s"] = [i.to_dict(deep=False) for i in val]
            elif key[-6:] == "_cache" and deep:
                out[key[1:-6]] = val.to_dict(deep=False)
        return out


class CustomUser(AbstractUser, PrintableModel):
    # username, first_name, email
    cell = models.CharField(max_length=16, null=True, blank=True)
    flat = models.CharField(max_length=30, null=True, blank=True)

    objects = UserManager()


def create_user_detail(sender, instance, signal, *args, **kwargs):
    if kwargs['created']:
        u = CustomUser()
        u.__dict__.update(instance.__dict__)
        u.save()

from django.db.models.signals import post_save
post_save.connect(create_user_detail, sender=AbstractUser)
del post_save, create_user_detail, UserManager, AbstractUser


class FileHistory(PrintableModel):
    TYPE_L1 = 1
    TYPE_L2 = 2
    TYPE_L3 = 3
    TYPE_UNKNOWN = -1

    JobTypes = (TYPE_L1, TYPE_L2, TYPE_L3)

    title = models.CharField(max_length=128)
    type = models.SmallIntegerField()
    file = models.FilePathField()
    create_time = models.DateTimeField(auto_now_add=True, db_index=True)
    creator = models.ForeignKey(CustomUser, on_delete=models.PROTECT, editable=False,
                              related_name="files", related_query_name="file")
    job = models.ForeignKey("Job", on_delete=models.SET_NULL, null=True, editable=False,
                              related_name="files", related_query_name="file")
    description = models.CharField(max_length=256, null=True)


class Job(PrintableModel):
    TYPE_ADMIN = 1
    TYPE_DEPART = 2
    TYPE_GROUP = 3
    TYPE_SUB_GROUP = 4
    TYPE_EMPLOYEE = 5

    TYPE_REMVOED_FACTOR = -1

    BRANCH_ADMIN = "一级管理员"

    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, editable=False,
                              related_name="jobs", related_query_name="job")
    boss = models.ForeignKey("self", on_delete=models.PROTECT, null=True, editable=False,
                              related_name="staffs", related_query_name="staff")
    type = models.SmallIntegerField(db_index=True)
    branch = models.CharField(max_length=20) # 部门名
    title = models.CharField(max_length=12) # 职务名
    start = models.DateField()
    end = models.DateField(null=True)
    helper = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, editable=False,
                               related_name="+", related_query_name="+")  # 助手

del models