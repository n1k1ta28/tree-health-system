from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe
import re
from .forms import CreateUserForm, CustomPasswordChangeForm
from .decorators import unauthenticated_user
from .decorators import allowed_users
from .models import Forest, Forest_image, Order, Forest_document, AnalyzedPhoto

import json

import base64
import io
from PIL import Image, ExifTags
import numpy as np
from deepforest import main
import cv2
from scipy.stats import entropy

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

@login_required(login_url='login')
def profile(request):
    user = request.user
    # Determine the user's role
    if user.is_superuser:
        role = 'administrarotius'
    elif user.groups.exists():
        if user.groups.first().name == 'customer':
            role = 'klientas'
        if user.groups.first().name == 'staff':
            role = 'darbuotojas'
    else:
        role = 'nežinoma'  # Fallback, though unlikely due to registration logic

    if request.method == 'POST':
        form = CustomPasswordChangeForm(user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Slaptažodis sėkmingai pakeistas!')
            return redirect('profile')
        # If form is invalid, errors will be displayed in the template
    else:
        form = CustomPasswordChangeForm(user)

    context = {
        'role': role,
        'form': form,
    }
    return render(request, 'miskoris_app/profile.html', context)

@login_required(login_url='login')
def redirect_after_login(request):
    if request.user.is_superuser or request.user.groups.filter(name='customer').exists():
        return redirect('forests')
    elif request.user.groups.filter(name='staff').exists():
        return redirect('worker_orders')
    else:
        return redirect('home')

def redirect_after_cancellation(request):
        return redirect('login')

@unauthenticated_user
def loginPage(request):
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
            if user.is_superuser or user.groups.filter(name='customer').exists():
                return redirect('forests')
            elif user.groups.filter(name='staff').exists():
                return redirect('worker_orders')
        else:
            messages.info(request, 'Neteisingas prisijungimo vardas / el. paštas arba slaptažodis')

    context = {}
    return render(request, "miskoris_app/login.html", context)

def logoutUser(request):
    logout(request)
    return redirect('login')

@unauthenticated_user
def registerPage(request):
    form = CreateUserForm()

    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')

            group = Group.objects.get(name='customer')
            user.groups.add(group)

            messages.success(request, 'Sėkmingai sukurta paskyra naudotojui: ' + username)

            return redirect('login')

    context = {'form':form}
    return render(request, "miskoris_app/register.html", context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
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
@allowed_users(allowed_roles=['admin', 'customer'])
def forest(request, id):
    forest = get_object_or_404(Forest, id=id)

    latest_completed_order = (
        forest.orders.filter(status="completed", completed_at__isnull=False)
        .order_by("-completed_at")
        .first()
    )

    latest_completed_date = latest_completed_order.completed_at if latest_completed_order else None

    # Check if any AnalyzedPhoto has dry trees
    analyzed_photos = AnalyzedPhoto.objects.filter(forest=forest)

    has_dry_trees = "Ne" 
    dry_tree_pattern = re.compile(r"(\d+)\s+sausų\s+medžių")

    for photo in analyzed_photos:
        if photo.analysis_result:
            match = dry_tree_pattern.search(photo.analysis_result)
            if match:
                dry_tree_count = int(match.group(1))
                if dry_tree_count > 0:
                    has_dry_trees = "Taip"
                    break  

    polygon_coords = forest.polygon_coords or []  

    forest_data = json.dumps({
        "id": forest.id,
        "name": forest.name,
        "polygon_coords": polygon_coords,  
    })

    context = {
        "forest": forest,
        "forest_data": mark_safe(forest_data),
        "latest_completed_date": latest_completed_date,
        "has_dry_trees": has_dry_trees,
    }
    return render(request, "miskoris_app/forest.html", context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def photos(request, id):
    forest = get_object_or_404(Forest, id=id)
    if request.method == 'POST':
        # Handle deletion of regular photos
        photo_ids = request.POST.getlist('photos_to_delete')
        if photo_ids:
            photo_ids = list(map(int, photo_ids))
            photos_to_delete = Forest_image.objects.filter(id__in=photo_ids)
            photos_to_delete.delete()
            messages.success(request, 'Nuotraukos sėkmingai pašalintos!')

        # Handle deletion of analyzed photos
        analyzed_photo_ids = request.POST.getlist('analyzed_photos_to_delete')
        if analyzed_photo_ids:
            analyzed_photo_ids = list(map(int, analyzed_photo_ids))
            analyzed_photos_to_delete = AnalyzedPhoto.objects.filter(id__in=analyzed_photo_ids)
            analyzed_photos_to_delete.delete()
            messages.success(request, 'Analizuotos nuotraukos sėkmingai pašalintos!')

        if photo_ids or analyzed_photo_ids:
            return redirect('photos', id=forest.id)

    photos = forest.images.all()
    analyzed_photos = AnalyzedPhoto.objects.filter(forest=forest)
    return render(request, 'miskoris_app/photos.html', {
        'forest': forest,
        'photos': photos,
        'analyzed_photos': analyzed_photos
    })

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def image_upload(request):
    if request.method == 'POST' and request.FILES.getlist('images'):
        forest_id = request.POST.get('forest_id')
        forest = get_object_or_404(Forest, id=forest_id)
        images = request.FILES.getlist('images')
        allowed_extensions = ('.jpg', '.jpeg', '.png')

        for image in images:
            if not image.name.lower().endswith(allowed_extensions):
                messages.error(request, f"Netinkamas failas: {image.name}. Leidžiami tik JPEG ir PNG!")
                continue

            image_data = image.read()

            try:
                img = Image.open(io.BytesIO(image_data))
                exif_data = img._getexif()
                lat, lon = None, None
                if exif_data:
                    gps_info = exif_data.get(34853)
                    if gps_info:
                        lat = convert_to_degrees(gps_info.get(2)) 
                        lat_ref = gps_info.get(1)
                        lon = convert_to_degrees(gps_info.get(4))  
                        lon_ref = gps_info.get(3) 
                        if lat and lat_ref and lon and lon_ref:
                            lat = lat if lat_ref == 'N' else -lat
                            lon = lon if lon_ref == 'E' else -lon
            except Exception as e:
                print(f"Failed to extract GPS data for {image.name}: {e}")
                lat, lon = None, None

            forest_image = Forest_image(forest=forest, image=image_data)
            if lat and lon:
                forest_image.latitude = lat
                forest_image.longitude = lon
            forest_image.save()

        messages.success(request, "Nuotraukos sėkmingai įkeltos!")
        return redirect('photos', id=forest_id)

    return render(request, 'miskoris_app/photos.html')

def convert_to_degrees(value):
    """Convert GPS coordinates from (degrees, minutes, seconds) to decimal degrees."""
    if not value or len(value) != 3:
        return None
    d, m, s = value
    return d + (m / 60.0) + (s / 3600.0)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def dry_trees_map(request, id):
    forest = get_object_or_404(Forest, id=id)
    analyzed_photos = AnalyzedPhoto.objects.filter(forest=forest)
    
    dry_tree_locations = []
    for photo in analyzed_photos:
        if photo.analysis_result:
            match = re.search(r"(\d+)\s+sausų\s+medžių", photo.analysis_result)
            if match:
                dry_tree_count = int(match.group(1))
                if dry_tree_count > 0 and photo.original_image:
                    lat = photo.original_image.latitude
                    lon = photo.original_image.longitude
                    if lat and lon:
                        dry_tree_locations.append({
                            'lat': lat,
                            'lng': lon,
                            'count': dry_tree_count
                        })
    
    context = {
        'forest': forest,
        'dry_tree_locations': json.dumps(dry_tree_locations)
    }
    return render(request, 'miskoris_app/dry_trees_map.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
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
@allowed_users(allowed_roles=['admin', 'customer'])
def forests_gallery(request):
    user = request.user

    forests = Forest.objects.filter(user=user)

    forests_images = {}
    for forest in forests:
        images = Forest_image.objects.filter(forest=forest)
        forests_images[forest] = images

    return render(request, 'miskoris_app/gallery.html', {'forests_images': forests_images})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def orders(request, id):
    forest = get_object_or_404(Forest, id=id)

    orders = Order.objects.filter(forest=forest)

    if request.method == 'POST':
        forest_id = request.POST.get('forest_id')
        worker_id = 1

        forest = get_object_or_404(Forest, id=forest_id)

        # Create the order
        order = Order.objects.create(
            forest=forest,
            worker_id=worker_id if worker_id else None,
            created_at=timezone.now(),
            status='in_progress'
        )

        messages.success(request, "Tikrinimas užsakytas!")
        return redirect('orders', id=forest.id)

    return render(request, 'miskoris_app/orders.html', {'forest': forest, 'orders': orders})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def order(request, forest_id, order_id):
    order = get_object_or_404(Order, id=order_id)
    forest = get_object_or_404(Forest, id=forest_id)
    
    images = Forest_image.objects.filter(order=order)

    return render(request, 'miskoris_app/order.html', {'order': order, 'forest': forest, 'images': images})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def documents(request, id):
    forest = get_object_or_404(Forest, id=id, user=request.user)
    if request.method == 'POST':
        document_ids = request.POST.getlist('documents_to_delete')
        if document_ids:
            document_ids = list(map(int, document_ids))
            documents_to_delete = Forest_document.objects.filter(id__in=document_ids, forest=forest)
            documents_to_delete.delete()
            messages.success(request, 'Dokumentai sėkmingai pašalinti!')
        return redirect('documents', id=forest.id)

    documents = forest.documents.all()
    return render(request, 'miskoris_app/documents.html', {'forest': forest, 'documents': documents})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def document_upload(request):
    if request.method == 'POST':
        forest_id = request.POST.get('forest_id')
        forest = get_object_or_404(Forest, id=forest_id, user=request.user)
        documents = request.FILES.getlist('documents')

        for document in documents:
            document_data = document.read()
            original_filename = document.name
            Forest_document.objects.create(
                forest=forest,
                document=document_data,
                filename=original_filename
            )

        messages.success(request, "Dokumentai įkelti sėkmingai!")
        return redirect('documents', id=forest_id)

    return render(request, 'miskoris_app/documents.html')

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def forests_documents(request):
    user = request.user
    forests = Forest.objects.filter(user=user)
    return render(request, 'miskoris_app/documents_gallery.html', {'forests': forests})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def serve_document(request, document_id):
    document = get_object_or_404(Forest_document, id=document_id)
    response = HttpResponse(document.document, content_type='application/octet-stream')
    filename = document.filename if document.filename else f"document_{document_id}"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'staff'])
def worker_orders(request):
    #worker = request.user
    ongoing_orders = Order.objects.filter(status='in_progress') #worke=worker

    if request.method == 'POST' and request.FILES.getlist('images'):
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id, status='in_progress') #worker=worker
        forest = order.forest
        images = request.FILES.getlist('images')
        allowed_extensions = ('.jpg', '.jpeg', '.png')

        for image in images:
            if not image.name.lower().endswith(allowed_extensions):
                messages.error(request, f"Netinkamas failas: {image.name}. Leidžiami tik JPEG ir PNG!")
                return redirect('worker_orders')

            # Save the image linked to the order and forest
            image_data = image.read()
            forest_image = Forest_image(forest=forest, order=order, image=image_data)
            forest_image.save()

        # Update order status to completed
        order.status = 'completed'
        order.completed_at = timezone.now()
        order.bad_trees_found = False  # Default; update this logic if needed
        order.save()

        messages.success(request, "Nuotraukos sėkmingai įkeltos ir užsakymas užbaigtas!")
        return redirect('worker_orders')

    context = {
        'ongoing_orders': ongoing_orders,
    }
    return render(request, "miskoris_app/worker_orders.html", context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'staff'])
