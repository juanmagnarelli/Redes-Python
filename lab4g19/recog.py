from constants import KEEP, DROP, DONTKNOW, mime_to_extension
import re
import zlib
import mimetypes

headerlimit = 2000
httpok = re.compile("^HTTP/\d\.?\d 200 OK\r\n")
mimetype = re.compile("\r\nContent-Type: (.*?)(?:;|\r\n)")
httpcompression = re.compile("\r\nContent-Encoding: (.*?)\r\n")
last_filename_index = 1


def recognizer(payload):
    """
    payload is of type array.array.
    """
    l = len(payload)
    payload = payload[:headerlimit].tostring()
    if httpok.match(payload):
        return KEEP
    elif l > headerlimit:
        return DROP
    else:
        return DONTKNOW


def index_http_header_end(s):
    i = s.find("\r\n\r\n")
    while s[i:i + 2] == "\r\n":
        i += 2
    return i


def filename_and_payload(payload, basename=None, extension=None):
    global last_filename_index
    payload = payload.tostring()
    t = mimetype.search(payload)
    if t is not None:
        t = mime_to_extension.get(t.group(1), None)
    if t is None:
        t = ".unknown"
    i = index_http_header_end(payload)
    content_encoding = httpcompression.search(payload)
    if content_encoding is not None:
        content_encoding = content_encoding.group(1)
    payload = payload[i:]
    if content_encoding == 'gzip':
        payload = zlib.decompress(payload, 16+zlib.MAX_WBITS)
    elif content_encoding == 'deflate':
        payload = zlib.decompress(payload)
    if extension is None:
        extension = t
    if basename is None:
        basename = str(last_filename_index)
        last_filename_index += 1
    filename = basename + extension
    return filename, payload
