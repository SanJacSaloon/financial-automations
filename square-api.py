#!/opt/sjs/bin/python

import httplib, urllib, json, locale
from urlparse import urlparse
import os,sys
import smtplib
import pickle
from datetime import *
from dateutil.relativedelta import *
import time
import google_sheets
import pymysql

testing = False


homepath ='/home/ec2-user/code/reports/'
args = sys.argv
report_date = (datetime.today()-timedelta(days=1)).strftime("%Y-%m-%d")
if len(args) > 1: report_date = args[1]
filename = "%s.txt"%report_date
fh = open(homepath+filename, 'w')
log = open(homepath+"log.txt", 'rb').read()

secrets = json.loads(open("secrets.json").read())
location_ids = secrets["square"]["location_ids"]

# Your application's personal access token.
# Get this from your application dashboard (https://connect.squareup.com/apps)
access_token = secrets["square"]["access_token"]

# Standard HTTP headers for every Connect API request
request_headers = {'Authorization': 'Bearer ' + access_token,
                   'Accept': 'application/json',
                   'Content-Type': 'application/json'}


# Uses the locale to format currency amounts correctly
locale.setlocale(locale.LC_ALL, '')

secrets  = json.loads(open("secrets.json").read())
sql_db   = secrets["sql"]["database"]
sql_user = secrets["sql"]["user"]
sql_pw   = secrets["sql"]["password"]

def get_row(table,date):
  try:
    result = database("SELECT * from %s where date like '%s'"%(table,date))[0]
    return result
  except: return False

def database(sql):# Connect to the database
  db = pymysql.connect(host='localhost',
                             user=sql_user,
                             password=sql_pw,
                             db=sql_db,
                             charset='utf8mb4',
                             autocommit=True,
                             cursorclass=pymysql.cursors.DictCursor)

  cur = db.cursor(pymysql.cursors.DictCursor)
  sql+=";"
  print sql
  cur.execute(sql)
  result = cur.fetchall()
  db.close()
  return result

def populate_database(date):
  if not date: date = "2018-05-01"
  try: date = datetime.strptime(date,"%Y-%m-%d")
  except: pass
  while date < datetime.today():
    sales = daily_sales(date)
    date = date + timedelta(days=1)

# Helper function to convert cent-based money amounts to dollars and cents
def format_money(amount):
  return locale.currency(amount / 100.)


# Obtains all of the business's location IDs. Each location has its own collection of payments.
def get_location_ids():
  global log
  # The base URL for every Connect API request
  connection = httplib.HTTPSConnection('connect.squareup.com')
  request_path = '/v1/me/locations'
  connection.request('GET', request_path, '', request_headers)
  response = connection.getresponse()

  # Transform the JSON array of locations into a Python list
  locations = json.loads(response.read())

  location_ids = []
  for location in locations:
    location_ids.append(location['id'])
  connection.close()
  return location_ids


def get_items():
  global log
  items = []
  # The base URL for every Connect API request
  connection = httplib.HTTPSConnection('connect.squareup.com')

  # For each location...
  for location_id in location_ids:

    #full_report += 'Downloading drawers for location with ID ' + location_id + '...'

    request_path = '/v1/' + location_id + '/items'
    more_results = True

    # ...as long as there are more drawers to download from the location...
    while more_results:

      # ...send a GET request to /v1/LOCATION_ID/payments
      connection.request('GET', request_path, '', request_headers)
      response = connection.getresponse()

      # Read the response body JSON into the cumulative list of results
      items = items + json.loads(response.read())

      # Check whether pagination information is included in a response header, indicating more results
      pagination_header = response.getheader('link', '')
      if "rel='next'" not in pagination_header:
        more_results = False
      else:

        # Extract the next batch URL from the header.
        #
        # Pagination headers have the following format:
        # <https://connect.squareup.com/v1/LOCATION_ID/cash-drawer-shifts?batch_token=BATCH_TOKEN>;rel='next'
        # This line extracts the URL from the angle brackets surrounding it.
        next_batch_url = urlparse(pagination_header.split('<')[1].split('>')[0])

        request_path = next_batch_url.path + '?' + next_batch_url.query

  # Remove potential duplicate values from the list of drawers
  seen_item_ids = set()
  unique_items = []
  for item in items:
    if item['id'] in seen_item_ids: continue
    seen_item_ids.add(item['id'])
    unique_items.append(item)

  connection.close()
  return unique_items

def update_variation(item_id,variation_id,variation_updates):
  global log
  connection = httplib.HTTPSConnection('connect.squareup.com')

  request_body = str(variation_updates)
  #for update in item_updates.keys():
   # request_body += '"%s":"%s"'%(
  #print request_body
  connection.request('PUT', '/v1/' + location_ids[0] + '/items/' + item_id + '/variations/' + variation_id, request_body, request_headers)
  response = connection.getresponse()
  response_body = json.loads(response.read())
  if response.status == 200:
    #print 'Successfully updated item:'
    #print json.dumps(response_body, sort_keys=True, indent=2, separators=(',', ': '))
    connection.close()
    return response_body
  else:
    print 'Item update failed'
    print json.dumps(response_body, sort_keys=True, indent=2, separators=(',', ': '))
    connection.close()
    return None


