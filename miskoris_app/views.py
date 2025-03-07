from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.forms import UserCreationForm 

from .forms import CreateUserForm

# Create your views here.

def home(request):
  return render(request, "miskoris_app/home.html")

def about(request):
    return render(request, "miskoris_app/about.html")

def login(request):
    return render(request, "miskoris_app/login.html")

def register(request):
    form = CreateUserForm()

    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()

    context = {'form':form}
    return render(request, "miskoris_app/register.html", context)

def forests(request):
    return render(request, "miskoris_app/forests.html")

def photos(request):
    return render(request, "miskoris_app/photos.html")

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

def forest(request):
    return render(request, "miskoris_app/forest.html")
