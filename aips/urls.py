from django.conf.urls import include, url
from django.views.generic import RedirectView
from django.contrib import admin

from app import views

urlpatterns = [
    # Examples:
    # url(r'^blog/', include('blog.urls')),
    # url(r'^member/(?P<id>[_0-9A-Fa-f]+)$', views.get_help),
    url(r'^admin/', admin.site.urls),
]

from .static_urls import static_patterns
urlpatterns += static_patterns
del static_patterns

urlpatterns += [
    url(r'^api/', include('app.api_urls')),
    url(r'api/', views.api_ret_error),
    url(r'login$', views.do_login),
    url(r'logout$', views.do_logout),
    # Default:
    #url(r'^$', RedirectView.as_view(url = '/static/index.html')),
    url(r'^\d\d\d', views.show_user_home),
    url(r'^home$', views.show_user_home),
    url(r'^.*$', views.index),
]
