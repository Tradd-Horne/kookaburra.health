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
from datetime import datetime
import pytz

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
    
    # Get all bookings for this folder
    bookings_queryset = Booking.objects.filter(
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
    
    # Get unique booking statuses for filter dropdown
    booking_statuses = Booking.objects.filter(
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
    
    # Get filtered bookings (same filtering logic as main view)
    bookings_queryset = Booking.objects.filter(
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