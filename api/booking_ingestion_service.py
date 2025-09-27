"""
Booking ingestion service - handles merge/dedupe logic for hotel booking data.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from decimal import Decimal

from django.db import transaction
from django.utils import timezone as django_timezone

from .models import (
    Booking, IngestionRun, ProcessedFile, RawRow, 
    QuarantinedRow, BookingConflict, GoogleDriveFolder
)
from .google_sheets_service import GoogleSheetsService
from .google_drive_service import GoogleDriveService


class BookingIngestionService:
    """
    Service to handle the complete booking ingestion pipeline.
    Implements your step-by-step process: discover → extract → merge → dedupe → store.
    """
    
    def __init__(self):
        self.sheets_service = GoogleSheetsService()
        self.drive_service = GoogleDriveService()
        
        # Define immutable fields that should never change
        self.IMMUTABLE_FIELDS = {
            'booking_number', 'arrive_date', 'depart_date', 
            'original_total', 'deposit_required'
        }
    
    def calculate_row_hash(self, row_data: Dict[str, Any]) -> str:
        """Calculate hash of normalized row data for change detection."""
        # Remove metadata fields and sort for consistent hashing
        clean_data = {k: v for k, v in row_data.items() if not k.startswith('_')}
        sorted_data = json.dumps(clean_data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def extract_data_time_from_file(self, filename: str, file_created_time: datetime) -> datetime:
        """
        Extract data timestamp from filename, fallback to file creation time.
        """
        extracted_date = self.sheets_service.extract_file_date(filename)
        if extracted_date:
            # Combine extracted date with file creation time
            return datetime.combine(
                extracted_date.date(), 
                file_created_time.time()
            ).replace(tzinfo=timezone.utc)
        
        return file_created_time
    
    def discover_new_files(self, folder: GoogleDriveFolder) -> List[Dict[str, Any]]:
        """
        Discover new Google Sheets files in the watched folder.
        Returns list of file metadata for unprocessed files.
        """
        try:
            if not self.drive_service.service:
                self.drive_service.authenticate()
            
            # Get all Google Sheets files in the folder
            query = f"'{folder.folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
            
            results = self.drive_service.service.files().list(
                q=query,
                fields="files(id, name, createdTime, modifiedTime, owners)",
                orderBy="createdTime asc"  # Process oldest first for chronological ordering
            ).execute()
            
            files = results.get('files', [])
            
            # Filter out already processed files
            processed_file_ids = set(
                ProcessedFile.objects.filter(folder=folder).values_list('file_id', flat=True)
            )
            
            new_files = []
            for file_info in files:
                if file_info['id'] not in processed_file_ids:
                    # Parse timestamps
                    created_time = datetime.fromisoformat(file_info['createdTime'].replace('Z', '+00:00'))
                    modified_time = datetime.fromisoformat(file_info['modifiedTime'].replace('Z', '+00:00'))
                    
                    # Extract data time from filename
                    data_time = self.extract_data_time_from_file(file_info['name'], created_time)
                    
                    new_files.append({
                        'file_id': file_info['id'],
                        'filename': file_info['name'],
                        'created_time': created_time,
                        'modified_time': modified_time,
                        'data_time': data_time,
                        'owners': file_info.get('owners', [])
                    })
            
            # Sort by data_time for chronological processing
            new_files.sort(key=lambda x: x['data_time'])
            
            return new_files
            
        except Exception as e:
            print(f"Error discovering files: {e}")
            return []
    
    def process_booking_row(self, booking_data: Dict[str, Any], ingestion_run: IngestionRun) -> Tuple[str, str]:
        """
        Process a single booking row with merge/dedupe logic.
        
        Returns (action_taken, details) where action is:
        - 'inserted': New booking created
        - 'updated': Existing booking updated with newer data
        - 'ignored': Older data ignored
        - 'conflict': Immutable field conflict detected
        """
        booking_number = str(booking_data['booking_number']).strip()
        
        try:
            existing_booking = Booking.objects.get(booking_number=booking_number)
            
            # Check if incoming data is newer
            if booking_data.get('source_file_time', ingestion_run.data_time) <= existing_booking.source_file_time:
                return 'ignored', f"Older data ignored (file time: {ingestion_run.data_time})"
            
            # Check for immutable field conflicts
            conflicts = []
            for field in self.IMMUTABLE_FIELDS:
                if field in booking_data and booking_data[field] is not None:
                    existing_value = getattr(existing_booking, field)
                    incoming_value = booking_data[field]
                    
                    # Compare values (handle different types)
                    if existing_value is not None and str(existing_value) != str(incoming_value):
                        # Log conflict
                        BookingConflict.objects.create(
                            booking_number=booking_number,
                            field_name=field,
                            existing_value=str(existing_value),
                            incoming_value=str(incoming_value),
                            source_file_id=ingestion_run.file_id,
                            ingestion_run=ingestion_run
                        )
                        conflicts.append(f"{field}: {existing_value} -> {incoming_value}")
            
            # Update mutable attributes only
            mutable_fields = set(booking_data.keys()) - self.IMMUTABLE_FIELDS - {'_row_index', '_raw_data'}
            
            updated_fields = []
            for field in mutable_fields:
                if field in booking_data and hasattr(existing_booking, field):
                    old_value = getattr(existing_booking, field)
                    new_value = booking_data[field]
                    
                    if old_value != new_value:
                        setattr(existing_booking, field, new_value)
                        updated_fields.append(field)
            
            # Update metadata
            existing_booking.source_file_id = ingestion_run.file_id
            existing_booking.source_file_time = ingestion_run.data_time
            existing_booking.source_row_hash = self.calculate_row_hash(booking_data)
            existing_booking.ingestion_run = ingestion_run
            
            existing_booking.save()
            
            action = 'conflict' if conflicts else 'updated'
            details = f"Updated {len(updated_fields)} fields"
            if conflicts:
                details += f", {len(conflicts)} conflicts: {', '.join(conflicts)}"
                
            return action, details
            
        except Booking.DoesNotExist:
            # Create new booking
            # Remove metadata fields
            clean_data = {k: v for k, v in booking_data.items() if not k.startswith('_')}
            
            booking = Booking.objects.create(
                **clean_data,
                source_file_id=ingestion_run.file_id,
                source_file_time=ingestion_run.data_time,
                source_row_hash=self.calculate_row_hash(booking_data),
                ingestion_run=ingestion_run
            )
            
            return 'inserted', f"New booking created: {booking.booking_number}"
    
    @transaction.atomic
    def ingest_file(self, folder: GoogleDriveFolder, file_info: Dict[str, Any]) -> IngestionRun:
        """
        Ingest a single Google Sheets file with full audit and merge logic.
        """
        # Create ingestion run record
        ingestion_run = IngestionRun.objects.create(
            folder=folder,
            file_id=file_info['file_id'],
            filename=file_info['filename'],
            file_created_time=file_info['created_time'],
            file_modified_time=file_info['modified_time'],
            data_time=file_info['data_time'],
            status='running'
        )
        
        try:
            # Extract booking data from sheet
            extraction_result = self.sheets_service.extract_bookings_from_sheet(
                file_info['file_id']
            )
            
            bookings = extraction_result['bookings']
            metadata = extraction_result['metadata']
            extraction_errors = extraction_result['errors']
            
            # Update ingestion run with metadata
            ingestion_run.sheet_names = [metadata.get('sheet_name', 'Sheet1')]
            ingestion_run.rows_processed = len(bookings) + len(extraction_errors)
            ingestion_run.save()
            
            # Process each booking
            for booking_data in bookings:
                try:
                    # Store raw row for audit
                    row_hash = self.calculate_row_hash(booking_data)
                    RawRow.objects.create(
                        file_id=file_info['file_id'],
                        row_index=booking_data.get('_row_index', 0),
                        row_hash=row_hash,
                        raw_data=booking_data.get('_raw_data', []),
                        ingestion_run=ingestion_run
                    )
                    
                    # Process booking with merge logic
                    action, details = self.process_booking_row(booking_data, ingestion_run)
                    
                    # Update counters
                    if action == 'inserted':
                        ingestion_run.rows_inserted += 1
                    elif action == 'updated':
                        ingestion_run.rows_updated += 1
                    elif action == 'ignored':
                        ingestion_run.rows_ignored += 1
                    elif action == 'conflict':
                        ingestion_run.conflicts_detected += 1
                        ingestion_run.rows_updated += 1
                        
                except Exception as e:
                    # Quarantine row that failed processing
                    QuarantinedRow.objects.create(
                        file_id=file_info['file_id'],
                        row_index=booking_data.get('_row_index', 0),
                        raw_data=booking_data.get('_raw_data', []),
                        error_message=str(e),
                        ingestion_run=ingestion_run
                    )
                    ingestion_run.rows_quarantined += 1
            
            # Quarantine extraction errors
            for error in extraction_errors:
                QuarantinedRow.objects.create(
                    file_id=file_info['file_id'],
                    row_index=error.get('row', 0),
                    raw_data=error.get('data', []),
                    error_message=error.get('error', 'Unknown error'),
                    ingestion_run=ingestion_run
                )
                ingestion_run.rows_quarantined += 1
            
            # Mark file as processed
            ProcessedFile.objects.create(
                file_id=file_info['file_id'],
                folder=folder,
                filename=file_info['filename'],
                ingestion_run=ingestion_run
            )
            
            # Complete ingestion run
            ingestion_run.status = 'completed' if ingestion_run.rows_quarantined == 0 else 'partial'
            ingestion_run.completed_at = django_timezone.now()
            ingestion_run.save()
            
            return ingestion_run
            
        except Exception as e:
            # Mark ingestion as failed
            ingestion_run.status = 'failed'
            ingestion_run.error_message = str(e)
            ingestion_run.completed_at = django_timezone.now()
            ingestion_run.save()
            
            raise e
    
    def process_folder(self, folder: GoogleDriveFolder) -> Dict[str, Any]:
        """
        Process all new files in a watched folder.
        Implements the complete discovery → ingestion pipeline.
        """
        results = {
            'folder_id': folder.folder_id,
            'folder_name': folder.folder_name,
            'files_discovered': 0,
            'files_processed': 0,
            'files_failed': 0,
            'total_bookings_inserted': 0,
            'total_bookings_updated': 0,
            'total_bookings_ignored': 0,
            'total_conflicts': 0,
            'total_quarantined': 0,
            'ingestion_runs': [],
            'errors': []
        }
        
        try:
            # Discover new files
            new_files = self.discover_new_files(folder)
            results['files_discovered'] = len(new_files)
            
            if not new_files:
                results['message'] = "No new files found"
                return results
            
            # Process each file in chronological order
            for file_info in new_files:
                try:
                    print(f"Processing file: {file_info['filename']}")
                    ingestion_run = self.ingest_file(folder, file_info)
                    
                    results['files_processed'] += 1
                    results['total_bookings_inserted'] += ingestion_run.rows_inserted
                    results['total_bookings_updated'] += ingestion_run.rows_updated
                    results['total_bookings_ignored'] += ingestion_run.rows_ignored
                    results['total_conflicts'] += ingestion_run.conflicts_detected
                    results['total_quarantined'] += ingestion_run.rows_quarantined
                    
                    results['ingestion_runs'].append({
                        'id': ingestion_run.id,
                        'filename': ingestion_run.filename,
                        'status': ingestion_run.status,
                        'rows_processed': ingestion_run.rows_processed,
                        'rows_inserted': ingestion_run.rows_inserted,
                        'rows_updated': ingestion_run.rows_updated,
                        'rows_ignored': ingestion_run.rows_ignored,
                        'conflicts_detected': ingestion_run.conflicts_detected,
                        'rows_quarantined': ingestion_run.rows_quarantined
                    })
                    
                except Exception as e:
                    results['files_failed'] += 1
                    results['errors'].append({
                        'filename': file_info['filename'],
                        'error': str(e)
                    })
                    
            return results
            
        except Exception as e:
            results['errors'].append({
                'error': f"Folder processing failed: {str(e)}"
            })
            return results