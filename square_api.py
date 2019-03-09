#!/opt/sjs/bin/python

"""
Runs nightly at 4am CST, after tabs have been closed via cron:

    $ cat /etc/cron.d/sjs_nightly_financials_report
    0 4 * * * ec2-user /opt/sjs/financial-automations/square_api.py

Also imported by twilio_bot.py.
"""

import dateutil.relativedelta
import urlparse
import datetime
import httplib
import pymysql
import smtplib
import urllib
import pickle
import locale
import json
import time
import sys

import squareconnect
from squareconnect.rest import ApiException
from squareconnect.apis.locations_api import LocationsApi
from squareconnect.apis.catalog_api import CatalogApi
from squareconnect.models.catalog_object import CatalogObject
from squareconnect.models.catalog_object_batch import CatalogObjectBatch
from squareconnect.models.catalog_item import CatalogItem
from squareconnect.models.catalog_item_variation import CatalogItemVariation
from squareconnect.models.money import Money
from squareconnect.models.batch_upsert_catalog_objects_request import BatchUpsertCatalogObjectsRequest
from squareconnect.models.batch_retrieve_catalog_objects_request import BatchRetrieveCatalogObjectsRequest
from squareconnect.models.search_catalog_objects_request import SearchCatalogObjectsRequest


# batteries not included.
import google_api

# enable testing
testing = True

# Uses the locale to format currency amounts correctly.
# NOTE: this took a touch of trial and error.
locale.setlocale(locale.LC_ALL, "en_CA.UTF-8")

# pull secrets.
secrets      = json.loads(open("/opt/sjs/secrets.json").read())
location_ids = secrets["square"]["location_ids"]
homepath     = secrets["general"]["home_path"]

'''
try:
    # ListLocations
    api_response = api_instance.list_locations()
    print (api_response.locations)
except ApiException as e:
    print ('Exception when calling LocationApi->list_locations: %s\n' % e)
'''

# calculate report date automatically
report_date = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

# allow for CLI override.
if len(sys.argv) > 1:
    report_date = sys.argv[1]

# resolve report and log paths.
filename = "%s.txt" % report_date
fh       = open(homepath + filename,   "w")
log      = open(homepath + "log.txt", "rb").read()

# personal access token retrieved from https://connect.squareup.com/apps
access_token = secrets["square"]["access_token"]

# Standard HTTP headers for every Connect API request
request_headers = \
{
    "Authorization" : "Bearer " + access_token,
    "Accept"        : "application/json",
    "Content-Type"  : "application/json",
}

# database credentials.
sql_db   = secrets["sql"]["database"]
sql_user = secrets["sql"]["user"]
sql_pw   = secrets["sql"]["password"]

########################################################################################################################
def update_item_price (amount):
    """
    This code runs to update the prices of each item by the given amount (100 increases by $1 -100 lowers by $1
    """
    """
    ITEM OBJECT
    {
        u'category': 
            {
                u'id': u'3KH3JCBYYOFWEIFG7VUVHAG4', 
                u'name': u'Vodka'
             }, 
        u'name': u'Deep Eddy Lemon', 
        u'variations': [
            {
                u'ordinal': 1, 
                u'name': u'', 
                u'pricing_type': u'FIXED_PRICING', 
                u'item_id': u'BTSIJNC7ZKLZ53OPJYOMVRDN', 
                u'price_money': 
                    {
                        u'amount': 800, 
                        u'currency_code': u'USD'
                    }, 
                u'track_inventory': True, 
                u'id': u'LTNZXXUDBVJM4XSPESS2BLL6', 
                u'inventory_alert_type': u'NONE'
            }
            ], 
        u'available_for_pickup': False, 
        u'available_online': False, 
        u'visibility': u'PRIVATE', 
        u'fees': [
            {
                u'inclusion_type': u'INCLUSIVE', 
                u'name': u'Sales Tax', 
                u'applies_to_custom_amounts': True, 
                u'adjustment_type': u'TAX', 
                u'enabled': True, 
                u'rate': u'0.0825', 
                u'calculation_phase': u'FEE_SUBTOTAL_PHASE', 
                u'type': u'US_SALES_TAX', 
                u'id': u'3YQ6JIF447RW6L2E2J7S6RR7'
            }, 
            {
                u'inclusion_type': u'INCLUSIVE', 
                u'name': u'Alcohol Sales Tax', 
                u'applies_to_custom_amounts': True, 
                u'adjustment_type': u'TAX', 
                u'enabled': True, 
                u'rate': u'0.067', 
                u'calculation_phase': u'FEE_SUBTOTAL_PHASE', 
                u'type': u'US_SALES_TAX', 
                u'id': u'Q7QKJC4RLTBAL3IHKDROESOM'
            }], 
        u'category_id': u'3KH3JCBYYOFWEIFG7VUVHAG4', 
        u'type': u'NORMAL', 
        u'id': u'BTSIJNC7ZKLZ53OPJYOMVRDN', 
        u'master_image': 
            {
                u'url': u'https://images-production-f.squarecdn.com/kIiDFWrUgN5kARrjZRe9zXps2X8=/https://square-production.s3.amazonaws.com/files/bd9e5c3ce5512cf5df1c9a561d037fea18967c3c/original.jpeg', 
                u'id': u'778289B7-724B-406E-BD97-0269C287A1F1'
            }
    }
    """
    api_instance = CatalogApi()
    api_instance.api_client.configuration.access_token = secrets["square"]["access_token"]

    #save_item_prices("Pre-Price-Update_%s" % datetime.datetime.today().strftime("%Y-%m-%d"))
    items = get_items()

    idempotency_key = int(pickle.load(open("/opt/sjs/financial-automations/idempotency_key.p", "rb")))
    idempotency_key += 1
    pickle.dump(idempotency_key, open("/opt/sjs/financial-automations/idempotency_key.p", "wb"))
    count = 0
    for i in items:
        
        item_data = i.item_data
        if item_data.category_id == 'HWXUT7NC7CMYTQML76MIXU7F':
            print "Skipping",item_data.name
            continue
        if i.id == 'QSBZSC5VJA2C2ASQ5TQVJXO5':
            print "Skipping",item_data.name 
            items.remove(i)
            continue
        if item_data.product_type.lower() != "regular":
            print "Skipping",item_data.name
            continue

        #print item.to_dict()
        #var = CatalogItemVariation(item.item_variation_data())
        var = item_data.variations
        for v in var:
            variation_data = v.item_variation_data
            price_money = variation_data.price_money
            try:
                price_money.amount = int(price_money.amount)+amount
                count += 1
            except:
                pass
        count += 1

    body = BatchUpsertCatalogObjectsRequest(
        idempotency_key=str(idempotency_key),
        batches=[CatalogObjectBatch(items)]
    )

    response = api_instance.batch_upsert_catalog_objects(body)
    print "Successfully updated prices"
    return response
    

########################################################################################################################
def update_variation (variation_updates):
    """
    @LOGAN? what's this for?
    """

    global log
    
    '''
    connection   = httplib.HTTPSConnection("connect.squareup.com")
    request_body = variation_updates
    #url          = "/v1/" + location_ids[0] + "/items/" + item_id + "/variations/" + variation_id
    url          = "/v2/catalog/batch-upsert"
    print request_body
    
    #req = requests.Request("POST","http://connect.squareup.com/v2/catalog/batch-upsert", data=json.dumps(request_body), headers=request_headers)
    #prepared = req.prepare()
    #pretty_print_POST(prepared)

    #req = requests.post("http://connect.squareup.com/v2/catalog/batch-upsert", data=json.dumps(request_body), headers=request_headers)
    #response = req.text
    #print response
    connection.request("POST", url, str(request_body), request_headers)

    response      = connection.getresponse()
    response_body = json.loads(response.read())
    resp = ""
    if response.status == 200:
        connection.close()
        return response_body

    else:
        resp += "Item update failed\n"
        resp += json.dumps(response_body, sort_keys=True, indent=2, separators=(",", ": "))
        connection.close()
        return resp
    '''
