import pytest
from app.integrations.nasa.nssdca import validate_nasa_url, _TextExtractor


def test_nssdca_adapter_allows_only_registered_nasa_https_hosts():
    validate_nasa_url('https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-059C')
    validate_nasa_url('https://science.nasa.gov/mission/surveyor-3/')
    with pytest.raises(ValueError):
        validate_nasa_url('http://nssdc.gsfc.nasa.gov/nmc/')
    with pytest.raises(ValueError):
        validate_nasa_url('https://example.com/mission')


def test_nasa_html_extractor_preserves_page_title_description_and_text():
    parser = _TextExtractor()
    parser.feed('<html><head><title>Mission Page</title><meta name="description" content="Mission summary"></head><body><h1>Mission</h1><p>Surface science</p><script>secret()</script></body></html>')
    assert ' '.join(parser.title) == 'Mission Page'
    assert parser.description == 'Mission summary'
    assert 'Surface science' in ' '.join(parser.parts)
    assert 'secret' not in ' '.join(parser.parts)
