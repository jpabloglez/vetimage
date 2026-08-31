"""
Authenticated serving of uploaded patient files.

Everything under MEDIA_ROOT is clinical data — DICOM pixel data, clinical
photographs, lab result PDFs — but it was served with no authorization at all:
Django's `static()` helper under DEBUG, and whatever the reverse proxy happened
to do in production. Filenames are predictable enough that "unguessable path"
was never a control.

Why signed URLs rather than a permission check on the request:
the browser loads these through `<img src>` and `<a href>`, which cannot carry
the `Authorization` header (the access token lives in memory, not a cookie), so
a plain IsAuthenticated view would simply break every image. A signed,
expiring URL is the same approach S3 presigning uses: the capability travels in
the URL, is unforgeable without SECRET_KEY, and expires on its own.

The serializer that already decided a user may see a record mints the URL; this
module only verifies the signature and streams the bytes.
"""

import mimetypes
import os
import posixpath

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.views import View

# Signed media links are meant to live just long enough for the page that
# embedded them to finish loading, not to be shared around.
MEDIA_URL_TTL_SECONDS = int(os.getenv('MEDIA_URL_TTL_SECONDS', 900))  # 15 min

_signer = TimestampSigner(salt='vetimage.protected-media')


def sign_media_path(relative_path: str) -> str:
    """Return the signature for *relative_path* (a MEDIA_ROOT-relative path)."""
    return _signer.sign(relative_path).split(':', 1)[1]


def signed_media_url(file_field, request=None) -> str | None:
    """
    Build a signed URL for a FileField/ImageField, or None when it's empty.

    Pass *request* to get an absolute URL (what API clients need).
    """
    if not file_field:
        return None

    relative_path = file_field.name
    url = f"{settings.MEDIA_URL}{relative_path}?sig={sign_media_path(relative_path)}"
    return request.build_absolute_uri(url) if request is not None else url


def _is_safe_path(relative_path: str) -> bool:
    """
    Reject anything that escapes MEDIA_ROOT.

    The signature already covers the path, so a traversal string can't be
    injected without SECRET_KEY — this is the belt to that braces.
    """
    normalised = posixpath.normpath(relative_path)
    if normalised.startswith(('/', '..')) or '\\' in relative_path:
        return False
    full = os.path.realpath(os.path.join(settings.MEDIA_ROOT, normalised))
    return full.startswith(os.path.realpath(settings.MEDIA_ROOT) + os.sep)


class ProtectedMediaView(View):
    """
    Serve a file from MEDIA_ROOT, but only with a valid, unexpired signature.

    Set `MEDIA_ACCEL_REDIRECT_PREFIX` (e.g. `/internal-media/`) to hand the
    actual byte-pushing to nginx via X-Accel-Redirect, matched by an
    `internal;` location block pointed at MEDIA_ROOT. Without it the file is
    streamed by Django, which is fine for development but wasteful in
    production.
    """

    def get(self, request, path):
        signature = request.GET.get('sig', '')
        if not signature:
            return HttpResponseForbidden('Missing signature.')

        try:
            # TimestampSigner works on "value:timestamp:signature"; we transport
            # the value in the URL path and the rest in ?sig=.
            unsigned = _signer.unsign(f'{path}:{signature}', max_age=MEDIA_URL_TTL_SECONDS)
        except SignatureExpired:
            return HttpResponseForbidden('This link has expired.')
        except BadSignature:
            return HttpResponseForbidden('Invalid signature.')

        if unsigned != path or not _is_safe_path(path):
            return HttpResponseForbidden('Invalid signature.')

        full_path = os.path.join(settings.MEDIA_ROOT, path)
        if not os.path.isfile(full_path):
            raise Http404('File not found.')

        content_type, _ = mimetypes.guess_type(full_path)
        content_type = content_type or 'application/octet-stream'

        accel_prefix = getattr(settings, 'MEDIA_ACCEL_REDIRECT_PREFIX', '')
        if accel_prefix:
            response = HttpResponse(content_type=content_type)
            response['X-Accel-Redirect'] = f'{accel_prefix}{path}'
            return response

        return FileResponse(open(full_path, 'rb'), content_type=content_type)
