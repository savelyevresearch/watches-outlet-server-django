import os
import requests
import logging

from dotenv import load_dotenv
from functools import reduce
from urllib.parse import urlencode
from hashlib import md5
from utils import CrmError

load_dotenv()

logger = logging.getLogger(__name__)

class CrmService():
    @classmethod
    def _get_request_password(cls, params):
        try:
            crm_token = cls._get_token();

            getting_request_password_params = {
                'app_id': os.getenv('BUSINESS_RU_APP_ID'),
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
    def _get_token(cls):
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
    def make_api_request(cls, method, model, params = {}, body = {}):
        try:
            request_password = cls._get_request_password(params)
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

    @classmethod
    def get_all_product_groups(cls):
        try:
            product_groups = cls.make_api_request('get', 'groupsofgoods')

            return product_groups
        except Exception as error:
            raise CrmError('Something went wrong while getting all product groups from CRM: ', error)

    @classmethod
    def get_all_store_goods_documents(cls):
        try:
            all_store_goods_documents = []
            intermediate_store_goods_documents = []
            page = 1

            while len(intermediate_store_goods_documents) > 0 or page == 1:
                store_goods_documents = cls.make_api_request('get', 'storegoods', {
                    'limit': 250,
                    'page': page,
                })

                intermediate_store_goods_documents = store_goods_documents['result']

                all_store_goods_documents = [
                    *all_store_goods_documents,
                    *intermediate_store_goods_documents,
                ]

                page = page + 1

            return all_store_goods_documents
        except Exception as error:
            raise CrmError('Something went wrong while getting all store goods documents from CRM')

    @classmethod
    def get_all_available_goods(cls):
        try:
            brand_groups = map(int, os.getenv('BRAND_GROUPS').split(','))
            necessary_store_ids = map(int, os.getenv('BUSINESS_RU_NECESSARY_STORE_IDS').split(','))

            all_goods_from_stores = []
            intermediate_goods_from_stores = []
            page = 1

            logger.info('Getting the goods data from CRM is started...')

            while len(intermediate_goods_from_stores) or page == 1:
                goods_from_stores = cls.make_api_request('get', 'goods', {
                    'with_additional_fields': 1,
                    'with_remains': 1,
                    'filter_positive_free_remains': 1,
                    'limit': 250,
                    'page': page,
                    'with_attributes': 1,
                    'with_prices': 1,
                    'deleted': False,
                })
                intermediate_goods_from_stores = goods_from_stores.result
                all_goods_from_stores = [*all_goods_from_stores, *intermediate_goods_from_stores]
                
                page = page + 1

            goods_filtered_by_brand_groups = []

            for product in all_goods_from_stores:
                for brand_group in brand_groups:
                    if int(product['group_id']) == brand_group:
                        goods_filtered_by_brand_groups.append(product)

            all_store_goods_documents = cls.get_all_store_goods_documents()
            target_goods = []

            for store_product_document in all_store_goods_documents:
                for product_filtered_by_brand_groups in goods_filtered_by_brand_groups:
                    if int(store_product_document['good_id']) == int(product_filtered_by_brand_groups['id']):
                        for necessary_store_id in necessary_store_ids:
                            free_remaining_quantity = int(store_product_document.amount) - int(store_product_document.reserved)

                            if int(store_product_document.store_id) == necessary_store_id and free_remaining_quantity > 0:
                                target_goods.append({
                                    **product_filtered_by_brand_groups,
                                    'quantity': free_remaining_quantity,
                                })

            logger.info('Getting the goods data from CRM is finished...')

            return target_goods
        except Exception as error:
            raise CrmError('Something went wrong while getting all available goods')

    @classmethod
    def get_partner_id(cls, partner_name):
        try:
            partner = cls.make_api_request('get', 'partners', {
                'name': partner_name,
            })

            return partner['result'][0]['id'] if partner['result'][0] else None
        except Exception:
            raise CrmError('Something went wrong while getting a partner ID from CRM')

    @classmethod
    def create_partner(cls, name, phone_number, email):
        try:
            partner = cls.make_api_request('post', 'partners', { 'name': name })
            partner_id = int(partner['result']['id'])
            contact_info_types = cls.make_api_request('get', 'contactinfotypes')

            for contact_info_type in contact_info_types['result']:
                contact_info_type_id = int(contact_info_type['id'])
                value = ''

                if (contact_info_type['name'] == 'Email'):
                    value = email
                elif contact_info_type['name'] == 'Телефон':
                    value = phone_number
                
                if value:
                    cls.make_api_request('post', 'partnercontactinfo', {
                        'contact_info': value,
                        'contact_info_type_id': contact_info_type_id,
                        'partner_id': partner_id,
                    })
        except Exception:
            raise CrmError('omething went wrong while creating a partner')

    @classmethod
    def update_partner(cls, partner_id, phone_number, email):
        try:
            contact_info_types = cls.make_api_request('get', 'contactinfotypes')

            for contact_info_type in contact_info_types['result']:
                contact_info_type_id = int(contact_info_type['id'])
                value = ''

                if (contact_info_type['name'] == 'Email'):
                    value = email
                elif contact_info_type['name'] == 'Телефон':
                    value = phone_number

                if value:
                    cls.make_api_request('put', 'partnercontactinfo', {
                        'contact_info': value,
                        'contact_info_type_id': contact_info_type_id,
                        'partner_id': partner_id,
                    })
        except Exception:
            raise CrmError('Something went wrong while updating a partner')