def update_item(item_id,item_updates):
  global log
  connection = httplib.HTTPSConnection('connect.squareup.com')
  #print 'Updating item ' + item_id
  request_body = str(item_updates)
  #for update in item_updates.keys():
   # request_body += '"%s":"%s"'%(update,item_updates[update])
  connection.request('PUT', '/v1/' + location_ids[0] + '/items/' + item_id, request_body, request_headers)
  response = connection.getresponse()
  response_body = json.loads(response.read())
  if response.status == 200:
    #print 'Successfully updated item:'
    #print json.dumps(response_body, sort_keys=True, indent=2, separators=(',', ': '))
    connection.close()
    return response_body
  else:
    print 'Item update failed'
    connection.close()
    return None

def get_cash_drawer(date=False):
  global log
  global full_report

  if not date:
    reportdate = datetime.today()-timedelta(days=1)
    end = datetime.today()
    end = end.strftime("%Y-%m-%dT04:00:00-06:00")
  else:
    reportdate = datetime.strptime(date,"%Y-%m-%d")
    end = (reportdate+timedelta(days=1)).strftime("%Y-%m-%dT04:00:00-06:00")
  begin = reportdate.strftime("%Y-%m-%dT08:00:00-06:00")


  parameters = urllib.urlencode({'begin_time': begin,
                                 'end_time'  : end})

  drawers = []
  # The base URL for every Connect API request
  connection = httplib.HTTPSConnection('connect.squareup.com')

  # For each location...
  for location_id in location_ids:

    #full_report += 'Downloading drawers for location with ID ' + location_id + '...'

    request_path = '/v1/' + location_id + '/cash-drawer-shifts?' + parameters
    more_results = True

    # ...as long as there are more drawers to download from the location...
    while more_results:

      # ...send a GET request to /v1/LOCATION_ID/payments
      connection.request('GET', request_path, '', request_headers)
      response = connection.getresponse()
      resp = eval(response.read())

      if "unauthorized" in resp:
        return ""
      # Read the response body JSON into the cumulative list of results
      for r in resp:
        drawers.append(r)

      # Check whether pagination information is included in a response header, indicating more results
      pagination_header = response.getheader('link', '')
      if "rel='next'" not in pagination_header:
        more_results = False
      else:

        # Extract the next batch URL from the header.
        #
        # Pagination headers have the following format:
        # <https://connect.squareup.com/v1/LOCATION_ID/cash-drawer-shifts?batch_token=BATCH_TOKEN>;rel='next'
        # This line extracts the URL from the angle brackets surrounding it.
        next_batch_url = urlparse(pagination_header.split('<')[1].split('>')[0])

        request_path = next_batch_url.path + '?' + next_batch_url.query

  # Remove potential duplicate values from the list of drawers
  seen_drawer_ids = set()
  unique_drawers = []

  for drawer in drawers:
    if drawer['id'] in seen_drawer_ids: continue

    if (datetime.strptime(drawer['opened_at'].replace("Z",''),"%Y-%m-%dT%H:%M:%S")-timedelta(hours=6)) < datetime.strptime(begin[:-6],"%Y-%m-%dT%H:%M:%S"): continue
    seen_drawer_ids.add(drawer['id'])
    unique_drawers.append(drawer)
  connection.close()
  return unique_drawers

# Downloads all of a business's payments
def get_payments(date=False,current=False):
  global log
  global full_report
  # Make sure to URL-encode all parameters
  if not date:
    reportdate = datetime.today()-timedelta(days=1)
    end = datetime.today()
    end = end.strftime("%Y-%m-%dT04:00:00-06:00")
  else:
    try:reportdate = datetime.strptime(date,"%Y-%m-%d")
    except: reportdate = date
    end = (reportdate+timedelta(days=1)).strftime("%Y-%m-%dT04:00:00-06:00")
  if current:
    if not date:
        if int(time.strftime("%H")) < 4:
            begin = (datetime.today()-timedelta(days=1)).strftime("%Y-%m-%dT08:00:00-06:00")
        else: begin = datetime.today().strftime("%Y-%m-%dT08:00:00-06:00")
    else:
        begin = date + "T08:00:00-06:00"
    parameters = urllib.urlencode({'begin_time': begin})
  else:
    begin = reportdate.strftime("%Y-%m-%dT08:00:00-06:00")

    parameters = urllib.urlencode({'begin_time': begin,
                                 'end_time'  : end})

  payments = []
  # The base URL for every Connect API request
  connection = httplib.HTTPSConnection('connect.squareup.com')

  # For each location...
  for location_id in location_ids:
    request_path = '/v1/' + location_id + '/payments?' + parameters
    more_results = True

    # ...as long as there are more payments to download from the location...
    while more_results:

      # ...send a GET request to /v1/LOCATION_ID/payments
      connection.request('GET', request_path, '', request_headers)
      response = connection.getresponse()

      # Read the response body JSON into the cumulative list of results
      payments = payments + json.loads(response.read())

      # Check whether pagination information is included in a response header, indicating more results
      pagination_header = response.getheader('link', '')
      if "rel='next'" not in pagination_header:
        more_results = False
      else:

        # Extract the next batch URL from the header.
        #
        # Pagination headers have the following format:
        # <https://connect.squareup.com/v1/LOCATION_ID/payments?batch_token=BATCH_TOKEN>;rel='next'
        # This line extracts the URL from the angle brackets surrounding it.
        next_batch_url = urlparse(pagination_header.split('<')[1].split('>')[0])

        request_path = next_batch_url.path + '?' + next_batch_url.query

  # Remove potential duplicate values from the list of payments
  seen_payment_ids = set()
  unique_payments = []

  for payment in payments:
    if payment['id'] in seen_payment_ids:
      continue
    seen_payment_ids.add(payment['id'])
    unique_payments.append(payment)
  connection.close()

  return unique_payments

