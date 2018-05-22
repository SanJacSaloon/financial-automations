#!/opt/sjs/bin/python

from flask       import Flask, Response, request
from twilio      import twiml
from twilio.rest import TwilioRestClient
from datetime    import datetime,timedelta

import locale
import pickle
import json
import os

# instantiate our flask app.
app = Flask(__name__)

# batteries not included.
import square_api

# load secrets.
secrets     = json.loads(open("secrets.json").read())
account_sid = secrets["twilio"]["account_sid"]
auth_token  = secrets["twilio"]["auth_token"]

@app.route("/")
def check_app():
    # returns a simple string stating the app is working
    return Response("It works!"), 200

# Uses the locale to format currency amounts correctly
locale.setlocale( locale.LC_ALL, 'en_CA.UTF-8' )

def send_sms(message,to):
    client = TwilioRestClient(account_sid, auth_token)

    client.messages.create(from_=secrets["twilio"]["phone_number"],
                       to=to,
                       body=message)
   #return twiml.Sms(str(message),to=to,sender="+17372040418", mimetype="application/xml")

# Helper function to convert cent-based money amounts to dollars and cents
def format_money(amount):
  return locale.currency(amount / 100.)



def get_sales():

    try:
        payments = square_api.get_payments(current=True)
    except Exception as e:
        return "Square is fucking up. Try again: %s" % str(e)

    try:
        drawers = square_api.get_cash_drawer()
    except:
        drawers = []

    sales = square_api.sales_totals(payments,drawers,'')

    full_report  = "SALES:\n"
    full_report += 'San Jac:           ' + format_money(sales['sjs_total'])+'\n'
    full_report += "Jack's:            " + format_money(sales['jacks_total'])+'\n'
    full_report += 'Total:             ' + format_money(sales['jacks_total']+sales['sjs_total'])+'\n'
    total_tips   = int(sales['jacks_tips'])+int(sales['sjs_tips'])

    try:
        transactions = square_api.print_transactions_report(square_api.get_transactions(current=True))
    except:
        transactions = int(-111)

    full_report += "Total Transactions:\n" + format_money(transactions-total_tips)+'\n'

    return full_report

def get_week():
        weekdays = {"Sun":0,
                    "Mon":1,
                    "Tue":2,
                    "Wed":3,
                    "Thu":4,
                    "Fri":5,
                    "Sat":6}
        date = (datetime.today()-timedelta(days=weekdays[datetime.today().strftime("%a")])).strftime("%Y-%m-%d")

        try: payments = square_api.get_payments(date=date,current=True)
        except: return "Square is fucking up. Try again"

        try:drawers = square_api.get_cash_drawer()
        except:drawers = []
        sales = square_api.sales_totals(payments,drawers,'')
        full_report = "WTD SALES:\n"
        full_report += 'San Jac:           ' + format_money(sales['sjs_total'])+'\n'
        full_report += "Jack's:            " + format_money(sales['jacks_total'])+'\n'
        full_report += 'Total:             ' + format_money(sales['jacks_total']+sales['sjs_total'])+'\n'
        return full_report

def return_month():
        full_report = pickle.load( open( "month.p", "rb" ) )
        return full_report

def return_year():
        full_report = pickle.load( open( "year.p", "rb" ) )
        return full_report

@app.route("/twilio", methods=["POST"])
def inbound_sms():
    response = twiml.Response()
    # we get the SMS message from the request. we could also get the
    # "To" and the "From" phone number as well
    inbound_message = request.form.get("Body")
    number = request.form.get("From")

    # we can now use the incoming message text in our Python application
    if 'sales' in inbound_message.lower():
        send_sms(get_sales(),number)
    elif 'wtd' in inbound_message.lower():
        response.message(get_week())
    elif 'mtd' in inbound_message.lower():
        response.message(return_month())
    elif 'ytd' in inbound_message.lower():
        response.message(return_year())
    elif 'increase' in inbound_message.lower():
        send_sms("Increasing prices by $1...",number)
        square_api.update_item_price(100)
        send_sms("Done Processing",number)
    elif 'decrease' in inbound_message.lower():
        send_sms("Decreasing prices by $1...",number)
        square_api.update_item_price(-100)
        send_sms("Done Processing",number)
    elif 'restore' in inbound_message.lower():
        send_sms("Restoring default prices...",number)
        square_api.restore_item_price("regular")
        send_sms("Done Processing",number)
    elif 'report' in inbound_message.lower():
        send_sms("Processing report...",number)
        os.system("/opt/sjs/financial-automations/square_api.py")
        send_sms("Done Processing",number)
    else:
        response.message("Hi! All I understand for now is: \n'sales':Current Sales\n'wtd':Week to date sales\n'mtd':Month to date sales\n'ytd': Year to date sales\n'increase':Increase prices by $1\n'decrease':Decrease prices by $1\n'restore':Restore default prices\n'report':Generate the sales report")
    return Response(str(response), mimetype="application/xml"), 200


if __name__ == "__main__":
    app.run(debug=False)
