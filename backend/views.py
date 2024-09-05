from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncMonth, TruncDay
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET
from datetime import datetime, timedelta

from backend.models import GalleryImage, Service, User, Appointment
from django.db.models import Count, Max


def user_login(request):
    # Check if the user is already authenticated
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('dashboard')  # Redirect to the dashboard if logged in

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Authenticate the user
        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.is_superuser:  # Check if the user has admin privileges
                login(request, user)
                return redirect('dashboard')  # Redirect to the admin dashboard or desired page
            else:
                messages.error(request, 'You do not have permission to access this page.')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')


@login_required(login_url='login')
def user_logout(request):
    logout(request)
    return redirect('login')  # Redirect to the login page after logout


def get_operating_hours(date):
    """
    Returns the operating hours for a given date.
    """
    if date.weekday() == 6:  # Sunday
        return datetime.combine(date, datetime.min.time().replace(hour=9, minute=0)), \
               datetime.combine(date, datetime.min.time().replace(hour=12, minute=0))
    else:  # Monday to Saturday
        return datetime.combine(date, datetime.min.time().replace(hour=8, minute=30)), \
               datetime.combine(date, datetime.min.time().replace(hour=16, minute=0))


@require_GET
def get_available_time_slots(request):
    service_id = request.GET.get('service_id')
    date = request.GET.get('date')

    service = Service.objects.get(pk=service_id)
    selected_date = datetime.strptime(date, '%Y-%m-%d').date()

    # Get operating hours for the selected date
    start_time, end_time = get_operating_hours(selected_date)

    # Get all appointments for the selected date
    appointments = Appointment.objects.filter(date=selected_date).order_by('start_time')

    # Create a list of busy time slots
    busy_slots = [(datetime.combine(selected_date, apt.start_time),
                   datetime.combine(selected_date, apt.end_time))
                  for apt in appointments]

    available_slots = []
    current_time = start_time

    while current_time + timedelta(minutes=service.duration) <= end_time:
        slot_end = current_time + timedelta(minutes=service.duration)
        is_available = True

        for busy_start, busy_end in busy_slots:
            if (current_time < busy_end and slot_end > busy_start):
                is_available = False
                current_time = busy_end
                break

        if is_available:
            available_slots.append({
                'start': current_time.strftime('%I:%M %p'),
                'end': slot_end.strftime('%I:%M %p')
            })
            current_time += timedelta(minutes=service.duration)
        elif not is_available and current_time == busy_end:
            # If we've jumped to the end of a busy slot, don't increment further
            continue
        else:
            # If not available and not at the end of a busy slot, increment by the service duration
            current_time += timedelta(minutes=service.duration)

    return JsonResponse({'available_slots': available_slots})


