from django.conf.urls import include, url

from . import views, excel_views

urlpatterns = [
    url(r'^session$', views.get_user),
    url(r'^debug$', views.debug_sys),
    url(r'^job/list$', views.list_jobs),
    url(r'^job/select$', views.select_job),
    url(r'^job/admin/set$', views.set_admin),
    url(r'^job/admin/list$', views.list_admin),
    url(r'^job/helper/query$', views.list_helpers),
    url(r'^job/helper/set$', views.share_job),
    url(r'^upload/(?P<field>[^/]+)$', views.save_form_files),
    url(r'^excel/parse$', excel_views.parse_file),
    url(r'^list/main$', views.list_first_level_employees),
    url(r'^list/job$', views.list_employees_under_job),
    # url(r'^list/(?P<collection>[^/]+)$', views.query_list),
]