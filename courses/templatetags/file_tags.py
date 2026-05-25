from django import template
from urllib.parse import quote

register = template.Library()

@register.filter
def cloudinary_download(url):
    """Force Cloudinary to serve file as download attachment."""
    if not url:
        return url
    # Insert fl_attachment flag after /upload/
    return url.replace('/upload/', '/upload/fl_attachment/')

@register.filter
def google_viewer(url):
    """Wrap URL in Google Docs Viewer for in-browser preview."""
    if not url:
        return url
    return 'https://docs.google.com/viewer?url=' + quote(str(url), safe='') + '&embedded=true'

@register.filter
def office_viewer(url):
    """Wrap URL in Microsoft Office Online viewer."""
    if not url:
        return url
    return 'https://view.officeapps.live.com/op/embed.aspx?src=' + quote(str(url), safe='')
