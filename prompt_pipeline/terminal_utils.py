"""Terminal utilities for color output and progress indicators."""

import sys
import time
import threading
from typing import Optional


class Color:
    """ANSI color codes for terminal output."""
    
    # Reset
    RESET = "\033[0m"
    
    # Text colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright text colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # Styles
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    REVERSE = "\033[7m"


class Spinner:
    """Simple spinner for showing progress."""
    
    # ASCII frames for Windows compatibility
    FRAMES = ["|", "/", "-", "\\"]
    
    def __init__(self, message: str, color: str = Color.CYAN):
        """Initialize spinner.
        
        Args:
            message: Message to display with spinner
            color: Color code for the message
        """
        self.message = message
        self.color = color
        self.is_spinning = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the spinner."""
        if self.is_spinning:
            return
        
        self.is_spinning = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()
    
    def stop(self, success: bool = True):
        """Stop the spinner.
        
        Args:
            success: Whether to show success or failure symbol
        """
        if not self.is_spinning:
            return
        
        self.is_spinning = False
        if self.thread:
            self.thread.join(timeout=0.1)
        
        # Clear the line and show final status
        symbol = "[OK]" if success else "[FAILED]"
        color = Color.GREEN if success else Color.RED
        try:
            print(f"\r{color}{symbol} {self.message}{Color.RESET}")
        except UnicodeEncodeError:
            # Fallback: print without colors
            print(f"\r{symbol} {self.message}")
    
    def _spin(self):
        """Animation loop."""
        i = 0
        while self.is_spinning:
            frame = self.FRAMES[i % len(self.FRAMES)]
            try:
                print(f"\r{self.color}{frame} {self.message}{Color.RESET}", end="", flush=True)
            except UnicodeEncodeError:
                # Fallback: print without colors
                print(f"\r{frame} {self.message}", end="", flush=True)
            time.sleep(0.1)
            i += 1
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        success = exc_type is None
        self.stop(success)


def print_colored(text: str, color: str = Color.RESET, bold: bool = False) -> None:
    """Print colored text to terminal.
    
    Args:
        text: Text to print
        color: ANSI color code
        bold: Whether to make text bold
    """
    style = Color.BOLD if bold else ""
    try:
        print(f"{style}{color}{text}{Color.RESET}")
    except UnicodeEncodeError:
        # If encoding fails, try to print with error replacement
        try:
            print(text.encode('utf-8', errors='replace').decode('utf-8'))
        except:
            # Last resort: print without special characters
            print(text.encode('ascii', errors='ignore').decode('ascii'))


def print_header(text: str, color: str = Color.CYAN) -> None:
    """Print a formatted header.
    
    Args:
        text: Header text
        color: Color for the header
    """
    try:
        print_colored(f"\n{'='*80}", color, True)
        print_colored(text, color, True)
        print_colored(f"{'='*80}", color, True)
    except:
        # Fallback: print without colors
        print(f"\n{'='*80}")
        print(text)
        print(f"{'='*80}")


def print_success(text: str) -> None:
    """Print success message in green.
    
    Args:
        text: Success message
    """
    try:
        print_colored(f"[OK] {text}", Color.GREEN)
    except:
        print(f"[OK] {text}")


def print_warning(text: str) -> None:
    """Print warning message in yellow.
    
    Args:
        text: Warning message
    """
    try:
        print_colored(f"[WARN] {text}", Color.YELLOW)
    except:
        print(f"[WARN] {text}")


def print_error(text: str) -> None:
    """Print error message in red.
    
    Args:
        text: Error message
    """
    try:
        print_colored(f"[ERROR] {text}", Color.RED)
    except:
        print(f"[ERROR] {text}")


def print_info(text: str) -> None:
    """Print info message in cyan.
    
    Args:
        text: Info message
    """
    try:
        print_colored(f"[INFO] {text}", Color.CYAN)
    except:
        print(f"[INFO] {text}")


def supports_color() -> bool:
    """Check if terminal supports color output.
    
    Returns:
        True if terminal supports colors
    """
    # Check if running in a terminal that supports colors
    try:
        return sys.stdout.isatty()
    except:
        return False


# Color utility functions for different message types
def format_prompt(text: str) -> str:
    """Format prompt text for display.
    
    Args:
        text: Prompt text to format
        
    Returns:
        Formatted text with color
    """
    try:
        if supports_color():
            return f"{Color.CYAN}{Color.BOLD}{text}{Color.RESET}"
        return text
    except UnicodeEncodeError:
        # If encoding fails, return plain text
        return text


def format_response(text: str) -> str:
    """Format response text for display.
    
    Args:
        text: Response text to format
        
    Returns:
        Formatted text with color
    """
    try:
        if supports_color():
            return f"{Color.GREEN}{text}{Color.RESET}"
        return text
    except UnicodeEncodeError:
        # If encoding fails, return plain text
        return text


def format_model(text: str) -> str:
    """Format model name for display.
    
    Args:
        text: Model name to format
        
    Returns:
        Formatted text with color
    """
    if supports_color():
        return f"{Color.MAGENTA}{text}{Color.RESET}"
    return text


def format_step(text: str) -> str:
    """Format step name for display.
    
    Args:
        text: Step name to format
        
    Returns:
        Formatted text with color
    """
    if supports_color():
        return f"{Color.YELLOW}{text}{Color.RESET}"
    return text