def print_transactions_report(transactions):
  total = 0
  for transaction in transactions:
    for t in transaction['tenders']:
      total += int(t['amount_money']['amount'])

  return total

def get_transactions(date=False,current=False):
  global log
  global full_report

  count = 0

  # Make sure to URL-encode all parameters
  if not date:
    reportdate = datetime.today()-timedelta(days=1)
    end = datetime.today()
    end = end.strftime("%Y-%m-%dT04:00:00-06:00")
  else:
    try:reportdate = datetime.strptime(date,"%Y-%m-%d")
    except:reportdate = date
    end = (reportdate+timedelta(days=1)).strftime("%Y-%m-%dT04:00:00-06:00")
  if current:
    if not date:
        if int(time.strftime("%H")) < 4:
            begin = (datetime.today()-timedelta(days=1)).strftime("%Y-%m-%dT08:00:00-06:00")
            end = datetime.today()
            end = end.strftime("%Y-%m-%dT04:00:00-06:00")
        else:
            begin = datetime.today().strftime("%Y-%m-%dT08:00:00-06:00")
            end = datetime.today()
            end = end.strftime("%Y-%m-%dT23:59:59-06:00")
    else:
        begin = date + "T08:00:00-06:00"
    parameters = urllib.urlencode({'begin_time': begin})
  else:
    begin = reportdate.strftime("%Y-%m-%dT08:00:00-06:00")



  transactions = []

  # The base URL for every Connect API request
  connection = httplib.HTTPSConnection('connect.squareup.com')

  # For each location...
  for location_id in location_ids:
    more_results = True

    cursor = ''
    # ...as long as there are more payments to download from the location...
    while more_results:
      if cursor: parameters = urllib.urlencode({'begin_time': begin,
                                 'end_time'  : end,'cursor':cursor})
      else: parameters = urllib.urlencode({'begin_time': begin,
                                 'end_time'  : end})

      request_path = '/v2/locations/' + location_id + '/transactions?' + parameters
      # ...send a GET request to /v1/LOCATION_ID/payments
      connection.request('GET', request_path, '', request_headers)
      response = connection.getresponse()

      data = response.read()

      try:output = json.loads(data)['transactions']
      except:break

      # Read the response body JSON into the cumulative list of results
      transactions = transactions + output
      if 'cursor' in json.loads(data).keys():
        if json.loads(data)['cursor']:
            cursor = json.loads(data)['cursor']
      else:
        more_results = False

      #if 'cursor' in data.keys():
      #  cursor = ['cursor']
      #  if not cursor: more_results = False


      '''else:

        # Extract the next batch URL from the header.
        #
        # Pagination headers have the following format:
        # <https://connect.squareup.com/v1/LOCATION_ID/payments?batch_token=BATCH_TOKEN>;rel='next'
        # This line extracts the URL from the angle brackets surrounding it.
        next_batch_url = urlparse(pagination_header.split('<')[1].split('>')[0])
        request_path = next_batch_url.path + '?' + next_batch_url.query'''

  # Remove potential duplicate values from the list of payments
  seen_transaction_ids = set()
  unique_transactions = []

  for transaction in transactions:
    if transaction['id'] in seen_transaction_ids:
      continue
    seen_transaction_ids.add(transaction['id'])
    unique_transactions.append(transaction)

  connection.close()
  fh = open(homepath+"transactions.txt",'w')
  fh.write(str(unique_transactions))
  fh.close()

  return unique_transactions


