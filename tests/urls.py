from __future__ import unicode_literals

from django.conf.urls import include, url
from rest_framework import routers

from . import views

router = routers.DefaultRouter(trailing_slash=False)

router.register(r'tickets', views.TicketViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^raw/$', views.RawViewSet.as_view(), name='raw-data'),
]
