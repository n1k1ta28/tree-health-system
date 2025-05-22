from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.urls import reverse
from django.views.decorators.http import require_POST
import re
from .forms import CreateUserForm, CustomPasswordChangeForm
from .decorators import unauthenticated_user
from .decorators import allowed_users
from .models import Forest, Forest_image, Order, Forest_document, AnalyzedPhoto, Subscription,Payment, ForestNote

import json

from dateutil.relativedelta import relativedelta

import base64
import io
from PIL import Image, ExifTags
import numpy as np
from deepforest import main
import cv2
from scipy.stats import entropy
import pandas as pd
# Create your views here.

def calculate_analysis_price(forest_size):
    if forest_size <= 20:
        return 70
    elif forest_size <= 40:
        return 90
    elif forest_size <= 80:
        return 120
    elif forest_size <= 150:
        return 170
    else:
        return 230

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
    if user.is_superuser:
        role = 'administrarotius'
    elif user.groups.exists():
        if user.groups.first().name == 'customer':
            role = 'klientas'
        if user.groups.first().name == 'staff':
            role = 'darbuotojas'
    else:
        role = 'nežinoma'  # mazai tiketina del registracijos logikos

    if request.method == 'POST':
        form = CustomPasswordChangeForm(user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  
            messages.success(request, 'Slaptažodis sėkmingai pakeistas!')
            return redirect('profile')
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
            user = User.objects.get(email=username_or_email)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=username_or_email)
            except User.DoesNotExist:
                user = None

        if user is None:
            messages.error(request, 'Neteisingas prisijungimo vardas / el. paštas arba slaptažodis')
        elif not user.check_password(password):
            messages.error(request, 'Neteisingas prisijungimo vardas / el. paštas arba slaptažodis')
        elif not user.is_active:
            messages.error(request, 'Prašome patvirtinti savo el. paštą')
        else:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            if user.is_superuser or user.groups.filter(name='customer').exists():
                return redirect('forests')
            elif user.groups.filter(name='staff').exists():
                return redirect('worker_orders')

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
            user = form.save(commit=False)
            user.is_active = False  # kol el. pastas nepatvirtintas, naudotojas neaktyvus
            user.save()
            username = form.cleaned_data.get('username')

            group = Group.objects.get(name='customer')
            user.groups.add(group)

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            verification_url = reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
            full_url = request.build_absolute_uri(verification_url)

            subject = 'Patvirtinkite savo el. paštą'
            message = f'Norėdami patvirtinti savo el. paštą, spustelėkite šią nuorodą: {full_url}'
            from_email = 'noreply@miskoris.com'
            recipient_list = [user.email]
            send_mail(subject, message, from_email, recipient_list)

            messages.success(request, 'Registracija naudotojui: ' + username + ' sėkminga. Patikrinkite savo el. paštą, kad patvirtintumėte paskyrą.')
            return redirect('login')

    context = {'form': form}
    return render(request, "miskoris_app/register.html", context)

