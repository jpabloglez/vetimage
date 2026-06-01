"""
Utility functions for credentials app
"""

import threading
import re

# Thread-local storage for request context
_thread_locals = threading.local()


def set_current_request(request):
    """Store current request in thread-local storage"""
    _thread_locals.request = request


def get_current_request():
    """Retrieve current request from thread-local storage"""
    return getattr(_thread_locals, 'request', None)


def clear_current_request():
    """Clear current request from thread-local storage"""
    if hasattr(_thread_locals, 'request'):
        delattr(_thread_locals, 'request')


def extract_ip_address(request):
    """
    Extract real IP address from request, handling proxies.

    Args:
        request: Django request object

    Returns:
        str: IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip


def detect_device_type(user_agent):
    """
    Detect device type from user agent string.

    Args:
        user_agent: User agent string

    Returns:
        dict: Device information
    """
    user_agent_lower = user_agent.lower()

    # Basic device detection
    if 'mobile' in user_agent_lower or 'android' in user_agent_lower:
        device_type = 'mobile'
    elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
        device_type = 'tablet'
    elif 'bot' in user_agent_lower or 'crawler' in user_agent_lower:
        device_type = 'api'
    else:
        device_type = 'desktop'

    # Browser detection
    browser = 'Unknown'
    browser_version = ''

    if 'chrome' in user_agent_lower:
        browser = 'Chrome'
        match = re.search(r'chrome/(\d+)', user_agent_lower)
        if match:
            browser_version = match.group(1)
    elif 'firefox' in user_agent_lower:
        browser = 'Firefox'
        match = re.search(r'firefox/(\d+)', user_agent_lower)
        if match:
            browser_version = match.group(1)
    elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
        browser = 'Safari'
        match = re.search(r'version/(\d+)', user_agent_lower)
        if match:
            browser_version = match.group(1)

    # OS detection
    os_name = 'Unknown'
    os_version = ''

    if 'windows' in user_agent_lower:
        os_name = 'Windows'
        if 'windows nt 10' in user_agent_lower:
            os_version = '10/11'
    elif 'mac os' in user_agent_lower or 'macos' in user_agent_lower:
        os_name = 'macOS'
    elif 'linux' in user_agent_lower:
        os_name = 'Linux'
    elif 'android' in user_agent_lower:
        os_name = 'Android'
    elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower:
        os_name = 'iOS'

    return {
        'device_type': device_type,
        'browser': browser,
        'browser_version': browser_version,
        'os': os_name,
        'os_version': os_version,
    }


def calculate_risk_score(reason):
    """
    Calculate risk score based on suspicious activity reason.

    Args:
        reason: Reason for suspicious activity

    Returns:
        int: Risk score (0-100)
    """
    risk_scores = {
        'ip_change': 50,
        'device_change': 60,
        'brute_force': 90,
        'scope_violation': 75,
        'rate_limit_exceeded': 40,
        'invalid_token': 70,
        'concurrent_session_limit': 30,
        'suspicious_location': 65,
        'multiple_failed_logins': 80,
        'token_replay': 85,
    }

    return risk_scores.get(reason, 50)


def get_ip_geolocation(ip_address):
    """
    Get geolocation (country, city) for an IP address.

    This is a placeholder implementation. For production, you can use:
    - GeoIP2 database (MaxMind)
    - IP geolocation API (ipapi.co, ipstack, etc.)

    Args:
        ip_address: IP address string

    Returns:
        Tuple of (country_code, city_name) or (None, None)
    """
    # Skip localhost/private IPs
    if ip_address in ['127.0.0.1', 'localhost'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        return None, None

    # Placeholder - return None for now
    # In production, implement GeoIP2 lookup:
    # try:
    #     import geoip2.database
    #     from django.conf import settings
    #     reader = geoip2.database.Reader(settings.GEOIP_DATABASE_PATH)
    #     response = reader.city(ip_address)
    #     return response.country.iso_code, response.city.name
    # except Exception:
    #     return None, None

    return None, None


def is_suspicious_ip_change(old_ip, new_ip):
    """
    Determine if an IP address change is suspicious.

    Args:
        old_ip: Previous IP address
        new_ip: New IP address

    Returns:
        True if change is suspicious, False otherwise
    """
    # Same IP - not suspicious
    if old_ip == new_ip:
        return False

    # If both IPs are private/local, not suspicious
    private_prefixes = ['127.', '192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.',
                        '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.',
                        '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.']

    old_is_private = any(old_ip.startswith(prefix) for prefix in private_prefixes)
    new_is_private = any(new_ip.startswith(prefix) for prefix in private_prefixes)

    if old_is_private and new_is_private:
        return False

    # Check if IPs are in same subnet (simple /24 check)
    old_subnet = '.'.join(old_ip.split('.')[:3])
    new_subnet = '.'.join(new_ip.split('.')[:3])

    if old_subnet == new_subnet:
        return False  # Same subnet, probably same location

    # Different public IPs - potentially suspicious
    return True
