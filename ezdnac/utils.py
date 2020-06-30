import requests
import json


def restcall(method, dnac, endpoint, **kwargs):
    baseurl = '/api/v1/'
    """
    General function for restcalls to DNAC

    attributes
    :mehtod (str) = POST/GET/PUT/DELETE
    :dnac (ezdnac apic obj)
    :endpoint(str) = endpoint ex: template-programmer/template/
    :data = payload to be sent as data
    :json = payload to be sent as json
    """
    if 'data' in kwargs:
        data = kwargs['data']
    else:
        data = None

    if 'jsondata' in kwargs:
        jsondata = kwargs['jsondata']
    else:
        jsondata = {}

    if 'headers' in kwargs:
        headers = kwargs['headers']
    else:
        headers = {
        'x-auth-token': dnac.authToken,
        'Content-Type': 'application/json'
        }

    if 'baseurl' in kwargs:
        baseurl = kwargs['baseurl']

    if method not in ['GET', 'PUT', 'POST', 'DELETE']:
        return "Invalid rest method"

    url = f'https://{dnac.ip}:{dnac.port}{baseurl}{endpoint}'
    response = requests.request(method, url, headers=headers, data=data,
                                json=jsondata, verify=dnac.verifySSL,
                                timeout=dnac.timeout)

    jsondata = json.loads(response.text)
    return jsondata
