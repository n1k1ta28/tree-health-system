from django.urls import path
from . import views

urlpatterns=[
  path('',views.home, name="home"),
  path('apie',views.about, name="about"),
  path('prisijungimas',views.login, name="login"),
  path('registracija',views.register, name="register"),
  path('miskai',views.forests, name="forests"),
  path('nuotraukos',views.photos, name="photos"),
  path('image_upload', views.image_upload, name='image_upload'),
  path('miskas', views.forest, name='forest'),
]