# Prints a sales report based on a list of payments
def sales_totals(payments,drawers,reportd):
  global log
  global full_report
  total = {}
  categories = []

  if not reportd:reportd = datetime.strptime(report_date,"%Y-%m-%d")
   # Variables for holding cumulative values of various monetary amounts
  total['sjs_tips'] = 0
  total['jacks_tips'] = 0
  total['sjs_refunds'] = 0
  total['jacks_refunds'] = 0
  total['sjs_beer'] = 0
  total['jacks_beer'] = 0
  total['sjs_liquor'] = 0
  total['jacks_liquor'] = 0
  total['sjs_retail'] = 0
  total['jacks_retail'] = 0
  total['sjs_alcohol'] = 0
  total['jacks_alcohol'] = 0
  total['sjs_nonalc'] = 0
  total['jacks_nonalc'] = 0
  total['sjs_dcounts'] = 0
  total['jacks_dcounts'] = 0
  total['sjs_total'] = 0
  total['jacks_total'] = 0
  total['sjs_credit'] = 0
  total['jacks_credit'] = 0
  total['sjs_wine'] = 0
  total['jacks_wine'] = 0
  total['sjs_service'] = 0
  total['jacks_service'] = 0
  total['sjs_tip_credit'] = 0
  total['jacks_tip_credit'] = 0
  total['sjs_paidout'] = 0
  total['jacks_paidout'] = 0
  total['sjs_cash'] = 0
  total['jacks_cash'] = 0
  total['unknown'] = 0
  # Add appropriate values to each cumulative variable
  for payment in payments:
    if 'device' not in payment.keys():

        if not payment['refunds']:
            for i in xrange(len(payment['itemizations'])):
                category = payment['itemizations'][i]['item_detail']['category_name']
                amount = 0
                amount += payment['itemizations'][i]['single_quantity_money']['amount']*int(float(payment['itemizations'][i]['quantity']))
        total['unknown'] += amount
    elif 'name' not in payment['device'].keys():
        if not payment['refunds']:
            for i in xrange(len(payment['itemizations'])):
                category = payment['itemizations'][i]['item_detail']['category_name']
                amount = 0
                amount += payment['itemizations'][i]['single_quantity_money']['amount']*int(float(payment['itemizations'][i]['quantity']))
        total['unknown'] += amount
    elif 'sanjac' in payment['device']['name'].lower():
      if not payment['refunds']:
        for i in xrange(len(payment['itemizations'])):
          category = payment['itemizations'][i]['item_detail']['category_name']
          amount = 0
          amount += payment['itemizations'][i]['single_quantity_money']['amount']*int(float(payment['itemizations'][i]['quantity']))

          for d in xrange(len(payment['itemizations'][i]['discounts'])):
              amount += payment['itemizations'][i]['discounts'][d]['applied_money']['amount']
              total['sjs_dcounts'] += payment['itemizations'][i]['discounts'][d]['applied_money']['amount']
          if category not in categories: categories.append(category)
          if 'beer' in category.lower():
              total['sjs_total']       = total['sjs_total']           + amount
              total['sjs_beer']        = total['sjs_beer']            + amount
              total['sjs_alcohol']     = total['sjs_alcohol']         + amount
          elif 'retail' in category.lower():
              total['sjs_total']       = total['sjs_total']           + amount
              total['sjs_retail']      = total['sjs_retail']          + amount
          elif 'non/alc' in category.lower():
              total['sjs_total']       = total['sjs_total']           + amount
              total['sjs_nonalc']      = total['sjs_nonalc']          + amount
          elif 'wine' in category.lower():
              total['sjs_total']       = total['sjs_total']           + amount
              total['sjs_wine']        = total['sjs_wine']            + amount
          elif 'room' in category.lower():
              total['sjs_total']       = total['sjs_total']           + amount
              total['sjs_service']     = total['sjs_service']         + amount
          else:
              total['sjs_total']       = total['sjs_total']           + amount
              total['sjs_liquor']      = total['sjs_liquor']          + amount
              total['sjs_alcohol']     = total['sjs_alcohol']         + amount
      total['sjs_refunds']             = total['sjs_refunds']         + payment['refunded_money']['amount']
      total['sjs_tips']                = total['sjs_tips']            + payment['tip_money']['amount']
      for p in xrange(len(payment['tender'])):
          if 'credit' in str(payment['tender'][p]['type']).lower():
              total['sjs_credit'] += payment['tender'][p]['total_money']['amount']-payment['tender'][p]['refunded_money']['amount']
              total['sjs_tip_credit'] += payment['tip_money']['amount']
          if 'cash' in str(payment['tender'][p]['type']).lower():
              total['sjs_cash'] += payment['tender'][p]['total_money']['amount']-payment['tender'][p]['refunded_money']['amount']

    else:
      if not payment['refunds']:
        for i in xrange(len(payment['itemizations'])):
          category = payment['itemizations'][i]['item_detail']['category_name']
          amount = 0
          amount += payment['itemizations'][i]['single_quantity_money']['amount']*int(float(payment['itemizations'][i]['quantity']))

          for d in xrange(len(payment['itemizations'][i]['discounts'])):
              amount += payment['itemizations'][i]['discounts'][d]['applied_money']['amount']
              total['jacks_dcounts'] += payment['itemizations'][i]['discounts'][d]['applied_money']['amount']
          if category not in categories: categories.append(category)
          if 'beer' in category.lower():
              total['jacks_total']       = total['jacks_total']           + amount
              total['jacks_beer']        = total['jacks_beer']            + amount
              total['jacks_alcohol']     = total['jacks_alcohol']         + amount
          elif 'retail' in category.lower():
              total['jacks_total']       = total['jacks_total']           + amount
              total['jacks_retail']      = total['jacks_retail']          + amount
          elif 'non/alc' in category.lower():
              total['jacks_total']       = total['jacks_total']           + amount
              total['jacks_nonalc']      = total['jacks_nonalc']          + amount
          elif 'wine' in category.lower():
              total['jacks_total']       = total['jacks_total']           + amount
              total['jacks_wine']        = total['jacks_wine']            + amount
          elif 'room' in category.lower():
              total['jacks_total']       = total['jacks_total']           + amount
              total['jacks_service']     = total['jacks_service']         + amount
          else:
              total['jacks_total']       = total['jacks_total']           + amount
              total['jacks_liquor']      = total['jacks_liquor']          + amount
              total['jacks_alcohol']     = total['jacks_alcohol']         + amount
      total['jacks_refunds']             = total['jacks_refunds']         + payment['refunded_money']['amount']
      total['jacks_tips']                = total['jacks_tips']            + payment['tip_money']['amount']
      for p in xrange(len(payment['tender'])):
        if 'credit' in str(payment['tender'][p]['type']).lower():
            total['jacks_credit'] += payment['tender'][p]['total_money']['amount']-payment['tender'][p]['refunded_money']['amount']
            total['jacks_tip_credit'] += payment['tip_money']['amount']
        if 'cash' in str(payment['tender'][p]['type']).lower():

            total['jacks_cash'] += payment['tender'][p]['total_money']['amount']-payment['tender'][p]['refunded_money']['amount']

  for drawer in drawers:
    if 'name' not in drawer['device'].keys(): continue
    if 'sanjac' in drawer['device']['name'].lower():
      total['sjs_paidout'] += drawer['cash_paid_out_money']['amount']
      total['sjs_cash'] += drawer['cash_paid_in_money']['amount']

    else:
      total['jacks_paidout'] += drawer['cash_paid_out_money']['amount']
      total['jacks_cash'] += drawer['cash_paid_in_money']['amount']

  return total

