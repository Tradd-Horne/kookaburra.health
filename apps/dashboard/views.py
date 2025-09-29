"""
Dashboard views for non-superuser interface.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, Http404
import csv
from datetime import datetime, timedelta
import pytz
from django.db.models import Q, Count, F, ExpressionWrapper, IntegerField
from django.utils import timezone as django_timezone
from collections import defaultdict

from api.models import GoogleDriveFolder, Booking, IngestionRun


@login_required
def dashboard_home(request):
    """Dashboard home page."""
    return render(request, 'dashboard/home.html')


@login_required
def flows(request):
    """Flows management page."""
    return render(request, 'dashboard/flows.html')


@login_required
def user_settings(request):
    """User settings page with password change."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('dashboard:settings')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'dashboard/settings.html', {
        'form': form
    })


@login_required
def folder_bookings(request, folder_name):
    """Bookings data page for a specific watched folder."""
    
    # Get the folder for the current user
    folder = get_object_or_404(
        GoogleDriveFolder, 
        folder_name=folder_name, 
        user=request.user,
        is_active=True
    )
    
    # Handle export request
    if request.GET.get('export') == 'csv':
        return export_bookings_csv(request, folder)
    
    # Get all bookings for this user only
    bookings_queryset = Booking.objects.filter(
        user=request.user,
        ingestion_run__folder=folder
    ).select_related('ingestion_run').order_by('arrive_date', '-created_at')
    
    # Apply filters
    search_query = request.GET.get('search', '').strip()
    booking_status = request.GET.get('booking_status', '')
    import_status = request.GET.get('import_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if search_query:
        bookings_queryset = bookings_queryset.filter(
            Q(booking_number__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(surname__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if booking_status:
        bookings_queryset = bookings_queryset.filter(status=booking_status)
    
    if import_status:
        bookings_queryset = bookings_queryset.filter(ingestion_run__status=import_status)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            bookings_queryset = bookings_queryset.filter(arrive_date__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            bookings_queryset = bookings_queryset.filter(arrive_date__lte=to_date)
        except ValueError:
            pass
    
    # Pagination
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(bookings_queryset, per_page)
    page_number = request.GET.get('page')
    bookings = paginator.get_page(page_number)
    
    # Get summary statistics
    total_bookings = bookings_queryset.count()
    recent_imports = IngestionRun.objects.filter(
        folder=folder,
        completed_at__isnull=False
    ).order_by('-completed_at')[:5]
    
    # Get unique booking statuses for filter dropdown (user-specific)
    booking_statuses = Booking.objects.filter(
        user=request.user,
        ingestion_run__folder=folder
    ).values_list('status', flat=True).distinct().order_by('status')
    
    # Queensland timezone for display
    qld_tz = pytz.timezone('Australia/Brisbane')
    
    context = {
        'folder': folder,
        'bookings': bookings,
        'total_bookings': total_bookings,
        'recent_imports': recent_imports,
        'booking_statuses': booking_statuses,
        'current_filters': {
            'search': search_query,
            'booking_status': booking_status,
            'import_status': import_status,
            'date_from': date_from,
            'date_to': date_to,
            'per_page': per_page,
        },
        'qld_tz': qld_tz,
    }
    
    return render(request, 'dashboard/folder_bookings.html', context)


def export_bookings_csv(request, folder):
    """Export bookings data as CSV."""
    
    # Get filtered bookings for this user only (same filtering logic as main view)
    bookings_queryset = Booking.objects.filter(
        user=request.user,
        ingestion_run__folder=folder
    ).select_related('ingestion_run').order_by('arrive_date', '-created_at')
    
    # Apply same filters as the main view
    search_query = request.GET.get('search', '').strip()
    booking_status = request.GET.get('booking_status', '')
    import_status = request.GET.get('import_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if search_query:
        bookings_queryset = bookings_queryset.filter(
            Q(booking_number__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(surname__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if booking_status:
        bookings_queryset = bookings_queryset.filter(status=booking_status)
    
    if import_status:
        bookings_queryset = bookings_queryset.filter(ingestion_run__status=import_status)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            bookings_queryset = bookings_queryset.filter(arrive_date__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            bookings_queryset = bookings_queryset.filter(arrive_date__lte=to_date)
        except ValueError:
            pass
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{folder.folder_name}_bookings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Booking Number', 'Status', 'Guest Name', 'Company', 'Email', 'Mobile',
        'Arrive Date', 'Depart Date', 'Room Number', 'Room Type', 
        'Total Amount', 'Balance', 'Deposit Required', 'Region', 'Agent',
        'Import Date', 'Import Status', 'Source File'
    ])
    
    # Write data rows
    qld_tz = pytz.timezone('Australia/Brisbane')
    for booking in bookings_queryset:
        guest_name = f"{booking.first_name} {booking.surname}".strip()
        import_date = booking.ingestion_run.completed_at.astimezone(qld_tz).strftime('%d-%m-%Y %H:%M') if booking.ingestion_run.completed_at else 'Processing'
        
        writer.writerow([
            booking.booking_number,
            booking.status,
            guest_name,
            booking.company,
            booking.email,
            booking.mobile,
            booking.arrive_date.strftime('%d-%m-%Y') if booking.arrive_date else '',
            booking.depart_date.strftime('%d-%m-%Y') if booking.depart_date else '',
            booking.room_number,
            booking.room_type,
            booking.total_amount,
            booking.balance,
            booking.deposit_required,
            booking.region,
            booking.agent,
            import_date,
            booking.ingestion_run.status,
            booking.ingestion_run.filename,
        ])
    
    return response


@login_required
def guest_extra_night_workflow(request):
    """Guest Extra Night Workflow Management Page."""
    
    # Try to get the connected database from the request parameter or default to SALT-DATA
    connected_folder_name = request.GET.get('database', 'SALT-DATA')
    
    try:
        # First, try to find the folder for the current user
        connected_folder = GoogleDriveFolder.objects.filter(
            folder_name=connected_folder_name,
            user=request.user,
            is_active=True
        ).first()
        
        if not connected_folder:
            # If not found for current user, try to find any folder with that name
            # (for demo purposes, in production you'd handle permissions differently)
            connected_folder = GoogleDriveFolder.objects.filter(
                folder_name=connected_folder_name,
                is_active=True
            ).first()
            
            if not connected_folder:
                # Try to find any available folder for this user
                available_folders = GoogleDriveFolder.objects.filter(
                    user=request.user,
                    is_active=True
                )
                
                if available_folders.exists():
                    connected_folder = available_folders.first()
                else:
                    return render(request, 'dashboard/guest_extra_night_workflow.html', {
                        'error': 'No database available. Please set up a Google Drive folder watch first in the Flows section.'
                    })
    except Exception as e:
        return render(request, 'dashboard/guest_extra_night_workflow.html', {
            'error': f'Database connection error: {str(e)}'
        })
    
    # Get current date for calculations
    today = django_timezone.now().date()
    
    # Step 1: Identify eligible guests (checkout Sunday, staying > 2 nights)
    # Django week_day: 1=Sunday, 2=Monday, 3=Tuesday, 4=Wednesday, 5=Thursday, 6=Friday, 7=Saturday
    # Look for bookings that check out on Sunday and stay more than 2 nights
    
    eligible_guests = Booking.objects.filter(
        user=request.user,  # Only show current user's bookings
        ingestion_run__folder=connected_folder,
        arrive_date__isnull=False,
        depart_date__isnull=False,
        depart_date__week_day=1,  # Sunday checkout (Django: 1=Sunday)
        arrive_date__gte=today,   # Future bookings only
        status__in=['Booking', 'Confirmed']  # Active bookings
    ).extra(
        where=["depart_date - arrive_date > 2"]
    ).order_by('arrive_date')[:20]  # Limit to next 20 for demo
    
    # Calculate workflow flags for each guest
    workflow_guests = []
    for booking in eligible_guests:
        # Calculate days until check-in
        days_until_checkin = (booking.arrive_date - today).days
        
        # Determine workflow flags
        t14_eligible = days_until_checkin == 14  # Exactly 14 days before
        t1_eligible = days_until_checkin == 1    # Exactly 1 day before
        in_window = 1 <= days_until_checkin <= 14  # In the window for offers
        
        # Mock workflow status (in real implementation, this would be stored in database)
        workflow_status = 'pending'  # pending, t14_sent, t1_sent, accepted, declined, completed
        offer_type = None  # extra_night, late_checkout
        
        # Determine next action
        if days_until_checkin > 14:
            next_action = f"Monitor (T-14 in {days_until_checkin - 14} days)"
        elif t14_eligible:
            next_action = "Send T-14 SMS Offer"
        elif t1_eligible:
            next_action = "Send T-1 SMS Reminder"
        elif days_until_checkin == 0:
            next_action = "Guest checking in today"
        elif days_until_checkin < 0:
            next_action = "Guest checked in"
        else:
            next_action = f"Monitor (T-1 in {days_until_checkin - 1} days)"
        
        workflow_guests.append({
            'booking': booking,
            'days_until_checkin': days_until_checkin,
            't14_eligible': t14_eligible,
            't1_eligible': t1_eligible,
            'in_window': in_window,
            'workflow_status': workflow_status,
            'offer_type': offer_type,
            'next_action': next_action
        })
    
    # Calculate T-1 countdown for ALL eligible guests
    all_t1_guests = []
    for guest in workflow_guests:
        booking = guest['booking']
        days_until_checkin = guest['days_until_checkin']
        
        # Calculate T-1 date (1 day before check-in)
        t1_date = booking.arrive_date - timedelta(days=1)
        
        # Calculate time until T-1
        now = django_timezone.now()
        t1_datetime = django_timezone.make_aware(datetime.combine(t1_date, datetime.min.time()))
        time_until_t1 = t1_datetime - now
        
        # Determine status
        if days_until_checkin == 1:
            status = 'ready'  # Ready to send T-1 SMS today
        elif days_until_checkin > 1:
            status = 'countdown'  # Still counting down to T-1
        else:
            status = 'past'  # T-1 has passed (guest checked in)
        
        # Calculate days and hours until T-1
        if time_until_t1.total_seconds() > 0:
            days_to_t1 = time_until_t1.days
            hours_to_t1 = time_until_t1.seconds // 3600
        else:
            days_to_t1 = 0
            hours_to_t1 = 0
        
        all_t1_guests.append({
            'guest': guest,
            'status': status,
            'days_to_t1': days_to_t1,
            'hours_to_t1': hours_to_t1,
            't1_date': t1_date
        })
    
    # Group T-1 guests by checkout date only, but order by rate within each group
    t1_grouped = defaultdict(list)
    for guest_data in all_t1_guests:
        checkout_date = guest_data['guest']['booking'].depart_date
        t1_grouped[checkout_date].append(guest_data)
    
    # Sort checkout dates and guests by rate within each group
    t1_grouped_sorted = []
    for checkout_date in sorted(t1_grouped.keys()):
        # Sort guests by rate within this checkout date group
        guests_sorted = sorted(t1_grouped[checkout_date], 
                             key=lambda x: x['guest']['booking'].rate or "Standard Rate")
        guest_count = len(guests_sorted)
        
        t1_grouped_sorted.append({
            'checkout_date': checkout_date,
            'guests': guests_sorted,
            'guest_count': guest_count
        })
    
    # Get summary statistics
    total_eligible = len(workflow_guests)
    pending_t1 = len(all_t1_guests)  # Count all guests for T-1 summary (since we show all guests in the section)
    in_monitoring = len([g for g in workflow_guests if g['in_window'] and not g['t14_eligible'] and not g['t1_eligible']])
    
    # Calculate T-14 countdown for ALL eligible guests
    
    all_t14_guests = []
    for guest in workflow_guests:
        booking = guest['booking']
        days_until_checkin = guest['days_until_checkin']
        
        # Calculate T-14 date (14 days before check-in)
        t14_date = booking.arrive_date - timedelta(days=14)
        
        # Calculate time until T-14
        now = django_timezone.now()
        t14_datetime = django_timezone.make_aware(datetime.combine(t14_date, datetime.min.time()))
        time_until_t14 = t14_datetime - now
        
        # Determine status
        if days_until_checkin == 14:
            status = 'ready'  # Ready to send T-14 SMS today
        elif days_until_checkin > 14:
            status = 'countdown'  # Still counting down to T-14
        else:
            status = 'past'  # T-14 has passed
        
        # Calculate days and hours until T-14
        if time_until_t14.total_seconds() > 0:
            days_to_t14 = time_until_t14.days
            hours_to_t14 = time_until_t14.seconds // 3600
        else:
            days_to_t14 = 0
            hours_to_t14 = 0
        
        all_t14_guests.append({
            'guest': guest,
            'status': status,
            'days_to_t14': days_to_t14,
            'hours_to_t14': hours_to_t14,
            't14_date': t14_date
        })
    
    # Group T-14 guests by checkout date only, but order by rate within each group
    t14_grouped = defaultdict(list)
    for guest_data in all_t14_guests:
        checkout_date = guest_data['guest']['booking'].depart_date
        t14_grouped[checkout_date].append(guest_data)
    
    # Sort checkout dates and guests by rate within each group
    t14_grouped_sorted = []
    for checkout_date in sorted(t14_grouped.keys()):
        # Sort guests by rate within this checkout date group
        guests_sorted = sorted(t14_grouped[checkout_date], 
                             key=lambda x: x['guest']['booking'].rate or "Standard Rate")
        guest_count = len(guests_sorted)
        
        t14_grouped_sorted.append({
            'checkout_date': checkout_date,
            'guests': guests_sorted,
            'guest_count': guest_count
        })
    
    # Count all guests for T-14 summary (since we show all guests in the section)
    pending_t14 = len(all_t14_guests)
    
    # Queensland timezone for display
    qld_tz = pytz.timezone('Australia/Brisbane')
    
    context = {
        'connected_folder': connected_folder,
        'workflow_guests': workflow_guests,
        'today': today,
        'summary': {
            'total_eligible': total_eligible,
            'pending_t14': pending_t14,
            'pending_t1': pending_t1,
            'in_monitoring': in_monitoring,
        },
        'all_t14_guests': all_t14_guests,
        'all_t1_guests': all_t1_guests,
        't14_grouped_sorted': t14_grouped_sorted,
        't1_grouped_sorted': t1_grouped_sorted,
        'qld_tz': qld_tz,
    }
    
    return render(request, 'dashboard/guest_extra_night_workflow.html', context)