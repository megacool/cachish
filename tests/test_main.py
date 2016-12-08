import hashlib
import os
from unittest import mock

from requests.exceptions import HTTPError
import responses

@responses.activate
def test_working_call(client):
    responses.add(responses.GET, 'https://api.heroku.com/apps/myapp/config-vars',
        json={"MYKEY": "MYVALUE"})

    heroku_mock = mock.Mock(return_value='postgres://mydbhost')

    with mock.patch('cachish.backends.Heroku', heroku_mock):
        response = client.get('/heroku/database-url', headers={
            'authorization': 'Bearer footoken',
        })

    assert response.status_code == 200

    # Should have written to cache
    cache_filename = hashlib.sha256(b'/heroku/database-url').hexdigest()
    cache_file = os.path.join(client.application.config.cache_dir, cache_filename)
    with open(cache_file) as fh:
        assert fh.read() == 'MYVALUE'



def test_invalid_token(client):
    response = client.get('/heroku/database-url', headers={
        'authorization': 'Bearer foobar',
    })
    assert response.status_code == 403


def test_no_token(client):
    response = client.get('/heroku/database-url')
    assert response.status_code == 401


@responses.activate
def test_backend_failure_no_cached(client):
    error = HTTPError('oops')
    responses.add(responses.GET, 'https://api.heroku.com/apps/myapp/config-vars',
        body=error)

    response = client.get('/heroku/database-url', headers={
        'authorization': 'bearer footoken',
    })
    assert response.status_code == 503


@responses.activate
def test_backend_failure_cached(client):
    error = HTTPError('oops')
    responses.add(responses.GET, 'https://api.heroku.com/apps/myapp/config-vars',
        body=error)

    application_cache_dir = client.application.config.cache_dir
    cache_filename = hashlib.sha256(b'/heroku/database-url').hexdigest()
    cache_file = os.path.join(application_cache_dir, cache_filename)
    with open(cache_file, 'w') as fh:
        fh.write('MYCACHEDVALUE')

    response = client.get('/heroku/database-url', headers={
        'authorization': 'bearer footoken',
    })
    assert response.status_code == 203
    assert response.data.decode('utf-8') == 'MYCACHEDVALUE'