@login_required(login_url='login')
def view_dashboard(request):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    if request.method == 'POST':
        # Handle the form submission
        user_id = request.POST.get('user')
        service_id = request.POST.get('service')
        date = request.POST.get('date')
        time_slot = request.POST.get('time_slot')
        status = request.POST.get('status')

        # Assuming that user_id and service_id refers to the User and Service model's primary key
        user = User.objects.get(pk=user_id)
        service = Service.objects.get(pk=service_id)

        # Parse the time slot
        start_time, end_time = time_slot.split(' - ')
        start_time = datetime.strptime(start_time, '%I:%M %p').time()
        end_time = datetime.strptime(end_time, '%I:%M %p').time()

        # Create the appointment
        appointment = Appointment(
            user=user,
            service=service,
            date=date,
            start_time=start_time,
            end_time=end_time,
            status=status
        )
        appointment.save()
        messages.success(request, 'Appointment added successfully.')
        return redirect('dashboard')

    # Retrieve all data
    now = timezone.now()
    today = now.date()

    all_appointments = Appointment.objects.count()
    todays_appointments = Appointment.objects.filter(date=today).count()
    pending_appointments = Appointment.objects.filter(status='Pending').count()
    approved_appointments = Appointment.objects.filter(status='Approved').count()
    cancelled_appointments = Appointment.objects.filter(status='Cancelled').count()

    # Determine start date for the 12-month range
    latest_date = Appointment.objects.aggregate(latest=Max('date'))['latest']
    start_date = (latest_date - timedelta(days=365) if latest_date else now - timedelta(days=365))

    # Aggregate monthly appointment data
    monthly_data = (Appointment.objects.filter(date__gte=start_date, status='Approved')
                    .annotate(month=TruncMonth('date'))
                    .values('month')
                    .annotate(total=Count('id'))
                    .order_by('month'))

    # Prepare data for the chart
    months = [data['month'].strftime('%B %Y') for data in monthly_data]
    monthly_totals = [data['total'] for data in monthly_data]

    # Calculate the start date for the last 7 days
    start_date_7_days = today - timedelta(days=7)

    # Query the database to aggregate daily appointment data
    daily_data = (Appointment.objects.filter(date__range=[start_date_7_days, today], status='Approved')
                  .annotate(day=TruncDay('date'))
                  .values('day')
                  .annotate(total=Count('id'))
                  .order_by('day'))

    # Prepare data for the chart
    days = [data['day'].strftime('%A') for data in daily_data]
    daily_totals = [data['total'] for data in daily_data]

    context = {
        'users': User.objects.filter(is_superuser=False, email_verified=True),
        'services': Service.objects.all(),
        'appointments': Appointment.objects.all(),
        'all_appointments': all_appointments,
        'todays_appointments': todays_appointments,
        'pending_appointments': pending_appointments,
        'approved_appointments': approved_appointments,
        'cancelled_appointments': cancelled_appointments,
        'months': months,
        'monthly_totals': monthly_totals,
        'days': days,
        'daily_totals': daily_totals,
    }

    return render(request, 'dashboard.html', context)


@login_required(login_url='login')
def upload_image(request):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    if request.method == 'POST':
        image = request.FILES.get('image')
        gallery_image = GalleryImage(image=image)
        gallery_image.save()
        messages.success(request, 'Image uploaded successfully.')
        return redirect('gallery')

    images = GalleryImage.objects.all()
    return render(request, 'gallery.html', {'images': images})


@login_required(login_url='login')
def delete_image(request, image_id):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    image = GalleryImage.objects.get(pk=image_id)
    image.delete()
    messages.success(request, 'Image deleted successfully.')
    return redirect('gallery')


@login_required(login_url='login')
def service_operations(request):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    if request.method == 'POST':
        # Check if an 'id' is provided to identify if it's an edit operation
        service_id = request.POST.get('service_id')

        # Add or Update Service
        if service_id:
            # Editing an existing service
            service = Service.objects.get(pk=service_id)
            title = request.POST.get('title')
            description = request.POST.get('description')
            duration = request.POST.get('duration')
            image = request.FILES.get('image')

            # Update the service fields
            service.title = title
            service.description = description
            service.duration = int(duration)

            # Only update image if a new file is uploaded
            if image:
                service.image = image

            # Save the updated service
            service.save()

            messages.success(request, 'Service updated successfully!')
        else:
            # Adding a new service
            title = request.POST.get('title')
            description = request.POST.get('description')
            duration = request.POST.get('duration')
            image = request.FILES.get('image')

            # Create a new Service instance
            service = Service(
                title=title,
                description=description,
                duration=int(duration),
                image=image
            )
            service.save()

            messages.success(request, 'Service added successfully!')

        return redirect('services')  # Redirect to the services page

    services = Service.objects.all()
    return render(request, 'services.html', {'services': services})


@login_required(login_url='login')
def delete_service(request, service_id):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    service = Service.objects.get(pk=service_id)
    service.delete()
    messages.success(request, 'Service deleted successfully.')
    return redirect('services')


