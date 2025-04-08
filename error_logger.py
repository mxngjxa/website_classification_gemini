# error_logger.py
import os
from collections import defaultdict
import datetime

class ErrorLogger:
    """
    A class for collecting, categorizing, and summarizing errors during processing.
    """
    def __init__(self, base_filename):
        """Initialize error logger with categorized error tracking."""
        self.base_filename = base_filename
        self.error_log_file = os.path.splitext(base_filename)[0] + "_error_messages.log"
        self.errors_by_type = defaultdict(list)
        self.total_errors = 0
        
    def log_error(self, error_type, url, error_message):
        """
        Log an error with its type, affected URL, and message.
        
        Args:
            error_type (str): Category of error (e.g., 'connection', 'api', 'parsing')
            url (str): The URL where the error occurred
            error_message (str): Description of the error
        """
        self.errors_by_type[error_type].append((url, str(error_message)))
        self.total_errors += 1
        
    def get_summary(self):
        """Generate a formatted summary of all logged errors."""
        summary = f"Error Summary Report - {datetime.datetime.now()}\n"
        summary += "=" * 80 + "\n\n"
        summary += f"Total errors: {self.total_errors}\n\n"
        
        for error_type, errors in self.errors_by_type.items():
            summary += f"{error_type.upper()} ERRORS ({len(errors)}):\n"
            summary += "-" * 40 + "\n"
            
            # Group similar errors to avoid repetition
            error_counts = defaultdict(list)
            for url, error_msg in errors:
                error_counts[error_msg].append(url)
            
            # Add each unique error with affected URLs
            for error_msg, urls in error_counts.items():
                summary += f"Error: {error_msg}\n"
                summary += f"Occurred in {len(urls)} URLs:\n"
                # Show all URLs if 5 or fewer, otherwise show first 3 and count
                if len(urls) <= 5:
                    for url in urls:
                        summary += f"  - {url}\n"
                else:
                    for url in urls[:3]:
                        summary += f"  - {url}\n"
                    summary += f"  - ... and {len(urls) - 3} more URLs\n"
                summary += "\n"
            
            summary += "\n"
            
        return summary
    
    def write_log(self):
        """Write the error summary to the log file."""
        if self.total_errors == 0:
            with open(self.error_log_file, 'w') as f:
                f.write("No errors were recorded during processing.\n")
            return
            
        with open(self.error_log_file, 'w') as f:
            f.write(self.get_summary())
            
        print(f"Error summary written to {self.error_log_file}")