def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Jūsų el. paštas patvirtintas. Dabar galite prisijungti.')
        return redirect('login')
    else:
        messages.error(request, 'Patvirtinimo nuoroda neteisinga arba pasibaigusi.')
        return redirect('home')

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

    subscription = Subscription.objects.filter(user=request.user, forest=forest, is_active=True).first()

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
        "subscription": subscription,
    }
    return render(request, "miskoris_app/forest.html", context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def subscribe_forest(request, id):
    forest = get_object_or_404(Forest, id=id, user=request.user)
    if request.method == 'POST' and request.POST.get('payment_confirmed') == 'true':
        payment_data = request.session.pop('pending_payment', None)
        if not payment_data:
            messages.error(request, "Prenumerata neapmokėta.")
            return redirect('subscribe_forest', id=forest.id)
       
        price = calculate_analysis_price(forest.area) * 6 * 0.85  # 15% discount for 6 months
        if float(payment_data['amount']) != round(price, 2):
            messages.error(request, "Neteisinga mokėjimo suma.")
            return redirect('subscribe_forest', id=forest.id)
        start_date = timezone.now().date()
        paid_until = start_date + relativedelta(months=6)
        subscription = Subscription.objects.create(
            user=request.user,
            forest=forest,
            start_date=start_date,
            paid_until=paid_until,
            is_active=True
        )
        Payment.objects.create(
            transaction_id=payment_data['transaction_id'],
            payer_email=payment_data['payer_email'],
            amount=payment_data['amount'],
            currency=payment_data['currency'],
            forest=forest,
            subscription=subscription
        )

        messages.success(request, "Sėkmingai užsisakėte prenumeratą!")
        return redirect('forest', id=forest.id)
    else:
        price = calculate_analysis_price(forest.area) * 6 * 0.85
        context = {'forest': forest, 'price': price}
        return render(request, 'miskoris_app/subscribe_confirm.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def cancel_subscription(request, id):
    forest = get_object_or_404(Forest, id=id, user=request.user)
    subscription = get_object_or_404(Subscription, user=request.user, forest=forest, is_active=True)
    if request.method == 'POST':
        subscription.is_active = False
        subscription.save()
        messages.success(request, "Prenumerata atšaukta.")
        return redirect('forest', id=forest.id)
    else:
        return render(request, 'miskoris_app/cancel_subscription_confirm.html', {'forest': forest})

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
    photos_uploaded_by_user = Forest_image.objects.filter(forest=forest, order_id__isnull=True).count()
    analyzed_photos = AnalyzedPhoto.objects.filter(forest=forest)
    return render(request, 'miskoris_app/photos.html', {
        'forest': forest,
        'photos': photos,
        'analyzed_photos': analyzed_photos,
        'photos_uploaded_by_user': photos_uploaded_by_user
    })

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def image_upload(request):
    if request.method == 'POST' and request.FILES.getlist('images'):
        forest_id = request.POST.get('forest_id')
        forest = get_object_or_404(Forest, id=forest_id)
        images = request.FILES.getlist('images')
        allowed_extensions = ('.jpg', '.jpeg', '.png')

        current_unassigned_count = Forest_image.objects.filter(forest=forest, order_id__isnull=True).count()

        max_upload_limit = 20

        if current_unassigned_count >= max_upload_limit:
            messages.error(request, "Pasiekėte maksimalų 20 nuotraukų limitą. Užsakykite tikrinimą norėdami išanalizuoti mišką.")
            return redirect('photos', id=forest_id)
        
        remaining_slots = max_upload_limit - current_unassigned_count

        if len(images) > remaining_slots:
            messages.error(request, f"Galite įkelti tik {remaining_slots} daugiau nuotraukų.")
            return redirect('photos', id=forest_id)

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
        if photo.analysis_result and not photo.fixed:
            match = re.search(r"(\d+)\s+sausų\s+medžių", photo.analysis_result)
            if match:
                dry_tree_count = int(match.group(1))
                if dry_tree_count > 0 and photo.original_image:
                    lat = photo.original_image.latitude
                    lon = photo.original_image.longitude
                    if lat and lon:
                        dry_tree_locations.append({
                            'id': photo.id,
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
def mark_tree_fixed(request, id):
    if request.method == 'POST':
        try:
            tree = AnalyzedPhoto.objects.get(id=id)
            tree.fixed = True
            tree.save()

            messages.success(request, "Sėkmingai sutvarkyta!")
            return JsonResponse({'status': 'success'})
        
        except AnalyzedPhoto.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Nerastas medis'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Negalimas iškvietimas'}, status=400)

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
    forests_data = [
        {
            'forest': forest,
            'images': Forest_image.objects.filter(forest=forest),
            'analyzed_photos': AnalyzedPhoto.objects.filter(forest=forest)
        }
        for forest in forests
    ]
    return render(request, 'miskoris_app/gallery.html', {'forests_data': forests_data})


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

        # Link payment from session if it exists
        payment_data = request.session.pop('pending_payment', None)
        if payment_data and payment_data.get('payment_type') == 'order':
            try:
                Payment.objects.create(
                    transaction_id=payment_data['transaction_id'],
                    payer_email=payment_data['payer_email'],
                    amount=payment_data['amount'],
                    currency=payment_data['currency'],
                    forest=forest,
                    order=order
                )
            except Exception as e:
                messages.warning(request, "Mokėjimo informacijos išsaugoti nepavyko.")

        messages.success(request, "Tikrinimas užsakytas!")
        return redirect('orders', id=forest.id)

    return render(request, 'miskoris_app/orders.html', {'forest': forest, 'orders': orders})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def store_payment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        request.session['pending_payment'] = {
            'transaction_id': data['transaction_id'],
            'payer_email': data['payer_email'],
            'amount': data['amount'],
            'currency': data['currency'],
            'forest_id': data['forest_id'],
            'payment_type': data.get('payment_type'),
            'subscription_id': data.get('subscription_id'),
        }
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def order(request, forest_id, order_id):
    order = get_object_or_404(Order, id=order_id)
    forest = get_object_or_404(Forest, id=forest_id)
    
    images = Forest_image.objects.filter(order=order)
    analyzed_photos = AnalyzedPhoto.objects.filter(original_image__in=images)
    
    return render(request, 'miskoris_app/order.html', {'order': order, 'forest': forest, 'images': images, 'analyzed_photos': analyzed_photos})


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
    ongoing_orders = Order.objects.filter(status='in_progress') #worker=worker

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

            image_data = image.read()
            forest_image = Forest_image(forest=forest, order=order, image=image_data)
            forest_image.save()

        order.status = 'completed'
        order.completed_at = timezone.now()
        order.bad_trees_found = False  # Default; update this logic if needed
        order.save()

        if order.forest.user.email:
            subject = 'Užsakymas užbaigtas'
            message = (
                f'Jūsų užsakymas miškui {order.forest.name} buvo užbaigtas. '
                f'Galite peržiūrėti rezultatus čia: '
                f'{request.build_absolute_uri(reverse("order", args=[order.forest.id, order.id]))}'
            )
            from_email = 'noreply@miskorius.com'
            recipient_list = [order.forest.user.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=True)
            except Exception as e:
                print(f"Failed to send email: {e}")

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
def forest_notes(request, id):
    forest = get_object_or_404(Forest, id=id, user=request.user)
    notes = forest.notes.all().order_by('-created_at')
    
    if request.method == 'POST':
        if 'add_note' in request.POST:
            note_text = request.POST.get('note')
            if note_text:
                ForestNote.objects.create(forest=forest, note=note_text)
                messages.success(request, 'Užrašas pridėtas sėkmingai!')
            else:
                messages.error(request, 'Užrašas negali būti tuščias.')
        elif 'delete_note' in request.POST:
            note_id = request.POST.get('note_id')
            try:
                note = forest.notes.get(id=note_id)
                note.delete()
                messages.success(request, 'Užrašas ištrintas sėkmingai!')
            except ForestNote.DoesNotExist:
                messages.error(request, 'Užrašas nerastas.')
        
        return redirect('forest_notes', id=forest.id)
    
    context = {
        'forest': forest,
        'notes': notes,
    }
    return render(request, 'miskoris_app/forest_notes.html', context)

# Initialize DeepForest model
model = main.deepforest()
model.use_release()

def is_dry_tree(image, xmin, ymin, xmax, ymax):

    roi = image[ymin:ymax, xmin:xmax]
    if roi.size == 0:
        return False
    
    roi_hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    roi_rgb = roi
    
    mean_saturation = np.mean(roi_hsv[:,:,1])
    mean_value = np.mean(roi_hsv[:,:,2])
    mean_r = np.mean(roi_rgb[:,:,0])
    mean_g = np.mean(roi_rgb[:,:,1])
    mean_b = np.mean(roi_rgb[:,:,2])
    
    green_lower = np.array([42, 25, 25])
    green_upper = np.array([125, 255, 255])
    green_mask = cv2.inRange(roi_hsv, green_lower, green_upper)
    total_pixels = roi.shape[0] * roi.shape[1]
    green_percentage = (np.sum(green_mask > 0) / total_pixels) * 100 if total_pixels > 0 else 0
    
    is_not_too_green = mean_g < mean_r or mean_g < mean_b or mean_g < 145
    is_brownish = mean_r > mean_g and mean_r > mean_b and mean_r > 55
    is_mixed = (mean_r > mean_g) and (mean_r - mean_g < 50) and (mean_g > 35)
    is_reasonable_saturation = mean_saturation < 75
    is_reasonable_brightness = 30 < mean_value < 180
    is_low_green = green_percentage < 10
    
    return (is_not_too_green and (is_brownish or is_mixed) and is_low_green and
            is_reasonable_saturation and is_reasonable_brightness)

def analyze_images(images):
    for forest_image in images:
        try:
            print(f"Processing image ID {forest_image.id}")
            image_data = forest_image.image
            img = Image.open(io.BytesIO(image_data)).convert("RGB")
            img_resized = img.resize((500, 500), Image.Resampling.LANCZOS)
            image_array = np.array(img_resized)
            predictions = model.predict_image(image=image_array, return_plot=False)
            if predictions is not None and not predictions.empty:
                predictions = predictions[predictions["score"] > 0.1]
            print(f"Image ID {forest_image.id}: Detected {len(predictions)} trees")
            if predictions is not None and not predictions.empty:
                dry_tree_count = 0
                for _, row in predictions.iterrows():
                    xmin, ymin, xmax, ymax = map(int, [row["xmin"], row["ymin"], row["xmax"], row["ymax"]])
                    score = row["score"]
                    is_dry = is_dry_tree(image_array, xmin, ymin, xmax, ymax)
                    label = "Sausas medis" if is_dry else "Medis"
                    color = (139, 69, 19) if is_dry else (0, 255, 0)
                    outer_color = (100, 50, 10) if is_dry else (0, 200, 0)
                    cv2.rectangle(image_array, (xmin, ymin), (xmax, ymax), color, 2)
                    cv2.rectangle(image_array, (xmin-2, ymin-2), (xmax+2, ymax+2), outer_color, 1)
                    text = f"{label} ({score:.2f})"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.4
                    text_size, _ = cv2.getTextSize(text, font, font_scale, 1)
                    text_w, text_h = text_size
                    bg_x, bg_y = xmin, ymin - text_h - 6
                    bg_x2, bg_y2 = bg_x + text_w + 2, bg_y + text_h + 2
                    overlay = image_array.copy()
                    cv2.rectangle(overlay, (bg_x, bg_y), (bg_x2, bg_y2), color, -1)
                    alpha = 0.5
                    cv2.addWeighted(overlay, alpha, image_array, 1 - alpha, 0, image_array)
                    cv2.putText(image_array, text, (bg_x + 1, bg_y + text_h), font,
                               font_scale, (255, 255, 255), 1, cv2.LINE_AA)
                    if is_dry:
                        dry_tree_count += 1
                analysis_result = f"Surasta {len(predictions)} medžių, {dry_tree_count} sausų medžių"
            else:
                analysis_result = "Medžių nerasta"
            _, buffer = cv2.imencode('.png', cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR))
            analyzed_photo = AnalyzedPhoto(
                forest=forest_image.forest,
                image=buffer.tobytes(),
                analysis_result=analysis_result,
                original_image=forest_image
            )
            analyzed_photo.save()
        except Exception as e:
            print(f"Error processing image ID {forest_image.id}: {str(e)}")

def analyze_single_forest(forest):
    unanalyzed_images = Forest_image.objects.filter(forest=forest, analyzed_versions__isnull=True) 
    analyze_images(unanalyzed_images)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
@require_POST
def analyze_forest_images(request, id):
    forest = get_object_or_404(Forest, id=id)
    analyze_single_forest(forest)
    messages.success(request, "Nuotraukos išanalizuotos sėkmingai!")
    return redirect('photos', id=forest.id)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
@require_POST
def analyze_order_images(request, forest_id, order_id):
    order = get_object_or_404(Order, id=order_id)
    forest = get_object_or_404(Forest, id=forest_id)
    images = Forest_image.objects.filter(order=order, analyzed_versions__isnull=True) 
    analyze_images(images)
    messages.success(request, "Užsakymo nuotraukos išanalizuotos sėkmingai!")
    return redirect('order', forest_id=forest_id, order_id=order_id)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
@require_POST
def analyze_all_forests(request):
    forests = Forest.objects.filter(user=request.user)
    for forest in forests:
        analyze_single_forest(forest)
    messages.success(request, "Visų miškų nuotraukos išanalizuotos sėkmingai!")
    return redirect('forests_gallery')