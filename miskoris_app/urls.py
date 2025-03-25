from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib import admin
from . import views

urlpatterns=[
  path('admin/', admin.site.urls),  
  path('',views.home, name="home"),
  path('apie/',views.about, name="about"),
  path('prisijungimas/',views.loginPage, name="login"),
  path('atsijungimas/',views.logoutUser, name="logout"),
  path('registracija/',views.registerPage, name="register"),
  path('miskai/',views.forests, name="forests"),
  path('miskai/<int:id>/nuotraukos',views.photos, name="photos"),
  path('image_upload', views.image_upload, name='image_upload'),
  path('nuotraukos/', views.forests_gallery, name="forests_gallery"),
  path('miskai/<int:id>/', views.forest, name='forest'),
  path('zemelapis/', views.mapPage, name="map"),
  path('tikrinimai/<int:id>/', views.orders, name="orders"),
  path('tikrinimai/<int:forest_id>/<int:order_id>/tikrinimas/', views.order, name="order"),
  path('slaptazodzio_atkurimas/', auth_views.PasswordResetView.as_view(template_name="miskoris_app/password_reset.html"), name="reset_password"),
  path('atkurimo_laiskas_issiustas/', auth_views.PasswordResetDoneView.as_view(template_name="miskoris_app/password_reset_sent.html"), name="password_reset_done"),
  path('atkurimas/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="miskoris_app/password_reset_form.html"), name='password_reset_confirm'),
  path('slapazodis_atkurtas/', auth_views.PasswordResetCompleteView.as_view(template_name="miskoris_app/password_reset_done.html"), name='password_reset_complete')
]