@login_required(login_url='login')
def view_accounts(request):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    users = User.objects.filter(is_superuser=False, email_verified=True)  # Retrieve all user records

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        sex = request.POST.get('sex')
        current_address = request.POST.get('current_address')
        birthday = request.POST.get('birthday')
        age = request.POST.get('age')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('accounts')

        # Check if the email is already taken
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already registered.')
            return redirect('accounts')

        # Create a new user if email is unique
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            sex=sex,
            current_address=current_address,
            birthday=birthday,
            age=age,
            email_verified=True,
        )
        user.set_password(password)
        user.save()
        messages.success(request, 'User registered successfully!')
        return redirect('accounts')

    return render(request, 'accounts.html', {'users': users})


@login_required(login_url='login')
def delete_user(request, user_id):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    user = User.objects.get(pk=user_id)
    user.delete()
    messages.success(request, 'User deleted successfully.')
    return redirect('accounts')


@login_required(login_url='login')
def user_details(request, user_id):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    user = User.objects.get(pk=user_id)
    appointments = Appointment.objects.filter(user_id=user_id)
    services = Service.objects.all()  # Assuming you have a Service model

    if request.method == 'POST':
        if 'service' in request.POST:
            # Extract appointment data from POST request
            service_id = request.POST.get('service')
            appointment_date = request.POST.get('date')
            appointment_time_slot = request.POST.get('time_slot')
            appointment_status = request.POST.get('status')

            service = Service.objects.get(pk=service_id)

            # Parse the time slot
            start_time, end_time = appointment_time_slot.split(' - ')
            start_time = datetime.strptime(start_time, '%I:%M %p').time()
            end_time = datetime.strptime(end_time, '%I:%M %p').time()

            # Create and save the new appointment
            appointment = Appointment(
                user=user,
                service=service,
                date=appointment_date,
                start_time=start_time,
                end_time=end_time,
                status=appointment_status
            )
            appointment.save()
            messages.success(request, 'Appointment created successfully!')

        else:
            # Existing code for updating user details
            new_first_name = request.POST.get('first_name')
            new_last_name = request.POST.get('last_name')
            new_email = request.POST.get('email')
            new_phone_number = request.POST.get('phone_number')
            new_sex = request.POST.get('sex')
            new_current_address = request.POST.get('current_address')
            new_birthday = request.POST.get('birthday')
            new_age = request.POST.get('age')
            new_password = request.POST.get('password')
            confirm_new_password = request.POST.get('confirm_password')

            # Check if the new email is already taken by another user
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                messages.error(request, 'Email is already registered.')
                return redirect('user_details', user_id)

            # Update user details
            user.first_name = new_first_name
            user.last_name = new_last_name
            user.email = new_email
            user.phone_number = new_phone_number
            user.sex = new_sex
            user.current_address = new_current_address
            user.birthday = new_birthday
            user.age = new_age
            user.email_verified = True

            # Check if passwords are being updated
            if new_password:
                # Check if passwords match
                if new_password != confirm_new_password:
                    messages.error(request, 'Passwords do not match.')
                    return redirect('user_details', user_id)
                user.set_password(new_password)

            user.save()
            messages.success(request, 'User details updated successfully!')
            return redirect('user_details', user_id)  # Redirect back to the accounts list

    context = {
        'user': user,
        'appointments': appointments,
        'services': services,  # Include services in the context for the form
    }
    return render(request, 'user_details.html', context)


@login_required(login_url='login')
def delete_appointment(request, appointment_id):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    appointment = Appointment.objects.get(pk=appointment_id)
    appointment.delete()
    messages.success(request, 'Appointment deleted successfully.')

    # Get the URL of the referring page
    referer = request.META.get('HTTP_REFERER', '/')
    # Redirect back to the referring page
    return HttpResponseRedirect(referer)


@login_required(login_url='login')
def update_appointment_status(request, appointment_id):
    # Check if the user is not admin
    if not request.user.is_superuser:
        return redirect('login')

    if request.method == 'POST':
        appointment = Appointment.objects.get(pk=appointment_id)
        status = request.POST.get('status')
        appointment.status = status
        appointment.save()
        messages.success(request, 'Appointment status updated successfully.')

    # Get the URL of the referring page
    referer = request.META.get('HTTP_REFERER', '/')
    # Redirect back to the referring page
    return HttpResponseRedirect(referer)