def worker_completed_orders(request):
    completed_orders = Order.objects.filter(status='completed') 

    context = {
        'completed_orders': completed_orders,
    }
    return render(request, "miskoris_app/worker_completed_orders.html", context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def analyze_forest_images(request, id):
    forest = get_object_or_404(Forest, id=id)
    # Get images that haven't been analyzed yet
    unanalyzed_images = Forest_image.objects.filter(forest=forest, analyzed_versions__isnull=True)

    for forest_image in unanalyzed_images:
        try:
            image_data = forest_image.image
            img = Image.open(io.BytesIO(image_data)).convert("RGB")
            img_resized = img.resize((500, 500), Image.Resampling.LANCZOS)
            image_array = np.array(img_resized)

            # Use the original image without enhancement
            predictions = model.predict_image(image=image_array, return_plot=False)
            
            if predictions is not None and not predictions.empty:
                dry_tree_count = 0
                for _, row in predictions.iterrows():
                    xmin, ymin, xmax, ymax = map(int, [row["xmin"], row["ymin"], row["xmax"], row["ymax"]])
                    score = row["score"]
                    is_dry = is_dry_tree(image_array, xmin, ymin, xmax, ymax)
                    label = "Sausas medis" if is_dry else "Medis"
                    color = (139, 69, 19) if is_dry else (0, 255, 0)
                    
                    cv2.rectangle(image_array, (xmin, ymin), (xmax, ymax), color, 2)
                    text = f"{label} ({score:.2f})"
                    cv2.putText(image_array, text, (xmin, ymin - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
                    if is_dry:
                        dry_tree_count += 1

                analysis_result = f"Surasta {len(predictions)} medžių, {dry_tree_count} sausų medžių"
            else:
                analysis_result = "Medžių nerasta"

            # Convert annotated image to bytes
            _, buffer = cv2.imencode('.png', cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR))
            
            # Save analyzed photo
            analyzed_photo = AnalyzedPhoto(
                forest=forest,
                image=buffer.tobytes(),
                analysis_result=analysis_result,
                original_image=forest_image
            )
            analyzed_photo.save()

        except Exception as e:
            messages.error(request, f"Nepavyko išanalizuoti nuotraukos ID {forest_image.id}: {str(e)}")
            continue

    messages.success(request, "Nuotraukos išanalizuotos sėkmingai!")
    return redirect('photos', id=forest.id)

# Initialize DeepForest model globally
model = main.deepforest()
model.use_release()


def is_dry_tree(image, xmin, ymin, xmax, ymax):
    """Check if a tree is dry with balanced green color detection."""
    # Extract the region of interest (ROI)
    roi = image[ymin:ymax, xmin:xmax]
    
    # Convert to HSV color space
    roi_hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    
    # Define HSV color ranges for dry trees (brown, yellow, and gray)
    brown_lower = np.array([0, 10, 20])    # Hue: 0-25 (brown), Sat: 10-150, Val: 20-200
    brown_upper = np.array([25, 150, 200])
    yellow_lower = np.array([25, 10, 20])  # Hue: 25-45 (pale yellow/beige), Sat: 10-150, Val: 20-200
    yellow_upper = np.array([45, 150, 200])
    gray_lower = np.array([0, 0, 20])      # Hue: 0-360 (gray), Sat: 0-40, Val: 20-200
    gray_upper = np.array([360, 40, 200])
    
    # Define balanced HSV range for healthy green trees
    green_lower = np.array([42, 25, 25])   # Hue: 42-125 (balanced green range), Sat: 25-255, Val: 25-255
    green_upper = np.array([125, 255, 255])
    
    # Create masks for brown, yellow, gray, and green pixels
    brown_mask = cv2.inRange(roi_hsv, brown_lower, brown_upper)
    yellow_mask = cv2.inRange(roi_hsv, yellow_lower, yellow_upper)
    gray_mask = cv2.inRange(roi_hsv, gray_lower, gray_upper)
    green_mask = cv2.inRange(roi_hsv, green_lower, green_upper)
    
    # Combine brown, yellow, and gray masks to detect dry pixels
    dry_mask = cv2.bitwise_or(brown_mask, yellow_mask)
    dry_mask = cv2.bitwise_or(dry_mask, gray_mask)
    
    # Calculate percentages of dry and green pixels
    total_pixels = roi.shape[0] * roi.shape[1]
    dry_pixel_count = np.sum(dry_mask > 0)
    green_pixel_count = np.sum(green_mask > 0)
    
    dry_percentage = (dry_pixel_count / total_pixels) * 100 if total_pixels > 0 else 0
    green_percentage = (green_pixel_count / total_pixels) * 100 if total_pixels > 0 else 0
    
    # Calculate mean HSV values
    mean_hue = np.mean(roi_hsv[:, :, 0])
    mean_saturation = np.mean(roi_hsv[:, :, 1])
    mean_value = np.mean(roi_hsv[:, :, 2])
    
    # Adjusted criteria for classifying a tree as dry:
    # 1. At least 15% of pixels must be in dry color ranges
    # 2. Less than 4% of pixels can be green (balanced threshold)
    # 3. At least 20 dry pixels to avoid noise in small ROIs
    primary_condition = (dry_percentage > 15) and (green_percentage < 4) and (dry_pixel_count > 20)
    
    # Fallback check using mean HSV values
    fallback_condition = (mean_hue < 45) and (mean_saturation < 100) and (20 < mean_value < 200)
    
    # Classify as dry if either the primary or fallback condition is met
    is_dry = primary_condition or (fallback_condition and green_percentage < 4)
    
    # Print debug information to diagnose issues
    print(f"ROI ({xmin}, {ymin}, {xmax}, {ymax}): Dry %: {dry_percentage:.2f}, Green %: {green_percentage:.2f}, Dry Pixels: {dry_pixel_count}, Mean Hue: {mean_hue:.2f}, Mean Sat: {mean_saturation:.2f}, Is Dry: {is_dry}")
    
    return is_dry