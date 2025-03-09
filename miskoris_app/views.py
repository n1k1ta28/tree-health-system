from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from .forms import CreateUserForm

# Create your views here.

def home(request):
  return render(request, "miskoris_app/home.html")

def about(request):
    return render(request, "miskoris_app/about.html")

# Prisijungimas tik su vartotojo vardu
# def loginPage(request):
#     if request.user.is_authenticated:
#         return redirect('home')
#     else:
#         if request.method == 'POST':
#             username = request.POST.get('username')
#             password = request.POST.get('password')

#             user = authenticate(request, username=username, password=password)

#             if user is not None:
#                 login(request, user)
#                 return redirect('forests')
#             else:
#                 messages.info(request, 'Neteisingas prisijungimo vardas arba slaptažodis')

#         context = {}
#         return render(request, "miskoris_app/login.html", context)

# Prisijungimas su vartotojo vardu arba el. pastu
def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        if request.method == 'POST':
            username_or_email = request.POST.get('username')
            password = request.POST.get('password')

            user = None

            try:
                user_by_email = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_by_email.username, password=password)
            except User.DoesNotExist:
                user = authenticate(request, username=username_or_email, password=password)

            if user is not None:
                login(request, user)
                return redirect('forests')
            else:
                messages.info(request, 'Neteisingas prisijungimo vardas / el. paštas arba slaptažodis')

        context = {}
        return render(request, "miskoris_app/login.html", context)

def logoutUser(request):
    logout(request)
    return redirect('login')

def registerPage(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        form = CreateUserForm()

        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                form.save()
                user = form.cleaned_data.get('username')
                messages.success(request, 'Sėkmingai sukurta paskyra naudotojui: ' + user)

                return redirect('login')

        context = {'form':form}
        return render(request, "miskoris_app/register.html", context)

@login_required(login_url='login')
def forests(request):
    return render(request, "miskoris_app/forests.html")

@login_required(login_url='login')
def photos(request):
    return render(request, "miskoris_app/photos.html")

@login_required(login_url='login')
def image_upload(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        
        # Check the file type for jpeg, jpg, and png
        if not image.name.endswith(('.jpeg', '.png')):
            messages.error(request, "Leidžiami tik JPEG ir PNG vaizdai!")
            return render(request, 'miskoris_app/photos.html')

        fs = FileSystemStorage()
        filename = fs.save(image.name, image)  
        uploaded_file_url = fs.url(filename)   

    return render(request, 'miskoris_app/photos.html', {'uploaded_file_url': uploaded_file_url})

@login_required(login_url='login')
def forest(request):
    return render(request, "miskoris_app/forest.html")
