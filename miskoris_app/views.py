from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Forest, Forest_image

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
    if request.method == 'POST':
        try:
            if 'delete_id' in request.POST:
                print("Received POST data:", request.POST)
                forest_id = request.POST.get('delete_id')
                forest = get_object_or_404(Forest, id=forest_id, user=request.user)
                forest.delete()
                messages.success(request, 'Miškas sėkmingai ištrintas!')
            else:
                name = request.POST.get('name')
                address = request.POST.get('address')
                area = request.POST.get('area')
                latitude = request.POST.get('latitude')
                longitude = request.POST.get('longitude')

                if not name or not address or not area or not latitude or not longitude:
                    raise ValueError("All fields are required.")

                Forest.objects.create(
                    user=request.user,
                    name=name,
                    address=address,
                    area=area,
                    latitude=latitude,
                    longitude=longitude
                )

                messages.success(request, 'Miškas pridėtas sėkmingai!')


            return redirect('forests')

        except Exception as e:
            print(f"Klaida: {e}")
            messages.error(request, f"Nepavyko atlikti operacijos: {e}")
            return redirect('forests')

    forests = Forest.objects.filter(user=request.user)
    return render(request, "miskoris_app/forests.html", {'forests': forests})


@login_required(login_url='login')
def forest(request, id):
    forest = get_object_or_404(Forest, id=id)
    return render(request, "miskoris_app/forest.html", {'forest': forest})

@login_required(login_url='login')
def photos(request, id):
    forest = get_object_or_404(Forest, id=id)
    photos = forest.images.all()  

    return render(request, 'miskoris_app/photos.html', {'forest': forest, 'photos': photos})

@login_required(login_url='login')
def image_upload(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        
        if not image.name.endswith(('.jpeg', '.png')):
            messages.error(request, "Leidžiami tik JPEG ir PNG vaizdai!")
            return render(request, 'miskoris_app/photos.html')

        image_data = image.read()

        forest_id = request.POST.get('forest_id')
        forest = Forest.objects.get(id=forest_id)

        forest_image = Forest_image(forest=forest, image=image_data)
        forest_image.save()

        messages.success(request, "Nuotrauka įkelta sėkmingai!")

        return redirect('photos', id=forest_id)

    return render(request, 'miskoris_app/photos.html')



