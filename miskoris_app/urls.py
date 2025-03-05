from django.urls import path
from . import views
from django.contrib import admin

urlpatterns=[
  path('admin/', admin.site.urls),  
  path('',views.home, name="home"),
  path('apie',views.about, name="about"),
  path('prisijungimas',views.login, name="login"),
  path('registracija',views.register, name="register"),
]