def fill_db(reportd,total,timeframe):
  if 'day' in timeframe:
    daily=get_row("daily",reportd)
    update = False
    if daily:
      d = Daily(daily['id'])
      update = True
      print "Found Row"
    else: d = Daily()
  elif 'week' in timeframe:
    weekly=get_row("weekly",reportd)
    update = False
    if weekly:
      d = Weekly(weekly['id'])
      update = True
      print "Found Row"
    else: d = weekly()
  elif 'month' in timeframe:
    monthly=get_row("monthly",reportd)
    update = False
    if monthly:
      d = Monthly(monthly['id'])
      update = True
      print "Found Row"
    else: d = Monthly()
  elif 'year' in timeframe:
    yearly=get_row("yearly",reportd)
    update = False
    if yearly:
      d = Yearly(yearly['id'])
      update = True
      print "Found Row"
    else: d = Yearly()

  d['date'] = str(reportd)
  d['sjs_liquor'] = total['sjs_liquor']
  d['sjs_beer'] = total['sjs_beer']
  d['sjs_wine'] = total['sjs_wine']
  d['sjs_redbull'] = 0
  d['sjs_nonalc'] = total['sjs_nonalc']
  d['sjs_service'] = total['sjs_service']
  d['sjs_retail'] = total['sjs_retail']
  d['sjs_total'] = total['sjs_total']
  d['sjs_credit'] = total['sjs_credit']
  d['sjs_tips'] = total['sjs_tips']
  d['sjs_refunds'] = total['sjs_refunds']
  d['sjs_alcohol'] = total['sjs_alcohol']
  d['sjs_dcounts'] = total['sjs_dcounts']
  d['sjs_paidout'] = total['sjs_paidout']
  d['sjs_cash'] = total['sjs_cash']
  d['jacks_liquor'] = total['jacks_liquor']
  d['jacks_beer'] = total['jacks_beer']
  d['jacks_wine'] = total['jacks_wine']
  d['jacks_redbull'] = 0
  d['jacks_nonalc'] = total['jacks_nonalc']
  d['jacks_service'] = total['jacks_service']
  d['jacks_retail'] = total['jacks_retail']
  d['jacks_total'] = total['jacks_total']
  d['jacks_credit'] = total['jacks_credit']
  d['jacks_tips'] = total['jacks_tips']
  d['jacks_refunds'] = total['jacks_refunds']
  d['jacks_alcohol'] = total['jacks_alcohol']
  d['jacks_dcounts'] = total['jacks_dcounts']
  d['jacks_paidout'] = total['jacks_paidout']
  d['jacks_cash'] = total['jacks_cash']
  d['jacks_tip_credit'] = total['jacks_tip_credit']
  d['sjs_tip_credit'] = total['sjs_tip_credit']
  d['unknown'] = total['unknown']

  if update:
    d.update()
  else:
    d.insert()
  return d

def daily_sales(date):
  global log
  full_report = '==%s SALES REPORT==\n'%date.strftime("%a, %b %-d %Y")

  payments = get_payments(date)
  transactions = get_transactions(date)
  try:drawers = get_cash_drawer(date)
  except Exception as e:
    drawers = []
    ts = time.time()
    log+= "[%s]: %s"%(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),e)
  try:reportdate = datetime.strptime(date,"%Y-%m-%d")
  except:reportdate = date
  sales = sales_totals(payments,drawers,reportdate)

  full_report += report_string(sales)

  ####LAST YEAR####
  last_year_report_date = reportdate+relativedelta(years=-1, weekday=reportdate.weekday())
  last_year_payments = get_payments(last_year_report_date.strftime("%Y-%m-%d"))
  try:last_year_drawers = get_cash_drawer(last_year_report_date.strftime("%Y-%m-%d"))
  except Exception as e:
    last_year_drawers = []
    ts = time.time()
    log+= "[%s]: %s"%(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),e)

  full_report += '\n'
  full_report += '===LAST YEAR===\n'
  full_report += '==%s SALES REPORT==\n'%last_year_report_date.strftime("%a, %b %-d %Y")

  last_year_sales = sales_totals(last_year_payments,last_year_drawers,last_year_report_date)
  full_report += report_string(last_year_sales)

  reportd = reportdate.strftime("%Y-%m-%d")
  fill_db(reportd,sales,"day")

  return (sales,full_report)

def weekly_sales(date,report=False,recursive=False):
  global log
  if not date:date = datetime.today()
  original_date = date
  date = date - timedelta(days=7)
  day = 0
  weekly_total = {}
  names = []
  full_report = ''
  while day < 7:
    if (date+timedelta(days=day)).strftime("%Y-%m-%d") >= date.today().strftime("%Y-%m-%d"):
      day+=1
      continue
    money = get_row('daily',(date+timedelta(days=day)).strftime("%Y-%m-%d"))

    for item in money:
      if item in weekly_total.keys():
        try:weekly_total[item]+=money[item]
        except:weekly_total[item]=money[item]
      else: weekly_total[item] = money[item]
    day+= 1

  if not recursive:
    #Create the report
    full_report = '==WEEKLY SALES REPORT==\n'
    full_report += report_string(weekly_total)

    #Fill DB
    fill_db(date.strftime("%Y-%m-%d"),weekly_total,"week")

    ####LAST YEAR####
    full_report += '==LAST YEAR WEEKLY SALES REPORT==\n'
    last_year_report_date = original_date+relativedelta(years=-1, weekday=original_date.weekday())
    full_report += weekly_sales(last_year_report_date,recursive=True)
  else: return (weekly_total,report_string(weekly_total))
  return (weekly_total,full_report)