########################################################################################################################
def save_item_prices (name):
    """
    This saves a backup of the prices in case something goes wrong and we need to restore the prices
    """

    items      = get_items()
    save_items = {}

    for i in items:
        price        = 0
        variation_id = ""

        item_data = i.item_data
        itemname = i.item_data.name

        #print item.to_dict()
        #var = CatalogItemVariation(item.item_variation_data())
        var = item_data.variations
        for v in var:
            variation_data = v.item_variation_data
            price_money = variation_data.price_money
            price = price_money.amount

            variation_id = v.id

        save_items[i["id"]] = \
        {
            "price"        : price,
            "variation_id" : variation_id,
            "item_id"      : i.id,
            "item_name"    : itemname,
        }

    pickle.dump(save_items, open("/opt/sjs/financial-automations/%s.p" % name, "wb"))

########################################################################################################################
def restore_item_price (name):
    """
    @LOGAN? what's this for?
    """

    data = pickle.load(open("/opt/sjs/financial-automations%s.p" % name, "rb"))

    for d in data:
        price = data[d]["price"]

        if price > 0:
            variation = "{'price_money':{'amount':%s,'currency_code': 'USD'}}" % price
            update_variation(data[d]["item_id"], data[d]["variation_id"], variation)
        else:
            continue


########################################################################################################################
def get_row (table, date):
    try:
        return database("SELECT * from %s where date like '%s'" % (table,date))[0]
    except:
        return False

########################################################################################################################
def database (sql):
    """
    establish a database connection, run SQL query, and close the handle.
    # TODO: keep an open handle.
    """

    db = pymysql.connect( \
        host='localhost', \
        user=sql_user,    \
        password=sql_pw,  \
        db=sql_db,        \
        charset='utf8mb4',\
        autocommit=True,  \
        cursorclass=pymysql.cursors.DictCursor)

    cur  = db.cursor(pymysql.cursors.DictCursor)
    sql += ";"

    cur.execute(sql)
    result = cur.fetchall()

    db.close()
    return result


########################################################################################################################
def populate_database (date):
    """
    @LOGAN? what's this for?
    """

    # @LOGAN? why this default date?
    if not date:
        date = "2017-01-01"

    try:
        date = datetime.datetime.strptime(date, "%Y-%m-%d")
    except:
        pass

    while date < datetime.datetime.today():
        daily_sales(date)
        date = date + datetime.timedelta(days=1)


########################################################################################################################
def format_money (amount):
  if not amount: return locale.currency(0)
  return locale.currency(amount / 100.0)


########################################################################################################################
def get_location_ids ():
    """
    Obtains all of the business's location IDs. Each location has its own collection of payments.
    """

    global log

    # the base url for every connect API request.
    connection   = httplib.HTTPSConnection("connect.squareup.com")
    request_path = "/v1/me/locations"
    connection.request("GET", request_path, "", request_headers)

    # transform the JSON array of locations into a python list.
    response  = connection.getresponse()
    locations = json.loads(response.read())

    location_ids = []
    for location in locations:
        location_ids.append(location["id"])

    connection.close()

    return location_ids


########################################################################################################################
def get_items ():
    """
    @LOGAN? what's this for?
    """

    global log
    #https://github.com/square/connect-python-sdk/blob/master/squareconnect/models

    api_instance = CatalogApi()
    api_instance.api_client.configuration.access_token = secrets["square"]["access_token"]

    body = SearchCatalogObjectsRequest(
        object_types=[
            "ITEM"
        ])
    response = api_instance.search_catalog_objects(body)
    items = response.objects
    
    return items


########################################################################################################################
def update_item (item_id, item_updates):
    """
    @LOGAN? what's this for?
    """

    global log
    connection   = httplib.HTTPSConnection("connect.squareup.com")
    request_body = str(item_updates)
    url          = "/v1/" + location_ids[0] + "/items/" + item_id, request_body

    connection.request("PUT", url, request_headers)

    response      = connection.getresponse()
    response_body = json.loads(response.read())

    if response.status == 200:
        connection.close()
        return response_body

    else:
        print "Item update failed"
        connection.close()
        return None


########################################################################################################################
def get_cash_drawer (date=False):
    """
    @LOGAN? what's this for?
    """

    global log

    if not date:
        reportdate = datetime.datetime.today()-datetime.timedelta(days=1)
        end        = datetime.datetime.today()
        end        = end.strftime("%Y-%m-%dT04:00:00-06:00")

    else:
        try:
            reportdate = datetime.datetime.strptime(date,"%Y-%m-%d")
        except:
            reportdate = date
        end        = (reportdate+datetime.timedelta(days=1)).strftime("%Y-%m-%dT04:00:00-06:00")

    # calculate beginning.
    begin      = reportdate.strftime("%Y-%m-%dT08:00:00-06:00")
    parameters = urllib.urlencode({"begin_time": begin, "end_time" : end})
    drawers    = []

    # the base url for every connect api request.
    connection = httplib.HTTPSConnection("connect.squareup.com")

    # for each location...
    for location_id in location_ids:
        request_path = "/v1/" + location_id + "/cash-drawer-shifts?" + parameters
        more_results = True

        # ...as long as there are more drawers to download from the location...
        while more_results:

            # ...send a GET request to /v1/LOCATION_ID/payments
            connection.request("GET", request_path, "", request_headers)

            response = connection.getresponse()
            resp     = eval(response.read())

            if "unauthorized" in resp:
                return ""

            # read the response body JSON into the cumulative list of results.
            for r in resp:
                drawers.append(r)

            # check whether pagination information is included in a response header, indicating more results.
            pagination_header = response.getheader("link", "")
            if "rel='next'" not in pagination_header:
                more_results = False

            else:
                # extract the next batch URL from the header.
                # pagination headers have the following format:
                # <https://connect.squareup.com/v1/LOCATION_ID/cash-drawer-shifts?batch_token=BATCH_TOKEN>;rel='next'
                # this line extracts the URL from the angle brackets surrounding it.
                next_batch_url = urlparse.urlparse(pagination_header.split("<")[1].split(">")[0])
                request_path   = next_batch_url.path + "?" + next_batch_url.query

    # remove potential duplicate values from the list of drawers.
    seen_drawer_ids = set()
    unique_drawers  = []

    for drawer in drawers:
        if drawer["id"] in seen_drawer_ids:
            continue

        opened_at  = datetime.datetime.strptime(drawer["opened_at"].replace("Z",""), "%Y-%m-%dT%H:%M:%S")
        opened_at -= datetime.timedelta(hours=6)

        if (opened_at < datetime.datetime.strptime(begin[:-6],"%Y-%m-%dT%H:%M:%S")):
            continue

        seen_drawer_ids.add(drawer["id"])
        unique_drawers.append(drawer)

    connection.close()
    return unique_drawers


########################################################################################################################
def get_payments (date=False, current=False):
    """
    downloads all of a business's payments.
    """

    global log

    # make sure to URL-encode all parameters.
    if not date:
        reportdate = datetime.datetime.today()-datetime.timedelta(days=1)
        end        = datetime.datetime.today()
        end        = end.strftime("%Y-%m-%dT04:00:00-06:00")

    else:
        try:
            reportdate = datetime.datetime.strptime(date,"%Y-%m-%d")
        except:
            reportdate = date

        end = (reportdate+datetime.timedelta(days=1)).strftime("%Y-%m-%dT04:00:00-06:00")

    if current:
        if not date:
            if int(time.strftime("%H")) < 4:
                begin = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%dT08:00:00-06:00")
            else:
                begin = datetime.datetime.today().strftime("%Y-%m-%dT08:00:00-06:00")
        else:
            begin = date + "T08:00:00-06:00"

        parameters = urllib.urlencode({"begin_time": begin})

    else:
        begin      = reportdate.strftime("%Y-%m-%dT08:00:00-06:00")
        parameters = urllib.urlencode({"begin_time": begin, "end_time" : end})

    payments = []

    # the base URL for every Connect API request.
    connection = httplib.HTTPSConnection("connect.squareup.com")

    # For each location...
    for location_id in location_ids:
        request_path = "/v1/" + location_id + "/payments?" + parameters
        more_results = True

        # ...as long as there are more payments to download from the location...
        while more_results:

            # ...send a GET request to /v1/LOCATION_ID/payments
            connection.request("GET", request_path, "", request_headers)
            response = connection.getresponse()

            # Read the response body JSON into the cumulative list of results
            payments = payments + json.loads(response.read())

            # Check whether pagination information is included in a response header, indicating more results
            pagination_header = response.getheader("link", "")

            if "rel='next'" not in pagination_header:
                more_results = False

            else:

                # extract the next batch URL from the header.
                # pagination headers have the following format:
                # <https://connect.squareup.com/v1/LOCATION_ID/payments?batch_token=BATCH_TOKEN>;rel='next'
                # this line extracts the URL from the angle brackets surrounding it.
                next_batch_url = urlparse.urlparse(pagination_header.split("<")[1].split(">")[0])
                request_path   = next_batch_url.path + "?" + next_batch_url.query

    # remove potential duplicate values from the list of payments.
    seen_payment_ids = set()
    unique_payments  = []

    for payment in payments:
        if payment['id'] in seen_payment_ids:
            continue

        seen_payment_ids.add(payment['id'])
        unique_payments.append(payment)

    connection.close()
    return unique_payments


