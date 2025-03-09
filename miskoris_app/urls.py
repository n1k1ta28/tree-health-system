from django.urls import path
from . import views
from django.contrib import admin

urlpatterns=[
  path('admin/', admin.site.urls),  
  path('',views.home, name="home"),
  path('apie',views.about, name="about"),
  path('prisijungimas',views.loginPage, name="login"),
  path('atsijungimas',views.logoutUser, name="logout"),
  path('registracija',views.registerPage, name="register"),
  path('miskai',views.forests, name="forests"),
  path('nuotraukos',views.photos, name="photos"),
  path('image_upload', views.image_upload, name='image_upload'),
  path('miskas', views.forest, name='forest'),
]