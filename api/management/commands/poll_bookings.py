"""
Django management command for polling Google Drive folders for new booking files.
"""
import time
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from api.models import GoogleDriveFolder, GoogleDriveWatchConfig, IngestionRun
from api.booking_ingestion_service import BookingIngestionService
from api.google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Poll Google Drive folders for new booking files and automatically import them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=getattr(settings, 'BOOKING_POLL_INTERVAL', 300),  # 5 minutes default
            help='Polling interval in seconds (default: 300 = 5 minutes)'
        )
        parser.add_argument(
            '--max-iterations',
            type=int,
            default=None,
            help='Maximum number of polling iterations (default: unlimited)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually importing'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        max_iterations = options['max_iterations']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting booking file polling every {interval} seconds')
        )
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be imported'))
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                if max_iterations and iteration > max_iterations:
                    self.stdout.write(
                        self.style.SUCCESS(f'Reached max iterations ({max_iterations}), stopping')
                    )
                    break
                
                self.stdout.write(f'Polling iteration {iteration} at {timezone.now()}')
                
                try:
                    results = self.poll_folders(dry_run)
                    self.report_results(results)
                    
                except Exception as e:
                    logger.error(f'Error during polling iteration {iteration}: {e}')
                    self.stdout.write(
                        self.style.ERROR(f'Error during polling: {e}')
                    )
                
                if max_iterations and iteration >= max_iterations:
                    break
                    
                self.stdout.write(f'Sleeping for {interval} seconds...\n')
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\nPolling stopped by user'))
        except Exception as e:
            logger.error(f'Fatal error in polling loop: {e}')
            self.stdout.write(self.style.ERROR(f'Fatal error: {e}'))

    def poll_folders(self, dry_run=False):
        """Poll all active watched folders for new files."""
        results = {
            'folders_checked': 0,
            'new_files_found': 0,
            'files_imported': 0,
            'errors': []
        }
        
        # Get all active watched folders
        active_folders = GoogleDriveFolder.objects.filter(is_active=True)
        
        if not active_folders.exists():
            self.stdout.write(self.style.WARNING('No active watched folders found'))
            return results
        
        results['folders_checked'] = active_folders.count()
        
        drive_service = GoogleDriveService()
        ingestion_service = BookingIngestionService()
        
        for folder in active_folders:
            try:
                # Check if folder has active watch configs
                watch_configs = GoogleDriveWatchConfig.objects.filter(
                    folder=folder,
                    is_active=True
                )
                
                if not watch_configs.exists():
                    continue
                
                self.stdout.write(f'Checking folder: {folder.folder_name}')
                
                # Get list of files in folder
                files = drive_service.list_files_in_folder(folder.folder_id)
                
                # Filter for Excel/Sheets files that haven't been processed recently
                new_files = self.filter_new_files(files, folder)
                
                if new_files:
                    results['new_files_found'] += len(new_files)
                    self.stdout.write(
                        self.style.SUCCESS(f'Found {len(new_files)} new files in {folder.folder_name}')
                    )
                    
                    if not dry_run:
                        # Process each new file
                        for file_info in new_files:
                            try:
                                self.stdout.write(f'Processing file: {file_info["name"]}')
                                
                                # Run ingestion for this specific file
                                ingestion_result = ingestion_service.ingest_file_by_id(
                                    folder_id=folder.folder_id,
                                    file_id=file_info['id'],
                                    filename=file_info['name']
                                )
                                
                                if ingestion_result.get('status') == 'success':
                                    results['files_imported'] += 1
                                    self.stdout.write(
                                        self.style.SUCCESS(f'Successfully imported: {file_info["name"]}')
                                    )
                                else:
                                    error_msg = f'Failed to import {file_info["name"]}: {ingestion_result.get("error", "Unknown error")}'
                                    results['errors'].append(error_msg)
                                    self.stdout.write(self.style.ERROR(error_msg))
                                    
                            except Exception as e:
                                error_msg = f'Error processing file {file_info["name"]}: {e}'
                                results['errors'].append(error_msg)
                                logger.error(error_msg)
                                self.stdout.write(self.style.ERROR(error_msg))
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'DRY RUN: Would process {len(new_files)} files')
                        )
                        for file_info in new_files:
                            self.stdout.write(f'  - {file_info["name"]}')
                
            except Exception as e:
                error_msg = f'Error checking folder {folder.folder_name}: {e}'
                results['errors'].append(error_msg)
                logger.error(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))
        
        return results

    def filter_new_files(self, files, folder):
        """Filter files to find new ones that haven't been processed recently."""
        if not files:
            return []
        
        new_files = []
        cutoff_time = timezone.now() - timedelta(hours=1)  # Only check files from last hour
        
        for file_info in files:
            try:
                # Check if file is a spreadsheet
                mime_type = file_info.get('mimeType', '')
                if not (
                    'spreadsheet' in mime_type or 
                    'excel' in mime_type or
                    file_info.get('name', '').lower().endswith(('.xlsx', '.xls'))
                ):
                    continue
                
                # Check if we've processed this file recently
                recent_runs = IngestionRun.objects.filter(
                    file_id=file_info['id'],
                    started_at__gte=cutoff_time,
                    status__in=['completed', 'partial']
                )
                
                if not recent_runs.exists():
                    # Parse file modification time
                    modified_time_str = file_info.get('modifiedTime')
                    if modified_time_str:
                        try:
                            modified_time = datetime.fromisoformat(
                                modified_time_str.replace('Z', '+00:00')
                            )
                            # Only process files modified in the last 24 hours
                            if modified_time >= timezone.now() - timedelta(days=1):
                                new_files.append(file_info)
                        except ValueError:
                            # If we can't parse the date, include the file to be safe
                            new_files.append(file_info)
                    else:
                        # If no modification time, include the file
                        new_files.append(file_info)
                        
            except Exception as e:
                logger.error(f'Error filtering file {file_info.get("name", "unknown")}: {e}')
                continue
        
        return new_files

    def report_results(self, results):
        """Report the results of the polling iteration."""
        self.stdout.write(f'Polling results:')
        self.stdout.write(f'  - Folders checked: {results["folders_checked"]}')
        self.stdout.write(f'  - New files found: {results["new_files_found"]}')
        self.stdout.write(f'  - Files imported: {results["files_imported"]}')
        
        if results['errors']:
            self.stdout.write(f'  - Errors: {len(results["errors"])}')
            for error in results['errors']:
                self.stdout.write(f'    * {error}')
        else:
            self.stdout.write(f'  - No errors')