########################################################################################################################
def print_transactions_report (transactions):
    total = 0
    for transaction in transactions:
        for t in transaction['tenders']:
            total += int(t['amount_money']['amount'])

    return total


########################################################################################################################
def get_transactions (date=False, current=False):
    global log

    # Make sure to URL-encode all parameters
    if not date:
        reportdate = datetime.datetime.today()-datetime.timedelta(days=1)
        end        = datetime.datetime.today()
        end       = end.strftime("%Y-%m-%dT04:00:00-06:00")

    else:
        try:
            reportdate = datetime.datetime.strptime(date,"%Y-%m-%d")
        except:
            reportdate = date

        end = (reportdate+datetime.timedelta(days=1)).strftime("%Y-%m-%dT04:00:00-06:00")
    if current:

        if not date:

            if int(time.strftime("%H")) < 4:
                begin = (datetime.datetime.today()-datetime.timedelta(days=1)).strftime("%Y-%m-%dT08:00:00-06:00")
                end   = datetime.datetime.today()
                end   = end.strftime("%Y-%m-%dT04:00:00-06:00")

            else:
                begin = datetime.datetime.today().strftime("%Y-%m-%dT08:00:00-06:00")
                end   = datetime.datetime.today()
                end   = end.strftime("%Y-%m-%dT23:59:59-06:00")

        else:
            begin = date + "T08:00:00-06:00"

        parameters = urllib.urlencode({'begin_time': begin})

    else:
        begin = reportdate.strftime("%Y-%m-%dT08:00:00-06:00")

    # the base URL for every Connect API request.
    transactions = []
    connection   = httplib.HTTPSConnection("connect.squareup.com")

    # For each location...
    for location_id in location_ids:
        more_results = True
        cursor       = ""

        # ...as long as there are more payments to download from the location...
        while more_results:

            if cursor:
                parameters = urllib.urlencode({"begin_time": begin, "end_time" : end, "cursor":cursor})
            else:
                parameters = urllib.urlencode({"begin_time": begin, "end_time" : end})

            # ...send a GET request to /v1/LOCATION_ID/payments
            request_path = "/v2/locations/" + location_id + "/transactions?" + parameters

            connection.request("GET", request_path, "", request_headers)

            response = connection.getresponse()
            data     = response.read()

            try:
                output = json.loads(data)["transactions"]
            except:
                break

            # read the response body JSON into the cumulative list of results.
            transactions = transactions + output

            if "cursor" in json.loads(data).keys():
                if json.loads(data)["cursor"]:
                    cursor = json.loads(data)["cursor"]

            else:
                more_results = False

    # remove potential duplicate values from the list of payments.
    seen_transaction_ids = set()
    unique_transactions   = []

    for transaction in transactions:
        if transaction["id"] in seen_transaction_ids:
            continue

        seen_transaction_ids.add(transaction["id"])
        unique_transactions.append(transaction)

    connection.close()

    with open(homepath + "transactions.txt", "w") as fh:
        fh.write(str(unique_transactions))

    return unique_transactions

def calculate_sin_discount(amount, quantity, item,items):

    price = False
    for it in items:
        item_data = it.item_data
        name = item_data.name.lower()
        var = item_data.variations
        it_price = 0
        for v in var:
            variation_data = v.item_variation_data
            price_money = variation_data.price_money
            try:
                it_price = price_money.amount
            except:
                pass
            if price: break
        if price: continue
        tmp = item.lower().replace('sin ','')
        if 'dom beer' in tmp:
            tmp = 'budweiser'
        elif 'draft' in tmp:
            tmp = 'hans pils'
        elif 'imp beer' in tmp:
            tmp = 'dos xx'
        elif 'jack' in tmp:
            tmp = 'jack daniels'
        elif 'well' in tmp:
            tmp = 'well rum'
        elif 'espolon' in tmp:
            tmp = 'espolon silver'
        if tmp == name:
            price = it_price
        elif tmp in name:
            if 'jack' in tmp: continue
            price = it_price
        
    if not price: 
        price = '800'
    discount = (int(amount)*quantity)-(int(price)*quantity)
    return discount

        


