import os
from django.conf import settings

CLOUDINARY_RAW_EXTENSIONS = (
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.txt', '.csv', '.zip', '.rar', '.tar', '.gz', '.7z'
)

def build_cloudinary_url(path):
    """
    Given a local or relative media path (e.g., 'media/nutritionist/certificates/xyz.pdf'
    or 'nutritionist/certificates/xyz.pdf'), returns the full secure Cloudinary delivery URL.
    If the path is already an absolute HTTP/HTTPS URL or empty, it is returned as-is.
    """
    if not path:
        return ""
    path_str = str(path).strip()
    if path_str.startswith("http://") or path_str.startswith("https://") or path_str.startswith("data:"):
        return path_str

    clean_path = path_str.lstrip('/')
    while clean_path.startswith('media/'):
        clean_path = clean_path[len('media/'):].lstrip('/')

    cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', 'dkcfeta0f')
    ext = os.path.splitext(clean_path.lower())[1]
    resource_type = 'raw' if ext in CLOUDINARY_RAW_EXTENSIONS else 'image'

    return f"https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/media/{clean_path}"
