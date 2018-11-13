from django.conf.urls import url
from orders import views

urlpatterns = [
    url(r'^place/$',views.order_place,name='place'),
]