########################################################################################################################
def sales_totals(payments,drawers,reportd):
    """
    prints a sales report based on a list of payments.
    """

    global log

    total      = {}
    categories = []

    if not reportd:
        reportd = datetime.datetime.strptime(report_date,"%Y-%m-%d")

     # variables for holding cumulative values of various monetary amounts.
    total["sjs_tips"]         = 0
    total["jacks_tips"]       = 0
    total["sjs_refunds"]      = 0
    total["jacks_refunds"]    = 0
    total["sjs_beer"]         = 0
    total["jacks_beer"]       = 0
    total["sjs_liquor"]       = 0
    total["jacks_liquor"]     = 0
    total["sjs_retail"]       = 0
    total["jacks_retail"]     = 0
    total["sjs_alcohol"]      = 0
    total["jacks_alcohol"]    = 0
    total["sjs_nonalc"]       = 0
    total["jacks_nonalc"]     = 0
    total["sjs_comps"]        = 0
    total["jacks_comps"]      = 0
    total["sjs_dcounts"]      = 0
    total["jacks_dcounts"]    = 0
    total["sjs_spills"]      = 0
    total["jacks_spills"]    = 0
    total["sjs_total"]        = 0
    total["jacks_total"]      = 0
    total["sjs_credit"]       = 0
    total["jacks_credit"]     = 0
    total["sjs_wine"]         = 0
    total["jacks_wine"]       = 0
    total["sjs_service"]      = 0
    total["jacks_service"]    = 0
    total["sjs_tip_credit"]   = 0
    total["jacks_tip_credit"] = 0
    total["sjs_paidout"]      = 0
    total["jacks_paidout"]    = 0
    total["sjs_cash"]         = 0
    total["jacks_cash"]       = 0
    total["unknown"]          = 0
    
    items = get_items()
    # @LOGAN? add some comments please.
    # add appropriate values to each cumulative variable.
    for payment in payments:

        if "device" not in payment.keys():
            if not payment["refunds"]:
                for i in xrange(len(payment["itemizations"])):
                    category  = payment["itemizations"][i]["item_detail"]["category_name"]
                    amount    = 0
                    amount   += payment["itemizations"][i]["single_quantity_money"]["amount"]*int(float(payment["itemizations"][i]["quantity"]))
            total["unknown"] += amount

        elif "name" not in payment["device"].keys():
            if not payment["refunds"]:
                for i in xrange(len(payment["itemizations"])):
                    category  = payment["itemizations"][i]["item_detail"]["category_name"]
                    amount    = 0
                    amount   += payment["itemizations"][i]["single_quantity_money"]["amount"]*int(float(payment["itemizations"][i]["quantity"]))
            total["unknown"] += amount

        elif "sanjac" in payment["device"]["name"].lower():
            if not payment["refunds"]:
                for i in xrange(len(payment["itemizations"])):
                    category = payment["itemizations"][i]["item_detail"]["category_name"]
                    amount   = 0
                    amount  += payment["itemizations"][i]["single_quantity_money"]["amount"]*int(float(payment["itemizations"][i]["quantity"]))

                    if "sin " in payment["itemizations"][i]['name'].lower():
                        discount = calculate_sin_discount(payment["itemizations"][i]["single_quantity_money"]["amount"],int(float(payment["itemizations"][i]["quantity"])),payment["itemizations"][i]['name'],items)
                        total["sjs_dcounts"] += discount

                    for d in xrange(len(payment["itemizations"][i]["discounts"])):
                        if 'spill' in payment["itemizations"][i]["discounts"][d]['name'].lower(): 
                            total["sjs_spills"] += payment["itemizations"][i]["discounts"][d]["applied_money"]["amount"]
                        amount += payment["itemizations"][i]["discounts"][d]["applied_money"]["amount"]
                        total["sjs_comps"] += payment["itemizations"][i]["discounts"][d]["applied_money"]["amount"]

                    if category not in categories:
                        categories.append(category)

                    if "beer" in category.lower():
                        total["sjs_total"]       = total["sjs_total"]   + amount
                        total["sjs_beer"]        = total["sjs_beer"]    + amount
                        total["sjs_alcohol"]     = total["sjs_alcohol"] + amount

                    elif "retail" in category.lower():
                        total["sjs_total"]       = total["sjs_total"]   + amount
                        total["sjs_retail"]      = total["sjs_retail"]  + amount

                    elif "non/alc" in category.lower():
                        total["sjs_total"]       = total["sjs_total"]   + amount
                        total["sjs_nonalc"]      = total["sjs_nonalc"]  + amount

                    elif "wine" in category.lower():
                        total["sjs_total"]       = total["sjs_total"]   + amount
                        total["sjs_wine"]        = total["sjs_wine"]    + amount

                    elif "room" in category.lower():
                        total["sjs_total"]       = total["sjs_total"]   + amount
                        total["sjs_service"]     = total["sjs_service"] + amount

                    else:
                        total["sjs_total"]       = total["sjs_total"]   + amount
                        total["sjs_liquor"]      = total["sjs_liquor"]  + amount
                        total["sjs_alcohol"]     = total["sjs_alcohol"] + amount

            total["sjs_refunds"] = total["sjs_refunds"] + payment["refunded_money"]["amount"]
            total["sjs_tips"]    = total["sjs_tips"]    + payment["tip_money"]["amount"]

            for p in xrange(len(payment["tender"])):
                if "credit" in str(payment["tender"][p]["type"]).lower():
                    total["sjs_credit"]     += payment["tender"][p]["total_money"]["amount"]
                    total["sjs_credit"]     -= payment["tender"][p]["refunded_money"]["amount"]
                    total["sjs_tip_credit"] += payment["tip_money"]["amount"]

                if "cash" in str(payment["tender"][p]["type"]).lower():
                    total["sjs_cash"] += payment["tender"][p]["total_money"]["amount"]
                    total["sjs_cash"] -= payment["tender"][p]["refunded_money"]["amount"]

        # @LOGAN? add some comments please.
        else:

            if not payment["refunds"]:
                for i in xrange(len(payment["itemizations"])):
                    category = payment["itemizations"][i]["item_detail"]["category_name"]
                    amount   = 0
                    amount  += payment["itemizations"][i]["single_quantity_money"]["amount"] * int(float(payment["itemizations"][i]["quantity"]))

                    if "sin " in payment["itemizations"][i]['name'].lower():
                        discount = calculate_sin_discount(payment["itemizations"][i]["single_quantity_money"]["amount"],int(float(payment["itemizations"][i]["quantity"])),payment["itemizations"][i]['name'],items)
                        total["jacks_dcounts"] += discount

                    for d in xrange(len(payment["itemizations"][i]["discounts"])):
                        if 'spill' in payment["itemizations"][i]["discounts"][d]['name'].lower():
                            total["jacks_spills"] += payment["itemizations"][i]["discounts"][d]["applied_money"]["amount"]
                        amount += payment["itemizations"][i]["discounts"][d]["applied_money"]["amount"]
                        total["jacks_comps"] += payment["itemizations"][i]["discounts"][d]["applied_money"]["amount"]

                    if category not in categories:
                        categories.append(category)

                    if "beer" in category.lower():
                        total["jacks_total"]   = total["jacks_total"]    + amount
                        total["jacks_beer"]    = total["jacks_beer"]     + amount
                        total["jacks_alcohol"] = total["jacks_alcohol"]  + amount

                    elif "retail" in category.lower():
                        total["jacks_total"]   = total["jacks_total"]    + amount
                        total["jacks_retail"]  = total["jacks_retail"]   + amount

                    elif "non/alc" in category.lower():
                        total["jacks_total"]   = total["jacks_total"]    + amount
                        total["jacks_nonalc"]  = total["jacks_nonalc"]   + amount

                    elif "wine" in category.lower():
                        total["jacks_total"]   = total["jacks_total"]    + amount
                        total["jacks_wine"]    = total["jacks_wine"]     + amount

                    elif "room" in category.lower():
                        total["jacks_total"]   = total["jacks_total"]    + amount
                        total["jacks_service"] = total["jacks_service"]  + amount

                    else:
                        total["jacks_total"]   = total["jacks_total"]    + amount
                        total["jacks_liquor"]  = total["jacks_liquor"]   + amount
                        total["jacks_alcohol"] = total["jacks_alcohol"]  + amount

            total["jacks_refunds"] = total["jacks_refunds"] + payment["refunded_money"]["amount"]
            total["jacks_tips"]    = total["jacks_tips"]    + payment["tip_money"]["amount"]

            for p in xrange(len(payment["tender"])):
                if "credit" in str(payment["tender"][p]["type"]).lower():
                    total["jacks_credit"]     += payment["tender"][p]["total_money"]["amount"]
                    total["jacks_credit"]     -= payment["tender"][p]["refunded_money"]["amount"]
                    total["jacks_tip_credit"] += payment["tip_money"]["amount"]

                if "cash" in str(payment["tender"][p]["type"]).lower():
                    total["jacks_cash"] += payment["tender"][p]["total_money"]["amount"]
                    total["jacks_cash"] -= payment["tender"][p]["refunded_money"]["amount"]

    for drawer in drawers:
        if "name" not in drawer["device"].keys():
            continue

        if "sanjac" in drawer["device"]["name"].lower():
            total["sjs_paidout"] += drawer["cash_paid_out_money"]["amount"]
            total["sjs_cash"]    += drawer["cash_paid_in_money"]["amount"]

        else:
            total["jacks_paidout"] += drawer["cash_paid_out_money"]["amount"]
            total["jacks_cash"]    += drawer["cash_paid_in_money"]["amount"]

    return total