def monthly_sales(date,recursive=False):
  global log
  if not date: date = datetime.today() - timedelta(days=1)
  date = date.replace(day=1)
  month = int(date.strftime("%m"))
  sdate = date
  day = 0
  monthly_total = {}

  while int((date+timedelta(days=day)).strftime("%m")) == month:
    if (date+timedelta(days=day)).strftime("%Y-%m-%d") >= date.today().strftime("%Y-%m-%d"):
      day+=1
      continue
    money = get_row('daily',(date+timedelta(days=day)).strftime("%Y-%m-%d"))

    for item in money:
      if item in monthly_total.keys():
        try:monthly_total[item]+=money[item]
        except:monthly_total[item]=money[item]
      else: monthly_total[item] = money[item]
    day+= 1

  if not recursive:
    #Create the report
    full_report = '==MONTHLY SALES REPORT==\n'
    full_report += report_string(monthly_total)

    #Fill DB
    fill_db(date.strftime("%Y-%m-%d"),monthly_total,"month")

    ####LAST YEAR####
    full_report += '==LAST YEAR MONTHLY SALES REPORT==\n'
    last_year_report_date = sdate+relativedelta(years=-1)
    full_report += monthly_sales(last_year_report_date,recursive=True)
  else: return report_string(monthly_total)
  return (monthly_total,full_report)

def yearly_sales(date,recursive=False):
  global log
  if not date: date = datetime.today()
  date = date.replace(day=1)
  date = date.replace(month=1)

  sdate = date
  month = 0
  yearly_total = {}

  while int(date.strftime("%m")) < datetime.today().strftime("%m"):
    if date.strftime("%Y-%m-%d") > date.today().strftime("%Y-%m-%d"):
      break
    money = get_row('monthly',date.strftime("%Y-%m-%d"))
    if not money:
      tmp = populate_database(date)
      money = get_row('monthly',date.strftime("%Y-%m-%d"))
    for item in money:
      if item in yearly_total.keys():
        try:yearly_total[item]+=money[item]
        except:yearly_total[item]=money[item]
      else: yearly_total[item] = money[item]
    date = date + timedelta(days=31)
    date = date.replace(day=1)


  if not recursive:
    #Create the report
    full_report = '==MONTHLY SALES REPORT==\n'
    full_report += report_string(yearly_total)

    #Fill DB
    fill_db(sdate.strftime("%Y-%m-%d"),yearly_total,"yearly")

    ####LAST YEAR####
    full_report += '==LAST YEAR MONTHLY SALES REPORT==\n'
    last_year_report_date = sdate+relativedelta(years=-1)
    full_report += monthly_sales(last_year_report_date,recursive=True)
  else: return report_string(yearly_total)
  return (yearly_total,full_report)

def get_month():
  global log
  date = datetime.today()
  sdate = date
  date = date.replace(day=1)
  month_total = monthly_sales(date)[0]

  full_report = "MTD SALES:\n"
  full_report += 'San Jac:           ' + format_money(month_total['sjs_total'])+'\n'
  full_report += "Jack's:            " + format_money(month_total['jacks_total'])+'\n'
  full_report += 'Total:             ' + format_money(month_total['jacks_total']+month_total['sjs_total'])+'\n'
  pickle.dump( full_report, open( "month.p", "wb" ) )
  return full_report

def get_year(custom_date=False):
  global log
  if not custom_date: date = datetime.today()
  else: date = custom_date
  sdate = date
  date = date.replace(day=1)
  date = date.replace(month=1)
  year_total = yearly_sales(date)[0]

  full_report = "YTD SALES:\n"
  full_report += 'San Jac:           ' + format_money(year_total['sjs_total'])+'\n'
  full_report += "Jack's:            " + format_money(year_total['jacks_total'])+'\n'
  full_report += 'Total:             ' + format_money(year_total['jacks_total']+year_total['sjs_total'])+'\n'
  if custom_date: return year_total
  pickle.dump( full_report, open( "year.p", "wb" ) )
  return full_report

