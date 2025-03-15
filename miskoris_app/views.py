from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Forest, Forest_image

from .forms import CreateUserForm

import json

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
                polygon_coords = request.POST.get('polygon_coords')

                if not name or not address or not area or not latitude or not longitude:
                    raise ValueError("All fields are required.")
                
                polygon_coords = json.loads(polygon_coords)

                Forest.objects.create(
                    user=request.user,
                    name=name,
                    address=address,
                    area=area,
                    latitude=latitude,
                    longitude=longitude,
                    polygon_coords=polygon_coords
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
    if request.method == 'POST':
        photo_ids = request.POST.getlist('photos_to_delete')
        if photo_ids:
            photo_ids = list(map(int, photo_ids))
            photos_to_delete = Forest_image.objects.filter(id__in=photo_ids)
            
            photos_to_delete.delete()

            messages.success(request, 'Nuotraukos sėkmingai pašalintos!')

        return redirect('photos', id=forest.id)

    photos = forest.images.all()  

    return render(request, 'miskoris_app/photos.html', {'forest': forest, 'photos': photos})

@login_required(login_url='login')
def image_upload(request):
    if request.method == 'POST' and request.FILES.getlist('images'):
        forest_id = request.POST.get('forest_id')
        forest = get_object_or_404(Forest, id=forest_id)
        images = request.FILES.getlist('images')

        allowed_extensions = ('.jpg', '.jpeg', '.png')

        for image in images:
            if not image.name.lower().endswith(allowed_extensions):
                messages.error(request, f"Netinkamas failas: {image.name}. Leidžiami tik JPEG ir PNG!")
                return render(request, 'miskoris_app/photos.html')

            image_data = image.read()
            forest_image = Forest_image(forest=forest, image=image_data)
            forest_image.save()

        messages.success(request, "Nuotraukos įkeltos sėkmingai!")
        return redirect('photos', id=forest_id)

    return render(request, 'miskoris_app/photos.html')

@login_required(login_url='login')
def mapPage(request):
    forests = Forest.objects.filter(user=request.user)
    
    # Prepare forest data with polygon coordinates
    forests_data = []
    for forest in forests:
        if forest.polygon_coords:
            forests_data.append({
                'id': forest.id,
                'name': forest.name,
                'polygon_coords': forest.polygon_coords
            })
    
    context = {
        'forests': forests,
        'forests_data': json.dumps(forests_data)
    }
    return render(request, "miskoris_app/map.html", context)

@login_required(login_url='login')
def forests_gallery(request):
    user = request.user

    forests = Forest.objects.filter(user=user)

    forests_images = {}
    for forest in forests:
        images = Forest_image.objects.filter(forest=forest)
        forests_images[forest] = images

    return render(request, 'miskoris_app/gallery.html', {'forests_images': forests_images})
