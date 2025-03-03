from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def home(request):
  return render(request, "miskoris_app/home.html")

def about(request):
    return render(request, "miskoris_app/about.html")

def login(request):
    return render(request, "miskoris_app/login.html")

def register(request):
    return render(request, "miskoris_app/register.html")

def forests(request):
    return render(request, "miskoris_app/forests.html")