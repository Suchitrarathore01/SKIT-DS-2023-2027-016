from urllib.parse import urlparse


def process_url(url: str):
    parsed_url = urlparse(url)

    return {
        "protocol": parsed_url.scheme,
        "domain": parsed_url.netloc,
        "path": parsed_url.path
    }