def report_string(total):
  return_string = ''
  return_string += '     =San Jac=\n'
  return_string += 'Total:             ' + format_money(total['sjs_total'])+'\n'
  return_string += 'Total Alcohol:     ' + format_money(total['sjs_alcohol'])+'\n'
  return_string += 'Total Non-Alcohol: ' + format_money(total['sjs_retail']+total['sjs_nonalc'])+'\n'
  return_string += 'Total Taxes:       ' + format_money((total['sjs_alcohol']*.027)+(total['sjs_total']*.0825))+'\n'
  return_string += '\n'
  return_string += 'Liquor:            ' + format_money(total['sjs_liquor'])+'\n'
  return_string += 'Beer:              ' + format_money(total['sjs_beer'])+'\n'
  return_string += 'Wine:              ' + format_money(total['sjs_wine'])+'\n'
  return_string += 'Non-Alcohol:       ' + format_money(total['sjs_nonalc'])+'\n'
  return_string += 'Service/Room:      ' + format_money(total['sjs_service'])+'\n'
  return_string += 'Merch:             ' + format_money(total['sjs_retail'])+'\n'
  return_string += 'Total Credit:      ' + format_money(total['sjs_credit'])+'\n'
  return_string += 'Processing Fees:   ' + format_money(total['sjs_credit']*.025)+'\n'
  return_string += '\n'
  return_string += 'Refunds:           ' + format_money(total['sjs_refunds'])+'\n'
  return_string += 'Discounts:         ' + format_money(total['sjs_dcounts'])+'\n'
  return_string += '\n'
  return_string += 'Cash In:           ' + format_money(total['sjs_cash'])+'\n'
  return_string += 'Paid Out:          ' + format_money(total['sjs_paidout'])+'\n'
  return_string += 'Tip Out:           ' + format_money(0-total['sjs_tip_credit'])+'\n'
  return_string += 'Tip Processing:    ' + format_money(total['sjs_tip_credit']*.025)+'\n'
  return_string += 'Net cash           ' + format_money(total['sjs_cash']+(total['sjs_paidout']+total['sjs_tip_credit'])+total['sjs_tip_credit']*.025)+'\n'
  return_string += '\n'
  return_string += "     =Jack's=\n"
  return_string += 'Total:             ' + format_money(total['jacks_total'])+'\n'
  return_string += 'Total Alcohol:     ' + format_money(total['jacks_alcohol'])+'\n'
  return_string += 'Total Non-Alcohol: ' + format_money(total['jacks_retail']+total['jacks_nonalc'])+'\n'
  return_string += 'Total Taxes:       ' + format_money((total['jacks_alcohol']*.027)+(total['jacks_total']*.0825))+'\n'
  return_string += '\n'
  return_string += 'Liquor:            ' + format_money(total['jacks_liquor'])+'\n'
  return_string += 'Beer:              ' + format_money(total['jacks_beer'])+'\n'
  return_string += 'Wine:              ' + format_money(total['jacks_wine'])+'\n'
  return_string += 'Non-Alcohol:       ' + format_money(total['jacks_nonalc'])+'\n'
  return_string += 'Service/Room:      ' + format_money(total['jacks_service'])+'\n'
  return_string += 'Merch:             ' + format_money(total['jacks_retail'])+'\n'
  return_string += 'Total Credit:      ' + format_money(total['jacks_credit'])+'\n'
  return_string += 'Processing Fees:   ' + format_money(total['jacks_credit']*.025)+'\n'
  return_string += '\n'
  return_string += 'Refunds:           ' + format_money(total['jacks_refunds'])+'\n'
  return_string += 'Discounts:         ' + format_money(total['jacks_dcounts'])+'\n'
  return_string += '\n'
  return_string += 'Cash In:           ' + format_money(total['jacks_cash'])+'\n'
  return_string += 'Paid Out:          ' + format_money(total['jacks_paidout'])+'\n'
  return_string += 'Tip Out:           ' + format_money(0-total['jacks_tip_credit'])+'\n'
  return_string += 'Tip Processing:    ' + format_money(total['jacks_tip_credit']*.025)+'\n'
  return_string += 'Net cash:          ' + format_money(total['jacks_cash']+(total['jacks_paidout']-total['jacks_tip_credit'])+total['jacks_tip_credit']*.025)+'\n'
  return_string += 'Unknown Device:    ' + format_money(total['unknown'])+'\n'
  return_string += '\n'
  return return_string

def transactions(date = False,current=False):
  if current: transactions = get_transactions(current=True)
  if not date: transactions = get_transactions(report_date)
  else: transactions = get_transactions(date)
  total = 0
  fh = open(homepath+'trans_amounts.txt','w')
  for t in transactions:
    if t['tenders'][0]['type'] == 'CARD':
      amount = int(t['tenders'][0]['amount_money']['amount'])
      fh.write("%s\n"%amount)
      total += amount
  fh.close()

def email_report(email='howdy@sanjacsaloon.com',report=False):
  global log
  if testing: email = 'logan@sanjacsaloon.com'

  fromaddr = 'sanjacsaloon@gmail.com'
  toaddrs  = email
  if not report:
    msg = "\r\n".join([
    "From: %s"%fromaddr,
    "To: %s"%toaddrs,
    "Subject: Report for %s"%report_date,"",full_report])
  else:
    msg = "\r\n".join([
    "From: %s"%fromaddr,
    "To: %s"%toaddrs,
    "Subject: %s"%(report['subject']),"",report['body']])
  username = 'sanjacsaloon@gmail.com'
  password = '9gYp3MSHxQlG'
  try:
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username,password)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()
  except: log+= '\n%s: Failed to send report'%datetime.today().strftime("%Y-%m-%d:%H:%M")

class Daily(dict):
    def __init__(self,day_id=False):
        if day_id:
            self['id'] = day_id
            if self['id']:
                result = database("SELECT * FROM daily WHERE id = %s"%int(self['id']))[0]
                for k in result:
                    self[k] = result[k]
                date_format = "%Y-%m-%d"
                #self['date'] = self['date'].strftime(date_format)

    def insert(self):
        keys = str(self.keys())
        keys = keys.replace('[','(')
        keys = keys.replace(']',')')
        keys = keys.replace("'","")
        values = str(self.values())
        values = values.replace('[','(')
        values = values.replace(']',')')
        i = database("INSERT INTO daily %s VALUES %s"%(keys,values))
        print i

    def update(self):
        values = ""
        for key in self.keys():
          values += "%s='%s',"%(key,self[key])
        values = values[:-1]
        u = database("UPDATE daily set %s WHERE id=%s"%(values,self['id']))