########################################################################################################################
def fill_db (reportd, total, timeframe):
    """
    @LOGAN? what's this for?
    """

    if "day" in timeframe:
        daily  = get_row("daily", reportd)
        update = False

        if daily:
            d      = Daily(daily["id"])
            update = True 
        else:
            d = Daily()

    elif "week" in timeframe:
        weekly = get_row("weekly", reportd)
        update = False

        if weekly:
            d      = Weekly(weekly["id"])
            update = True
        else:
            d = Weekly()

    elif "month" in timeframe:
        monthly = get_row("monthly", reportd)
        update  = False

        if monthly:
            d      = Monthly(monthly["id"])
            update = True
        else:
            d = Monthly()

    elif "year" in timeframe:
        yearly = get_row("yearly", reportd)
        update = False

        if yearly:
            d      = Yearly(yearly["id"])
            update = True
        else:
            d = Yearly()

    d["date"]             = str(reportd)
    d["sjs_liquor"]       = total["sjs_liquor"]
    d["sjs_beer"]         = total["sjs_beer"]
    d["sjs_wine"]         = total["sjs_wine"]
    d["sjs_redbull"]      = 0
    d["sjs_nonalc"]       = total["sjs_nonalc"]
    d["sjs_service"]      = total["sjs_service"]
    d["sjs_retail"]       = total["sjs_retail"]
    d["sjs_total"]        = total["sjs_total"]
    d["sjs_credit"]       = total["sjs_credit"]
    d["sjs_tips"]         = total["sjs_tips"]
    d["sjs_refunds"]      = total["sjs_refunds"]
    d["sjs_alcohol"]      = total["sjs_alcohol"]
    d["sjs_dcounts"]      = total["sjs_dcounts"]
    d["sjs_paidout"]      = total["sjs_paidout"]
    d["sjs_cash"]         = total["sjs_cash"]
    d["jacks_liquor"]     = total["jacks_liquor"]
    d["jacks_beer"]       = total["jacks_beer"]
    d["jacks_wine"]       = total["jacks_wine"]
    d["jacks_redbull"]    = 0
    d["jacks_nonalc"]     = total["jacks_nonalc"]
    d["jacks_service"]    = total["jacks_service"]
    d["jacks_retail"]     = total["jacks_retail"]
    d["jacks_total"]      = total["jacks_total"]
    d["jacks_credit"]     = total["jacks_credit"]
    d["jacks_tips"]       = total["jacks_tips"]
    d["jacks_refunds"]    = total["jacks_refunds"]
    d["jacks_alcohol"]    = total["jacks_alcohol"]
    d["jacks_dcounts"]    = total["jacks_dcounts"]
    d["jacks_paidout"]    = total["jacks_paidout"]
    d["jacks_cash"]       = total["jacks_cash"]
    d["jacks_tip_credit"] = total["jacks_tip_credit"]
    d["sjs_tip_credit"]   = total["sjs_tip_credit"]
    d["unknown"]          = total["unknown"]
    d["sjs_comps"]        = total["sjs_comps"]
    d["jacks_comps"]      = total["jacks_comps"]
    d["sjs_spills"]       = total["sjs_spills"]
    d["jacks_spills"]     = total["jacks_spills"]
    for k in d.keys():
        if not d[k]: 
            d[k] = 0
    if update:
        d.update()
    else:
        d.insert()

    return d

### input dates and duration(in weeks)
def get_recent_sales(date,duration):
    week = 0
    sjs_sales = []
    jacks_sales = []
    while week < duration:
        daily = get_row("daily", date.strftime("%Y-%m-%d"))
        if daily:
            d      = Daily(daily["id"])
        else:
            return
        sjs_sales.append(d['sjs_total'])
        jacks_sales.append(d['jacks_total'])
        date = date-datetime.timedelta(weeks=1)
        week += 1
    return (sjs_sales,jacks_sales)

### input dates and duration(in weeks)
def get_recent_average(date,duration):
    sales = get_recent_sales(date,duration)
    sjs = sales[0]
    jacks = sales[1]
    sjs_average = sum(sjs)/len(sjs)
    jacks_average = sum(jacks)/len(jacks)
    return (sjs_average,jacks_average)

### input dates and duration(in weeks)
def get_recent_sales_best(date,duration):
    sales = get_recent_sales(date,duration)
    sjs = sales[0]
    jacks = sales[1]
    sjs_best = max(sjs)
    jacks_best = max(jacks)
    return (sjs_best,jacks_best)

### input dates and duration(in weeks)
def get_recent_sales_worst(date,duration):
    sales = get_recent_sales(date,duration)
    sjs = sales[0]
    try:sjs.remove(0)
    except:pass
    jacks = sales[1]
    try:jacks.remove(0)
    except:pass
    sjs_worst = min(sjs)
    jacks_worst = min(jacks)
    return (sjs_worst,jacks_worst)

