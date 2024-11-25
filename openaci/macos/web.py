from urllib.parse import urlparse

def get_domain(url):
    """Extract domain from URL
    Args:
        url: URL string
    Returns:
        str: Domain name or empty string if invalid
    """
    try:
        if url:
            # handle http and https
            if not url.startswith('http'):
                url = f"https://{url}"
            parsed = urlparse(url)
            # Get domain (remove www. if present)
            domain = parsed.netloc.replace('www.', '')
            return domain
    except:
        return None
    
    return None