class Weekly(dict):
    def __init__(self,week_id=False):
        if week_id:
            self['id'] = week_id
            if self['id']:
                result = database("SELECT * FROM weekly WHERE id = %s"%int(self['id']))[0]
                for k in result:
                    self[k] = result[k]
                date_format = "%Y-%m-%d"
                #self['date'] = self['date'].strftime(date_format)

    def insert(self):
        keys = str(self.keys())
        keys = keys.replace('[','(')
        keys = keys.replace(']',')')
        keys = keys.replace("'","")
        values = str(self.values())
        values = values.replace('[','(')
        values = values.replace(']',')')
        i = database("INSERT INTO weekly %s VALUES %s"%(keys,values))

    def update(self):
        values = ""
        for key in self.keys():
          values += "%s='%s',"%(key,self[key])
        values = values[:-1]
        u = database("UPDATE weekly set %s WHERE id=%s"%(values,self['id']))

class Monthly(dict):
    def __init__(self,month_id=False):
        if month_id:
            self['id'] = month_id
            if self['id']:
                result = database("SELECT * FROM monthly WHERE id = %s"%int(self['id']))[0]
                for k in result:
                    self[k] = result[k]
                date_format = "%Y-%m-%d"
                #self['date'] = self['date'].strftime(date_format)

    def insert(self):
        keys = str(self.keys())
        keys = keys.replace('[','(')
        keys = keys.replace(']',')')
        keys = keys.replace("'","")
        values = str(self.values())
        values = values.replace('[','(')
        values = values.replace(']',')')
        i = database("INSERT INTO monthly %s VALUES %s"%(keys,values))

    def update(self):
        values = ""
        for key in self.keys():
          values += "%s='%s',"%(key,self[key])
        values = values[:-1]
        u = database("UPDATE monthly set %s WHERE id=%s"%(values,self['id']))

class Yearly(dict):
    def __init__(self,yearly_id=False):
        if yearly_id:
            self['id'] = yearly_id
            if self['id']:
                result = database("SELECT * FROM yearly WHERE id = %s"%int(self['id']))[0]
                for k in result:
                    self[k] = result[k]
                date_format = "%Y-%m-%d"
                #self['date'] = self['date'].strftime(date_format)

    def insert(self):
        keys = str(self.keys())
        keys = keys.replace('[','(')
        keys = keys.replace(']',')')
        keys = keys.replace("'","")
        values = str(self.values())
        values = values.replace('[','(')
        values = values.replace(']',')')
        i = database("INSERT INTO yearly %s VALUES %s"%(keys,values))

    def update(self):
        values = ""
        for key in self.keys():
          values += "%s='%s',"%(key,self[key])
        values = values[:-1]
        u = database("UPDATE yearly set %s WHERE id=%s"%(values,self['id']))

if __name__ == '__main__':
  ###########################
  ###########DAILY###########
  ###########################
  populate_database("2017-01-01")
  sales = daily_sales(datetime.strptime(report_date,"%Y-%m-%d"))
  google_sheets.fill_sales(datetime.strptime(report_date,"%Y-%m-%d"),sales[0])
  ##NOTIFY/WRITE#####################
  fh.write(sales[1])
  email_report(report={'subject':'Report for %s'%report_date,'body':sales[1]})

  ###########################
  ###########WEEKLY##########
  ###########################
  if 'sun' in datetime.today().strftime("%a").lower():
    try:sales = weekly_sales(datetime.strptime(report_date,"%Y-%m-%d"))
    except Exception as e:
      last_year_drawers = []
      ts = time.time()
      log+= "[%s]: %s"%(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),e)
    date = report_date - timedelta(days=7)
    fil = open(homepath+"WeekOf_%s.txt"%date.strftime("%Y-%m-%d"),'w')
    fil.write(sales[1])
    fil.close()

    email = {'subject':'Week of %s'%date.strftime("%Y-%m-%d"),'body':sales[1]}
    email_report(report=email)
  ###########################
  ##########MONTHLY##########
  ###########################
  if int(datetime.today().strftime("%d")) == 25:
    google_sheets.build_month_sheet()
  if int(datetime.today().strftime("%d")) == 1:
    try:sales = monthly_sales(datetime.strptime(report_date,"%Y-%m-%d"))
    except Exception as e:
      last_year_drawers = []
      ts = time.time()
      log+= "[%s]: %s"%(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),e)
    sdate = (datetime.today() - timedelta(days=1)).replace(day=1)
    fil = open(homepath+"MonthOf_%s.txt"%sdate.strftime("%Y-%m-%d"),'w')
    fil.write(sales[1])
    fil.close()

    email = {'subject':'Month of %s'%sdate.strftime("%Y-%m-%d"),'body':sales[1]}
    email_report(report=email)

  #############
  try: print get_month()
  except Exception as e:
    ts = time.time()
    log+= "[%s]: %s"%(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),e)

  try: print get_year()
  except Exception as e:
    ts = time.time()
    log+= "[%s]: %s"%(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),e)
  ###########################
  ########WRITE LOG##########
  ###########################
  lf = open(homepath+"log.txt",'w')
  lf.write(log)
  lf.close()
  fh.close()