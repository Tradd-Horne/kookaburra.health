"""
Google Sheets API service for reading booking data.
"""
import re
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple, Any
from dateutil.parser import parse as parse_date

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .google_drive_service import SCOPES


class GoogleSheetsService:
    """Service for reading Google Sheets data."""
    
    def __init__(self, service_account_file='service-account.json'):
        self.service_account_file = service_account_file
        self.sheets_service = None
        
        # Column mapping for booking data - based on your Excel header
        self.COLUMN_MAPPING = {
            0: 'booking_number',     # No.
            1: 'status',             # Status
            2: 'file_as',            # File As
            3: 'first_name',         # Name
            4: 'surname',            # Surname
            5: 'company',            # Company
            6: 'region',             # Region
            7: 'portal',             # Portal
            8: 'arrive_date',        # Arrive
            9: 'depart_date',        # Depart
            10: 'room_number',       # Room
            11: 'room_type',         # Room Type
            12: 'deposit_required',  # Deposit Req
            13: 'received_amount',   # Received
            14: 'deposit_due',       # Deposit Due
            15: 'deposit_by_date',   # Deposit By
            16: 'total_amount',      # Total
            17: 'balance',           # Balance
            18: 'agent',             # Agent
            19: 'agent_ref',         # Agent Ref
            20: 'email',             # Email
            21: 'mobile',            # Mobile
            22: 'car_rego',          # Car Rego
            23: 'guest_request',     # Guest Request
            24: 'enquiry_status',    # Enquiry Status
            25: 'primary_source',    # Primary Source
            26: 'black_list',        # Black List
            27: 'rate',              # Rate
            28: 'suburb',            # Suburb
            29: 'post_code',         # Post Code
            30: 'state',             # State
            31: 'room_status',       # Room Status
            32: 'dual_key',          # Dual Key
            33: 'pre_auth_amount',   # Pre-Auth Amount To
            34: 'total_pre_auths',   # Total Pre-Auths
        }
        
        # Fields that should never change once set (immutable facts)
        self.IMMUTABLE_FIELDS = {
            'booking_number', 'arrive_date', 'depart_date', 
            'original_total', 'deposit_required'
        }
        
    def authenticate(self):
        """Authenticate and create Google Sheets service."""
        if not self.sheets_service:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file, 
                scopes=SCOPES
            )
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
        return self.sheets_service
    
    def extract_file_date(self, filename: str) -> Optional[datetime]:
        """
        Extract date from filename, fallback to file creation time.
        Looks for patterns like: bookings_2025-09-28, data_27-09-2025, etc.
        """
        # Common date patterns in filenames
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # 2025-09-28
            r'(\d{2}-\d{2}-\d{4})',  # 28-09-2025
            r'(\d{2}/\d{2}/\d{4})',  # 28/09/2025
            r'(\d{4}/\d{2}/\d{2})',  # 2025/09/28
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    return parse_date(match.group(1), dayfirst=True)
                except:
                    continue
        
        return None
    
    def normalize_value(self, value: Any, field_name: str) -> Any:
        """
        Normalize and clean cell values based on field type.
        """
        # Define CharField fields that should return empty string instead of None
        char_fields = {
            'status', 'file_as', 'first_name', 'surname', 'company', 
            'region', 'portal', 'room_number', 'room_type', 'agent', 
            'agent_ref', 'email', 'mobile', 'car_rego', 'guest_request',
            'enquiry_status', 'primary_source', 'rate', 'suburb', 
            'post_code', 'state', 'room_status', 'dual_key'
        }
        
        if value is None or value == '':
            return '' if field_name in char_fields else None
            
        # Convert to string first and handle non-breaking spaces
        str_value = str(value).strip()
        
        # Handle non-breaking space and other whitespace characters
        if not str_value or str_value == '\u00a0' or str_value == ' ':
            return '' if field_name in char_fields else None
            
        # Date fields
        if field_name in ['arrive_date', 'depart_date', 'deposit_by_date', 'booking_date']:
            return self.parse_date(str_value)
            
        # Decimal/Money fields
        if field_name in ['deposit_required', 'received_amount', 'deposit_due', 
                         'total_amount', 'balance', 'original_total', 
                         'pre_auth_amount', 'total_pre_auths']:
            return self.parse_decimal(str_value)
            
        # Boolean fields
        if field_name == 'black_list':
            return self.parse_boolean(str_value)
            
        # Email normalization
        if field_name == 'email':
            return str_value.lower() if '@' in str_value else str_value
            
        # Phone number cleaning
        if field_name == 'mobile':
            return re.sub(r'[^\d\+\-\(\)\s]', '', str_value)
            
        # Standard string cleaning
        return str_value
    
    def parse_date(self, value: Any) -> Optional[date]:
        """Parse date string or Excel serial number to date object."""
        if not value or value == '#ERROR!':
            return None
            
        try:
            # Handle Excel serial date numbers (e.g., 45726 = Sep 19, 2025)
            if isinstance(value, (int, float)) and value > 10000:
                # Excel epoch starts on Jan 1, 1900, but has a leap year bug
                # So we use Jan 1, 1900 as day 1 and adjust
                excel_epoch = date(1900, 1, 1)
                # Excel incorrectly treats 1900 as a leap year, so subtract 2 days
                delta_days = int(value) - 2
                return excel_epoch + timedelta(days=delta_days)
            
            # Convert to string for text parsing
            value_str = str(value).strip()
            
            # Handle DD/MM/YYYY format (Australian)
            if '/' in value_str:
                parts = value_str.split('/')
                if len(parts) == 3:
                    # Assume DD/MM/YYYY
                    day, month, year = parts
                    return date(int(year), int(month), int(day))
            
            # Use dateutil parser for other formats
            parsed = parse_date(value_str, dayfirst=True)
            return parsed.date() if parsed else None
            
        except (ValueError, TypeError):
            return None
    
    def parse_decimal(self, value: str) -> Optional[Decimal]:
        """Parse money/decimal string to Decimal object."""
        if not value or value == '#ERROR!':
            return None
            
        try:
            # Remove currency symbols and formatting
            cleaned = re.sub(r'[\$,\s]', '', str(value))
            # Handle negative values in parentheses like (-$810.40)
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            # Remove any remaining non-numeric characters except decimal point and minus
            cleaned = re.sub(r'[^\d\.\-]', '', cleaned)
            
            if cleaned:
                return Decimal(cleaned)
                
        except (ValueError, InvalidOperation):
            pass
            
        return None
    
    def parse_boolean(self, value: str) -> bool:
        """Parse boolean value from string."""
        if not value:
            return False
        return str(value).upper() in ['TRUE', 'YES', '1', 'Y', 'T']
    
    def read_sheet_data(self, spreadsheet_id: str, sheet_name: str = None) -> List[List[Any]]:
        """
        Read raw data from Google Sheets.
        """
        if not self.sheets_service:
            self.authenticate()
        
        try:
            # If no sheet name specified, read from first sheet
            if not sheet_name:
                # Get sheet metadata to find first sheet
                sheet_metadata = self.sheets_service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id
                ).execute()
                
                sheets = sheet_metadata.get('sheets', [])
                if not sheets:
                    raise ValueError("No sheets found in spreadsheet")
                
                sheet_name = sheets[0]['properties']['title']
            
            # Read all data from the sheet
            range_name = f"'{sheet_name}'!A:AZ"  # Read columns A to AZ
            
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueRenderOption='UNFORMATTED_VALUE'
            ).execute()
            
            values = result.get('values', [])
            return values
            
        except HttpError as error:
            print(f"An error occurred reading sheet: {error}")
            raise
    
    def detect_header_row(self, rows: List[List[Any]]) -> Tuple[int, bool]:
        """
        Detect if first row is a header and return header row index.
        Returns (header_row_index, has_header)
        """
        if not rows:
            return 0, False
            
        first_row = rows[0] if rows else []
        
        # Check if first row looks like headers
        header_indicators = ['No.', 'Status', 'Name', 'Surname', 'Arrive', 'Depart']
        matches = sum(1 for cell in first_row if any(indicator in str(cell) for indicator in header_indicators))
        
        has_header = matches >= 3  # If at least 3 header indicators match
        
        return (0 if has_header else -1), has_header
    
    def normalize_row_data(self, row: List[Any], row_index: int) -> Dict[str, Any]:
        """
        Convert raw row data to normalized booking data using column mapping.
        """
        normalized = {}
        
        for col_index, field_name in self.COLUMN_MAPPING.items():
            if col_index < len(row):
                raw_value = row[col_index]
                normalized_value = self.normalize_value(raw_value, field_name)
                normalized[field_name] = normalized_value
            else:
                normalized[field_name] = None
        
        # Set original_total from total_amount if not already set
        if not normalized.get('original_total') and normalized.get('total_amount'):
            normalized['original_total'] = normalized['total_amount']
        
        # Add metadata
        normalized['_row_index'] = row_index
        normalized['_raw_data'] = row
        
        return normalized
    
    def validate_booking_row(self, normalized_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a normalized booking row.
        Returns (is_valid, error_message)
        """
        # Must have booking number
        if not normalized_data.get('booking_number'):
            return False, "Missing booking number"
        
        # Booking number should be numeric-ish
        booking_num = str(normalized_data['booking_number']).strip()
        if not booking_num or not re.match(r'^\d+$', booking_num):
            return False, f"Invalid booking number format: {booking_num}"
        
        # Should have guest name
        if not normalized_data.get('first_name') and not normalized_data.get('surname'):
            return False, "Missing guest name"
        
        # Should have arrival date
        if not normalized_data.get('arrive_date'):
            return False, "Missing arrival date"
        
        return True, ""
    
    def extract_bookings_from_sheet(self, spreadsheet_id: str, sheet_name: str = None) -> Dict[str, Any]:
        """
        Extract and normalize booking data from a Google Sheet.
        
        Returns:
            Dictionary with:
            - 'bookings': List of normalized booking data
            - 'metadata': Processing metadata
            - 'errors': List of validation errors
        """
        try:
            # Read raw sheet data
            raw_rows = self.read_sheet_data(spreadsheet_id, sheet_name)
            
            if not raw_rows:
                return {
                    'bookings': [],
                    'metadata': {'total_rows': 0, 'header_detected': False},
                    'errors': ['Sheet is empty']
                }
            
            # Detect header row
            header_row_index, has_header = self.detect_header_row(raw_rows)
            
            # Start processing from after header (if exists)
            data_start_index = 1 if has_header else 0
            
            bookings = []
            errors = []
            
            for row_index, row in enumerate(raw_rows[data_start_index:], start=data_start_index):
                if not any(cell for cell in row):  # Skip empty rows
                    continue
                
                try:
                    # Normalize row data
                    normalized = self.normalize_row_data(row, row_index)
                    
                    # Validate row
                    is_valid, error_msg = self.validate_booking_row(normalized)
                    
                    if is_valid:
                        bookings.append(normalized)
                    else:
                        errors.append({
                            'row': row_index + 1,
                            'error': error_msg,
                            'data': row
                        })
                        
                except Exception as e:
                    errors.append({
                        'row': row_index + 1,
                        'error': f"Processing error: {str(e)}",
                        'data': row
                    })
            
            metadata = {
                'total_rows': len(raw_rows),
                'header_detected': has_header,
                'data_rows_processed': len(raw_rows) - data_start_index,
                'valid_bookings': len(bookings),
                'invalid_rows': len(errors),
                'sheet_name': sheet_name
            }
            
            return {
                'bookings': bookings,
                'metadata': metadata,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'bookings': [],
                'metadata': {'error': str(e)},
                'errors': [f"Failed to process sheet: {str(e)}"]
            }