#######################################################################################################################
def daily_sales (date):
    """
    @LOGAN? what's this for?
    """

    global log

    full_report = "==%s SALES REPORT==\n" % date.strftime("%a, %b %-d %Y")
    payments    = get_payments(date)

    try:
        drawers = get_cash_drawer(date)
    except Exception as e:
        drawers = []
        ts      = time.time()
        log    += "[%s]: %s" % (datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"), e)

    try:
        reportdate = datetime.datetime.strptime(date,"%Y-%m-%d")
    except:
        reportdate = date

    # @LOGAN? add some comments please.
    sales        = sales_totals(payments, drawers, reportdate)
    full_report += report_string(sales)

    #####
    ## LAST YEAR
    #####

    last_year_report_date = reportdate + dateutil.relativedelta.relativedelta(years=-1, weekday=reportdate.weekday())
    last_year_payments    = get_payments(last_year_report_date.strftime("%Y-%m-%d"))

    try:
        last_year_drawers = get_cash_drawer(last_year_report_date.strftime("%Y-%m-%d"))

    except Exception as e:
        last_year_drawers = []
        ts                = time.time()
        log              += "[%s]: %s"%(datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"), e)

    full_report    += "\n"
    full_report    += "===LAST YEAR===\n"
    full_report    += '==%s SALES REPORT==\n'%last_year_report_date.strftime("%a, %b %-d %Y")
    last_year_sales = sales_totals(last_year_payments,last_year_drawers,last_year_report_date)
    full_report    += report_string(last_year_sales)
    full_report    += "\n"

    reportd = reportdate.strftime("%Y-%m-%d")
    fill_db(reportd,sales, "day")
    
    full_report    += "===RECENT COMPARISONS===\n"
    full_report    += "     =San Jac=\n"
    full_report    += "%s  %-20s %-15s %-15s\n"%("                              ",date.strftime("%a, %b %-d %Y"),"Value","Difference")
    full_report    += "%s    %-25s %-15s %-15s\n"%(" 3 Week Average:",format_money(sales['sjs_total']),format_money(get_recent_average(reportdate,3)[0]),format_money(sales['sjs_total'] - get_recent_average(reportdate,3)[0]))
    full_report    += "%s    %-25s %-15s %-15s\n"%("3 Month Average:",format_money(sales['sjs_total']),format_money(get_recent_average(reportdate,12)[0]),format_money(sales['sjs_total'] - get_recent_average(reportdate,12)[0]))
    full_report    += "%s    %-25s %-15s %-15s\n"%("      6 Month Best:",format_money(sales['sjs_total']),format_money(get_recent_sales_best(reportdate,26)[0]),format_money(sales['sjs_total'] - get_recent_sales_best(reportdate,26)[0]))
    full_report    += "%s    %-25s %-15s %-15s\n"%("    6 Month Worst:",format_money(sales['sjs_total']),format_money(get_recent_sales_worst(reportdate,26)[0]),format_money(sales['sjs_total'] - get_recent_sales_worst(reportdate,26)[0]))
    full_report    += "%s    %-25s %-15s %-15s\n"%("    12 Month Best:",format_money(sales['sjs_total']),format_money(get_recent_sales_best(reportdate,52)[0]),format_money(sales['sjs_total'] - get_recent_sales_best(reportdate,52)[0]))
    full_report    += "%s    %-25s %-15s %-15s\n"%(" 12 Month Worst:",format_money(sales['sjs_total']),format_money(get_recent_sales_worst(reportdate,52)[0]),format_money(sales['sjs_total'] - get_recent_sales_worst(reportdate,52)[0]))
    full_report    += "\n"
    full_report    += "     =Jack's=\n"
    full_report    += "%s  %-20s %-15s %-15s\n"%("                              ",date.strftime("%a, %b %-d %Y"),"Value","Difference")
    full_report    += "%s    %-25s %-15s %-15s\n"%(" 3 Week Average:",format_money(sales['jacks_total']),format_money(get_recent_average(reportdate,3)[1]),format_money(sales['jacks_total'] - get_recent_average(reportdate,3)[1]))
    full_report    += "%s    %-25s %-15s %-15s\n"%("3 Month Average:",format_money(sales['jacks_total']),format_money(get_recent_average(reportdate,12)[1]),format_money(sales['jacks_total'] - get_recent_average(reportdate,12)[1]))
    full_report    += "%s    %-25s %-15s %-15s\n"%("      6 Month Best:",format_money(sales['jacks_total']),format_money(get_recent_sales_best(reportdate,26)[1]),format_money(sales['jacks_total'] - get_recent_sales_best(reportdate,26)[1]))
    full_report    += "%s    %-25s %-15s %-15s\n"%("    6 Month Worst:",format_money(sales['jacks_total']),format_money(get_recent_sales_worst(reportdate,26)[1]),format_money(sales['jacks_total'] - get_recent_sales_worst(reportdate,26)[1]))
    full_report    += "%s    %-25s %-15s %-15s\n"%("    12 Month Best:",format_money(sales['jacks_total']),format_money(get_recent_sales_best(reportdate,52)[1]),format_money(sales['jacks_total'] - get_recent_sales_best(reportdate,52)[1]))
    full_report    += "%s    %-25s %-15s %-15s\n"%(" 12 Month Worst:",format_money(sales['jacks_total']),format_money(get_recent_sales_worst(reportdate,52)[1]),format_money(sales['jacks_total'] - get_recent_sales_worst(reportdate,52)[1]))

    return sales, full_report


########################################################################################################################
def weekly_sales (date, report=False, recursive=False):
    """
    @LOGAN? what's this for?
    """

    global log

    if not date:
        date = datetime.datetime.today()-datetime.timedelta(days=1)

    original_date = date
    date          = date - datetime.timedelta(days=6)
    day           = 0
    weekly_total  = {}
    full_report   = ""

    while day < 7:
        if (date+datetime.timedelta(days=day)).strftime("%Y-%m-%d") >= datetime.datetime.today().strftime("%Y-%m-%d"):
            day += 1
            continue
        money = get_row("daily", (date+datetime.timedelta(days=day)).strftime("%Y-%m-%d"))

        for item in money:
            if item in weekly_total.keys():
                try:
                    weekly_total[item] += money[item]
                except:
                    weekly_total[item] = money[item]
            else:
                weekly_total[item] = money[item]

        day+= 1

    # @LOGAN? add some comments please.
    if not recursive:
        # create the report.
        full_report = "==WEEKLY SALES REPORT==\n"
        full_report += report_string(weekly_total)

        # fill the database.
        fill_db(date.strftime("%Y-%m-%d"), weekly_total,"week")

        #### LAST YEAR ####
        full_report += "==LAST YEAR WEEKLY SALES REPORT==\n"
        last_year_report_date = original_date + dateutil.relativedelta.relativedelta(years=-1, weekday=original_date.weekday())
        full_report += weekly_sales(last_year_report_date,recursive=True)[1]

    else:
        return weekly_total, report_string(weekly_total)

    return weekly_total, full_report


########################################################################################################################
def monthly_sales (date, recursive=False):
    """
    @LOGAN? what's this for?
    """

    global log

    if not date:
        date = datetime.datetime.today() - datetime.timedelta(days=1)

    date          = date.replace(day=1)
    month         = int(date.strftime("%m"))
    sdate         = date
    day           = 0
    monthly_total = {}
    full_report   = ""

    while int((date+datetime.timedelta(days=day)).strftime("%m")) == month:
        if (date + datetime.timedelta(days=day)).strftime("%Y-%m-%d") >= date.today().strftime("%Y-%m-%d"):
            day += 1
            continue
        money = get_row("daily", (date+datetime.timedelta(days=day)).strftime("%Y-%m-%d"))
        if not money: 
            day+= 1
            continue
        for item in money:
            if item in monthly_total.keys():
                try:
                    monthly_total[item]+=money[item]
                except:
                    monthly_total[item]=money[item]
            else:
                monthly_total[item] = money[item]
        day+= 1

    if not recursive:
        # create the report.
        full_report = "==MONTHLY SALES REPORT==\n"
        full_report += report_string(monthly_total)

        # fill the database.
        fill_db(date.strftime("%Y-%m-%d"),monthly_total,"month")

        #### LAST YEA R####
        full_report += "==LAST YEAR MONTHLY SALES REPORT==\n"
        last_year_report_date = sdate + dateutil.relativedelta.relativedelta(years=-1)
        full_report += monthly_sales(last_year_report_date,recursive=True)

        ######TAXES######
        non_alc = (monthly_total["sjs_retail"]+monthly_total["jacks_retail"]+monthly_total["sjs_nonalc"]+monthly_total["jacks_nonalc"])
        total_alc = (monthly_total["sjs_liquor"]+monthly_total["jacks_liquor"]+monthly_total["sjs_wine"]+monthly_total["jacks_wine"]+monthly_total["sjs_beer"]+monthly_total["jacks_beer"])
        other_sales = (monthly_total["sjs_total"]+monthly_total["jacks_total"])-non_alc-total_alc

        full_report += "\n"
        full_report += "    =TAX INFO=\n"
        full_report += "--MIXED BEVERAGE GROSS RECEIPTS--\n"
        full_report += "Complimentary Drinks:" + format_money((monthly_total["sjs_comps"]+monthly_total["jacks_comps"])*.87) + "\n"
        full_report += "Gross Liquor:        " + format_money((monthly_total["sjs_liquor"]+monthly_total["jacks_liquor"])*.87) + "\n"
        full_report += "Gross Wine:          " + format_money((monthly_total["sjs_wine"]+monthly_total["jacks_wine"])*.87) + "\n"
        full_report += "Gross Beer:          " + format_money((monthly_total["sjs_beer"]+monthly_total["jacks_beer"])*.87) + "\n"
        full_report += "Total Gross Taxable: " + format_money(total_alc*.87) + "\n"
        full_report += "--MIXED BEVERAGE SALES--\n"
        full_report += "Total Sales:         " + format_money((non_alc*.9175)+(total_alc*.87)+other_sales) + "\n"
        full_report += "Taxable Sales:       " + format_money((monthly_total["sjs_liquor"]+monthly_total["jacks_liquor"]+monthly_total["sjs_wine"]+monthly_total["jacks_wine"]+monthly_total["sjs_beer"]+monthly_total["jacks_beer"])*.87) + "\n"
        full_report += "--SALES AND USE--\n"
        full_report += "Total Sales:         " + format_money((non_alc*.9175)+(total_alc*.87)+other_sales) + "\n"
        full_report += "Taxable Sales:       " + format_money(non_alc*.9175) + "\n"
        full_report += "Taxable Purchases:   " + format_money(((monthly_total["sjs_comps"]+monthly_total["jacks_comps"])*.87)*.2) + "\n"

    else:
        return report_string(monthly_total)

    return monthly_total, full_report


########################################################################################################################
def yearly_sales (date, recursive=False):
    """
    @LOGAN? what's this for?
    """

    global log
    if not date:
        date = datetime.datetime.today()

        date         = date.replace(day=1)
        date         = date.replace(month=1)
        sdate        = date
        yearly_total = {}
        full_report  = ""

        while int(date.strftime("%m")) < datetime.datetime.today().strftime("%m"):

            if date.strftime("%Y-%m-%d") > date.today().strftime("%Y-%m-%d"):
                break

            money = get_row("monthly",date.strftime("%Y-%m-%d"))

            if not money:
                populate_database(date)
                money = get_row("monthly",date.strftime("%Y-%m-%d"))

            for item in money:
                if item in yearly_total.keys():
                    try:
                        yearly_total[item]+=money[item]
                    except:
                        yearly_total[item]=money[item]
                else:
                    yearly_total[item] = money[item]

            date = date + datetime.timedelta(days=31)
            date = date.replace(day=1)

    else:
        sdate         = date.replace(day=1)
        sdate         = sdate.replace(month=1)
        yearly_total = {}
        full_report  = ""

        while int(sdate.strftime("%Y")) < int((date + dateutil.relativedelta.relativedelta(days=1)).strftime("%Y")):

            money = get_row("monthly",sdate.strftime("%Y-%m-%d"))

            for item in money:
                if item in yearly_total.keys():
                    try:
                        yearly_total[item]+=money[item]
                    except:
                        yearly_total[item]=money[item]
                else:
                    yearly_total[item] = money[item]

            sdate = sdate + datetime.timedelta(days=31)
            sdate = sdate.replace(day=1)
            
    if not recursive:
        # create the report.
        full_report = "==YEARLY SALES REPORT==\n"
        full_report += report_string(yearly_total)

        # fill the database.
        fill_db(sdate.strftime("%Y-%m-%d"), yearly_total, "yearly")

        #### LAST YEAR ####
        #full_report += "==LAST YEAR SALES REPORT==\n"
        #last_year_report_date = sdate + dateutil.relativedelta.relativedelta(years=-1)
        #full_report += yearly_sales(last_year_report_date,recursive=True)
    else:
        return report_string(yearly_total)

    return yearly_total, full_report


########################################################################################################################
def get_month ():
    global log

    date        = datetime.datetime.today()
    date        = date.replace(day=1)
    month_total = monthly_sales(date)[0]
    full_report = "MTD SALES:\n"
    full_report += "San Jac:           " + format_money(month_total["sjs_total"])   +"\n"
    full_report += "Jack's:            " + format_money(month_total["jacks_total"]) +"\n"
    full_report += "Total:             " + format_money(month_total["jacks_total"]  + month_total["sjs_total"]) + "\n"
    total_discount = -1.0*(month_total["sjs_dcounts"]+month_total["jacks_dcounts"]+month_total["sjs_comps"]+month_total["jacks_comps"])
    total_sales = month_total["sjs_total"]+month_total["jacks_total"]
    try:discount_percentage = "%.02f"%((total_discount/total_sales)*100)
    except:discount_percentage = "Error"
    full_report += "Discount Percentage: %s"%discount_percentage

    pickle.dump(full_report, open("/opt/sjs/financial-automations/month.p", "wb"))
    return full_report


########################################################################################################################
def get_year (custom_date=False):
    global log

    if not custom_date:
        year_total  = yearly_sales(False)[0]
    else:
        date = custom_date
        year_total  = yearly_sales(date)[0]
    
    full_report = "YTD SALES:\n"
    full_report += "San Jac:           " + format_money(year_total["sjs_total"])   + "\n"
    full_report += "Jack's:            " + format_money(year_total["jacks_total"]) + "\n"
    full_report += "Total:             " + format_money(year_total["jacks_total"]  + year_total["sjs_total"]) + "\n"
    total_discount = -1.0*(year_total["sjs_dcounts"]+year_total["jacks_dcounts"]+year_total["sjs_comps"]+year_total["jacks_comps"])
    total_sales = year_total["sjs_total"]+year_total["jacks_total"]
    try:discount_percentage = "%.02f"%((total_discount/total_sales)*100)
    except:discount_percentage = "Error"
    full_report += "Discount Percentage: %s"%discount_percentage

    if custom_date:
        return year_total

    pickle.dump(full_report, open("/opt/sjs/financial-automations/year.p", "wb"))

    return full_report


########################################################################################################################
def report_string (total):
    return_string = ""
    return_string += "     =San Jac=\n"
    return_string += "Total:             " + format_money(total["sjs_total"])   + "\n"
    return_string += "Total Alcohol:     " + format_money(total["sjs_alcohol"]) + "\n"
    return_string += "Total Non-Alcohol: " + format_money(total["sjs_retail"]   + total["sjs_nonalc"]) + "\n"
    return_string += "Total Taxes:       " + format_money((total["sjs_alcohol"] * .027) + (total["sjs_total"] * .0825)) + "\n"
    return_string += "\n"
    return_string += "Liquor:            " + format_money(total["sjs_liquor"])        + "\n"
    return_string += "Beer:              " + format_money(total["sjs_beer"])          + "\n"
    return_string += "Wine:              " + format_money(total["sjs_wine"])          + "\n"
    return_string += "Non-Alcohol:       " + format_money(total["sjs_nonalc"])        + "\n"
    return_string += "Service/Room:      " + format_money(total["sjs_service"])       + "\n"
    return_string += "Merch:             " + format_money(total["sjs_retail"])        + "\n"
    return_string += "Total Credit:      " + format_money(total["sjs_credit"])        + "\n"
    return_string += "Processing Fees:   " + format_money(total["sjs_credit"] * .025) + "\n"
    return_string += "\n"
    return_string += "Refunds:           " + format_money(total["sjs_refunds"]) + "\n"
    return_string += "Comps:             " + format_money(total["sjs_comps"]) + "\n"
    return_string += "Discounts:         " + format_money(total["sjs_dcounts"]) + "\n"
    return_string += "Spills:            " + format_money(total["sjs_spills"]) + "\n"
    return_string += "\n"
    return_string += "Cash In:           " + format_money(total["sjs_cash"])              + "\n"
    return_string += "Paid Out:          " + format_money(total["sjs_paidout"])           + "\n"
    return_string += "Tip Out:           " + format_money(0-total["sjs_tip_credit"])      + "\n"
    return_string += "Tip Processing:    " + format_money(total["sjs_tip_credit"] * .025) + "\n"
    return_string += "Net cash           " + format_money(total["sjs_cash"] + (total["sjs_paidout"] + total["sjs_tip_credit"]) + total["sjs_tip_credit"] * .025) + "\n"
    return_string += "\n"
    return_string += "     =Jack's=\n"
    return_string += "Total:             " + format_money(total["jacks_total"])   + "\n"
    return_string += "Total Alcohol:     " + format_money(total["jacks_alcohol"]) + "\n"
    return_string += "Total Non-Alcohol: " + format_money(total["jacks_retail"]   + total["jacks_nonalc"]) + "\n"
    return_string += "Total Taxes:       " + format_money((total["jacks_alcohol"] * .027)+(total["jacks_total"] * .0825)) + "\n"
    return_string += "\n"
    return_string += "Liquor:            " + format_money(total["jacks_liquor"])  + "\n"
    return_string += "Beer:              " + format_money(total["jacks_beer"])    + "\n"
    return_string += "Wine:              " + format_money(total["jacks_wine"])    + "\n"
    return_string += "Non-Alcohol:       " + format_money(total["jacks_nonalc"])  + "\n"
    return_string += "Service/Room:      " + format_money(total["jacks_service"]) + "\n"
    return_string += "Merch:             " + format_money(total["jacks_retail"])  + "\n"
    return_string += "Total Credit:      " + format_money(total["jacks_credit"])  + "\n"
    return_string += "Processing Fees:   " + format_money(total["jacks_credit"]   * .025) + "\n"
    return_string += "\n"
    return_string += "Refunds:           " + format_money(total["jacks_refunds"]) + "\n"
    return_string += "Comps:             " + format_money(total["jacks_comps"]) + "\n"
    return_string += "Discounts:         " + format_money(total["jacks_dcounts"]) + "\n"
    return_string += "Spills:            " + format_money(total["jacks_spills"]) + "\n"
    return_string += "\n"
    return_string += "Cash In:           " + format_money(total["jacks_cash"])              + "\n"
    return_string += "Paid Out:          " + format_money(total["jacks_paidout"])           + "\n"
    return_string += "Tip Out:           " + format_money(0-total["jacks_tip_credit"])      + "\n"
    return_string += "Tip Processing:    " + format_money(total["jacks_tip_credit"] * .025) + "\n"
    return_string += "Net cash:          " + format_money(total["jacks_cash"] + (total["jacks_paidout"] - total["jacks_tip_credit"])+total["jacks_tip_credit"]*.025) + "\n"
    return_string += "Unknown Device:    " + format_money(total["unknown"])   + "\n"
    return_string += "\n"
    return_string += "\n"
    total_discount = -1.0*(total["sjs_dcounts"]+total["jacks_dcounts"]+total["sjs_comps"]+total["jacks_comps"])
    total_sales = total["sjs_total"]+total["jacks_total"]
    try:discount_percentage = "%.02f"%((total_discount/total_sales)*100)
    except:discount_percentage = "Error"
    return_string += "Discount Percentage: %s"%discount_percentage
    return_string += "\n"
    return_string += "\n"

    
    return return_string


########################################################################################################################
def transactions (date=False, current=False):
    """
    @LOGAN? what's this for?
    """

    if current:
        transactions = get_transactions(current=True)

    if not date:
        transactions = get_transactions(report_date)
    else:
        transactions = get_transactions(date)

    total = 0
    with open (homepath + "trans_amounts.txt", "w") as fh:
        for t in transactions:
            if t["tenders"][0]["type"] == "CARD":
                amount = int(t["tenders"][0]["amount_money"]["amount"])
                total += amount
                fh.write("%s\n" % amount)


########################################################################################################################
def email_report (email=secrets["general"]["smtp_to"], report=False):
    global log
    global secrets

    if testing:
        email = secrets["general"]["smtp_to_test"]

    username = secrets["google"]["username"]
    password = secrets["google"]["password"]
    fromaddr = secrets["general"]["smtp_from"]
    toaddrs  = email
    msg      = "\r\n".join(["From: %s" % fromaddr, "To: %s" % toaddrs, "Subject: %s"%(report['subject']), "", report["body"]])

    try:
        server = smtplib.SMTP("smtp.gmail.com:587")
        server.starttls()
        server.login(username,password)
        server.sendmail(fromaddr, toaddrs, msg)
        server.quit()
    except:
        log += "\n%s: Failed to send report" % datetime.datetime.today().strftime("%Y-%m-%d:%H:%M")

########################################################################################################################
def rerun_numbers(starting_date):
    report_date = starting_date
    while datetime.datetime.date(datetime.datetime.strptime(report_date, "%Y-%m-%d")) < datetime.datetime.date(datetime.datetime.today()):
        sales = daily_sales(datetime.datetime.strptime(report_date, "%Y-%m-%d"))
        google_api.fill_sales(datetime.datetime.strptime(report_date, "%Y-%m-%d"), sales[0])
        report_date = datetime.datetime.strptime(report_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        report_date = datetime.datetime.strftime(report_date, "%Y-%m-%d")

########################################################################################################################
class Daily (dict):
    def __init__ (self, day_id=False):
        if day_id:
            self['id'] = day_id

            if self['id']:
                result = database("SELECT * FROM daily WHERE id = %s"%int(self['id']))[0]
                for k in result:
                    self[k] = result[k]

    def insert (self):
        keys   = str(self.keys())
        keys   = keys.replace('[', '(')
        keys   = keys.replace(']', ')')
        keys   = keys.replace("'", "")
        values = str(self.values())
        values = values.replace('[', '(')
        values = values.replace(']', ')')

        database("INSERT INTO daily %s VALUES %s" % (keys, values))

    def update (self):
        values = ""

        for key in self.keys():
            values += "%s='%s'," % (key, self[key])

        values = values[:-1]

        database("UPDATE daily set %s WHERE id=%s" % (values, self['id']))


########################################################################################################################
class Weekly (dict):
    def __init__ (self, week_id=False):
        if week_id:
            self['id'] = week_id

            if self['id']:
                result = database("SELECT * FROM weekly WHERE id = %s" % int(self['id']))[0]

                for k in result:
                    self[k] = result[k]

    def insert (self):
        keys   = str(self.keys())
        keys   = keys.replace('[', '(')
        keys   = keys.replace(']', ')')
        keys   = keys.replace("'", "")
        values = str(self.values())
        values = values.replace('[', '(')
        values = values.replace(']', ')')

        database("INSERT INTO weekly %s VALUES %s" % (keys, values))

    def update (self):
        values = ""

        for key in self.keys():
            values += "%s='%s'," % (key, self[key])

        values = values[:-1]

        database("UPDATE weekly set %s WHERE id=%s" % (values, self['id']))


########################################################################################################################
class Monthly (dict):
    def __init__ (self, month_id=False):
        if month_id:
            self['id'] = month_id

            if self['id']:
                result = database("SELECT * FROM monthly WHERE id = %s" % int(self['id']))[0]

                for k in result:
                    self[k] = result[k]

    def insert (self):
        keys   = str(self.keys())
        keys   = keys.replace('[', '(')
        keys   = keys.replace(']', ')')
        keys   = keys.replace("'", "")
        values = str(self.values())
        values = values.replace('[', '(')
        values = values.replace(']', ')')

        database("INSERT INTO monthly %s VALUES %s" % (keys ,values))

    def update (self):
        values = ""

        for key in self.keys():
            values += "%s='%s',"%(key,self[key])

        values = values[:-1]

        database("UPDATE monthly set %s WHERE id=%s" % (values, self['id']))


########################################################################################################################
class Yearly (dict):
    def __init__ (self, yearly_id=False):
        if yearly_id:
            self['id'] = yearly_id

            if self['id']:
                result = database("SELECT * FROM yearly WHERE id = %s" % int(self['id']))[0]

                for k in result:
                    self[k] = result[k]

    def insert (self):
        keys   = str(self.keys())
        keys   = keys.replace('[', '(')
        keys   = keys.replace(']', ')')
        keys   = keys.replace("'", "")
        values = str(self.values())
        values = values.replace('[', '(')
        values = values.replace(']', ')')

        database("INSERT INTO yearly %s VALUES %s" % (keys, values))

    def update (self):
        values = ""

        for key in self.keys():
            values += "%s='%s'," % (key, self[key])

        values = values[:-1]

        database("UPDATE yearly set %s WHERE id=%s" % (values, self['id']))


########################################################################################################################
if __name__ == '__main__':

    ###########################
    ###########DAILY###########
    ###########################

    sales = daily_sales(datetime.datetime.strptime(report_date, "%Y-%m-%d"))
    google_api.fill_sales(datetime.datetime.strptime(report_date, "%Y-%m-%d"), sales[0])
    email_report(report={'subject':'Report for %s' % report_date, 'body':sales[1]})
    fh.write(sales[1])

    ###########################
    ###########WEEKLY##########
    ###########################

    if 'sat' in datetime.datetime.strptime(report_date, "%Y-%m-%d").strftime("%a").lower():

        sales = weekly_sales(datetime.datetime.strptime(report_date, "%Y-%m-%d"))

        date = datetime.datetime.strptime(report_date, "%Y-%m-%d") - datetime.timedelta(days=6)
        fil  = open(homepath+"WeekOf_%s.txt" % date.strftime("%Y-%m-%d"), 'w')
        fil.write(sales[1])
        fil.close()

        email = {'subject':'Week of %s' % date.strftime("%Y-%m-%d"), 'body':sales[1]}
        email_report(report=email)

    ###########################
    ##########MONTHLY##########
    ###########################

    if int(datetime.datetime.today().strftime("%d")) == 25:
        google_api.build_month_sheet()

    if int((datetime.datetime.strptime(report_date, "%Y-%m-%d")+datetime.timedelta(days=1)).strftime("%d")) == 1:

        sales = monthly_sales(datetime.datetime.strptime(report_date, "%Y-%m-%d"))

        sdate = datetime.datetime.strptime(report_date, "%Y-%m-%d").replace(day=1)
        fil   = open(homepath+"MonthOf_%s.txt" % sdate.strftime("%Y-%m-%d"), 'w')
        fil.write(sales[1])
        fil.close()

        email = {'subject':'Month of %s'%sdate.strftime("%Y-%m"), 'body':sales[1]}
        email_report(report=email)
        
    if (datetime.datetime.strptime(report_date, "%Y-%m-%d")+datetime.timedelta(days=1)).strftime("%Y-%m-%d") == "2019-01-01":

        sales = yearly_sales(datetime.datetime.strptime(report_date, "%Y-%m-%d"))

        sdate = datetime.datetime.strptime(report_date, "%Y-%m-%d").replace(day=1)
        fil   = open(homepath+"YearOf_%s.txt" % sdate.strftime("%Y"), 'w')
        fil.write(sales[1])
        fil.close()

        email = {'subject':'Year of %s'%sdate.strftime("%Y"), 'body':sales[1]}
        email_report(report=email)

    try:
        get_month()

    except Exception as e:
        ts   = time.time()
        log += "[%s]: %s"%(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'), e)

    try:
        get_year()

    except Exception as e:
        ts   = time.time()
        log += "[%s]: %s" % (datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'), e)

    ###########################
    ########WRITE LOG##########
    ###########################

    with open (homepath + "log.txt", 'w') as fh:
        fh.write(log)
