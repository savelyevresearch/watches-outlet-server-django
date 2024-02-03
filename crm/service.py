import os
import requests

from dotenv import load_dotenv
from functools import reduce
from urllib.parse import urlencode
from hashlib import md5
from utils import CrmError

load_dotenv()

class CrmService():
    @classmethod
    def __get_request_password(cls, params):
        try:
            crm_token = cls._getToken();

            getting_request_password_params = {
                app_id: os.getenv('BUSINESS_RU_APP_ID'),
                **params,
            }
            getting_request_password_params_ordered = {}

            for param in sorted(getting_request_password_params.keys()):
                getting_request_password_params_ordered.update({ param: getting_request_password_params[param] })
        
            getting_request_password_params_ordered_string = urlencode(getting_request_password_params_ordered)
            request_password = md5(getting_request_password_params_ordered_string.encode('utf-8')).hexdigest()

            return request_password
        except error:
            raise CrmError('Something went wrong while getting a request password')

    @classmethod
    def __get_token(cls):
        try:
            formatted_stringified_params = f'{os.getenv('BUSINESS_RU_SECRET')}app_id={os.getenv('BUSINESS_RU_APP_ID')}'
            hashed_stringified_params = md5(formatted_stringified_params.encode()).hexdigest()

            params = {
                'app_id': os.getenv('BUSINESS_RU_APP_ID'),
                'app_psw': hashed_stringified_params,
            }

            getting_token_response = requests.get(f'{os.getenv('BUSINESS_RU_URL')}/api/rest/repair.json', params)

            if getting_token_response.status_code == 200:
                return getting_token_response.json()["token"]
            else:
                raise CrmError('Something went wrong while getting a token')
        except Exception:
            raise CrmError('Something went wrong while getting a token')

    @classmethod
    def make_api_request(cls, method, model, params, body):
        try:
            request_password = cls.__get_request_password()
            model_requesting_url = f'{os.getenv('BUSINESS_RU_URL')}/api/rest/{model}.json'
            native_params = {
                "app_id": os.getenv('BUSINESS_RU_APP_ID'),
                "app_psw": request_password,
            }
            target_params = { **native_params, **params }
            crm_api_response = requests.request(method=method, url=model_requesting_url, params=params, json=body)

            if crm_api_response.status_code == 200:
                return crm_api_response.json()
            else:
                raise CrmError('Something went wrong while making a request to the CRM API')
        except Exception:
            raise CrmError('Something went wrong while making a request to the CRM API')