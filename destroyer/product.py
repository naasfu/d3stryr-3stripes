import json

from settings import hyped_skus, user_config
from utils import *
import inventory


def canonicalize_product_info_client(product_json):
    # Initialize a dictionary.
    product_info = {}
    product_info['productStock'] = {}

    # Because of how we order the skus in clientStockURL 0-index is
    # always masterPid info in the JSON response.
    try:
        data = product_json['data'][0]
    except:
        print(d_(), x_('Parse Client JSON'))
    try:
        product_info['productName'] = data['name']
    except:
        product_info['productName'] = '/'
    try:
        product_info['productColor'] = data['c_defaultColor']
    except:
        product_info['productColor'] = '/'
    try:
        product_info['productOrderable'] = data['inventory']['orderable']
    except:
        product_info['productOrderable'] = False
    try:
        product_info['productPrice'] = data['price']
    except:
        product_info['productPrice'] = 0
    try:
        product_info['productCount'] = product_json['count'] - 1
    except:
        product_info['productCount'] = 0
    try:
        product_info['productATS'] = data['inventory']['ats']
    except:
        product_info['productATS'] = 0
    try:
        product_info['productStockLevel'] = data['inventory']['stock_level']
    except:
        product_info['productStockLevel'] = 0

    # Because data['c_sizeFTW'] and data['c_sizeSearchValue'] yield nonsense
    # for some EU locales:
    # Build a dictionary to convert adidas _XXX sizing to canonical sizing.
    adidasSize2Size = {}
    for variant in data['variation_attributes'][0]['values']:
        adidasSize2Size['{0}_{1}'.format(user_config.masterPid, variant['value'])] = variant['name']

    # We could avoid:
    # if data['id'] != masterPid:
    # by using a for loop to iterate through:
    # range(1,len(product_json['data'])):
    # But I doubt there is a performance hit here. Because this is only done
    # once even if threading is introduce in the future.
    for data in product_json['data']:
        if data['id'] != user_config.masterPid:
            try:
                product_info['productStock'][adidasSize2Size[data['id']]] = {}
                product_info['productStock'][adidasSize2Size[data['id']]]['ATS'] = int(data['inventory']['ats'])
                product_info['productStock'][adidasSize2Size[data['id']]]['pid'] = data['id']
            except:
                print(d_(), x_('Client Inventory'))

    if user_config.debug:
        print(d_(), z_('Debug'), o_(json.dumps(product_info, indent=2)))
    return product_info


def canonicalize_product_info_variant(product_json):
    """
    Creating a standard format of the data representation using a dictionary
    """
    product_info = {}
    product_info['productStock'] = {}
    product_info['productName'] = '/'
    product_info['productColor'] = '/'
    product_info['productOrderable'] = '/'
    try:
        product_info['productPrice'] = product_json[
            'variations']['variants'][0]['pricing']['standard']
    except:
        product_info['productPrice'] = 0
    try:
        product_info['productCount'] = len(product_json['variations']['variants'])
    except:
        product_info['productCount'] = 0

    product_info['productATS'] = 0

    try:
        for variant in product_json['variations']['variants']:
            product_info['productATS'] = product_info['productATS'] + int(variant['ATS'])
            product_info['productStock'][variant['attributes']['size']] = {}
            product_info['productStock'][variant['attributes']['size']]['ATS'] = int(variant['ATS'])
            product_info['productStock'][variant['attributes']['size']]['pid'] = variant['id']
    except:
        print(d_(), x_('Variant Inventory'))

    product_info['productStockLevel'] = product_info['productATS']

    if user_config.debug:
        print(d_(), z_('Debug'), o_(json.dumps(product_info, indent=2)))
    return product_info


def getProductInfo():
    if user_config.useClientInventory:
        try:
            print(d_(), s_('Client Endpoint'))
            response = inventory.get_client_response()
            product_json = response.json()
            productInfoClient = canonicalize_product_info_client(product_json)
            return productInfoClient
        except:
            print(d_(), x_('Client Endpoint'))
            if user_config.debug:
                print(d_(), z_('Debug'),
                      o_('Client Endpoint Response -', response.text))
    # If we reached this point then useClientInventory didn't successfully
    # return. So lets proceed with useVariantInventory.
    try:
        print(d_(), s_('Variant Endpoint'))
        response = inventory.get_variant_response()
        product_json = response.json()
        productInfoVariant = canonicalize_product_info_variant(product_json)
        return productInfoVariant
    except:
        print(d_(), x_('Variant Endpoint'))
        if user_config.debug:
            print(d_(), z_('Debug'),
                  o_('Variant Endpoint Response -', response.text))
    # If we reached this point then useVariantInventory did not successfully
    # return. So lets produce at minimum size inventory.
    # We will refer to this as Fallback for productInfo (when both client and
    # variant produces no inventory result).
    productInfoFallback = {}
    productInfoFallback['productStock'] = {}
    productInfoFallback['productName'] = '/'
    productInfoFallback['productColor'] = '/'
    productInfoFallback['productOrderable'] = '/'
    productInfoFallback['productPrice'] = 0
    productInfoFallback['productCount'] = -1
    productInfoFallback['productATS'] = -1
    productInfoFallback['productStockLevel'] = -1
    # US vs EU sizing seems to be off by 0.5 size
    if user_config.parametersLocale == 'US':
        literalSize = 4.5
        for variant in range(540, 750, 10):
            stringLiteralSize = str(literalSize).replace('.0', '')
            productInfoFallback['productStock'][stringLiteralSize] = {}
            productInfoFallback['productStock'][stringLiteralSize]['ATS'] = 1
            productInfoFallback['productStock'][stringLiteralSize][
                'pid'] = '{0}_{1}'.format(user_config.masterPid, variant)
            literalSize = literalSize + .5
    else:
        literalSize = 4.5
        for variant in range(550, 750, 10):
            stringLiteralSize = str(literalSize).replace('.0', '')
            productInfoFallback['productStock'][stringLiteralSize] = {}
            productInfoFallback['productStock'][stringLiteralSize]['ATS'] = 1
            productInfoFallback['productStock'][stringLiteralSize][
                'pid'] = '{0}_{1}'.format(user_config.masterPid, variant)
            literalSize = literalSize + .5
    return productInfoFallback


def printProductInfo(productInfo):
    print(d_(), s_('Product Name'), lb_(productInfo['productName']))
    print(d_(), s_('Product Color'), lb_(productInfo['productColor']))
    print(d_(), s_('Price'), lb_(productInfo['productPrice']))
    print(d_(), s_('Orderable'), lb_(productInfo['productOrderable']))
    print(d_(), s_('ATS'), lb_(str(productInfo['productATS']).rjust(6, ' ')))
    print(d_(), s_('Stock Level'), lb_(str(productInfo['productStockLevel']).rjust(6, ' ')))
    print(d_(), s_('Size Inventory'))

    for size in sorted(productInfo['productStock']):
        print(d_(), s_(size.ljust(5, ' '), '/', productInfo['productStock'][size]['pid']),
              lb_(str(productInfo['productStock'][size]['ATS']).rjust(6, ' ')))
