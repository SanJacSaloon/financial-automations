#!/opt/sjs/bin/python

"""
This script is standalone and binds to port 5000, currently being supervised under a shared screen session.

$ ./twilio_bot.py
 * Serving Flask app "twilio_bot" (lazy loading)
 * Environment: production
   WARNING: Do not use the development server in a production environment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)

We then use ngrok to map the Twilio hook back to the server.

TODO:
    - move to supervisor.
    - drop ngrok in place of ELB.
    - drop this pickle business.
"""

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
secrets     = json.loads(open("/opt/sjs/secrets.json").read())
account_sid = secrets["twilio"]["account_sid"]
auth_token  = secrets["twilio"]["auth_token"]

# Uses the locale to format currency amounts correctly.
# NOTE: this took a touch of trial and error.
locale.setlocale(locale.LC_ALL, "en_CA.UTF-8")

########################################################################################################################
##### HELPER ROUTINES
########################################################################################################################

def send_sms (message, to):
    global secrets
    client = TwilioRestClient(account_sid, auth_token)
    client.messages.create(from_=secrets["twilio"]["phone_number"], to=to, body=message)


def format_money (amount):
  return locale.currency(amount / 100.0)


def get_sales ():
    try:
        payments = square_api.get_payments(current=True)
    except Exception as e:
        return "square_api.get_payments(): %s" % str(e)

    try:
        drawers = square_api.get_cash_drawer()
    except:
        drawers = []

    # pull sales totals.
    sales = square_api.sales_totals(payments, drawers, "")

    # create a sales report for each floor and combined.
    full_report  = "SALES:\n"
    full_report += "San Jac:           " + format_money(sales["sjs_total"])   + "\n"
    full_report += "Jack's:            " + format_money(sales["jacks_total"]) + "\n"
    full_report += "Total:             " + format_money(sales["jacks_total"]  + sales["sjs_total"]) + "\n"
    
    # calculate total tips across both venues.
    total_tips   = int(sales["jacks_tips"]) + int(sales["sjs_tips"])

    # @LOGAN?
    try:
        transactions = square_api.print_transactions_report(square_api.get_transactions(current=True))
    except:
        transactions = int(-111)
    full_report += "Total Transactions:\n" + format_money(transactions - total_tips) + "\n"
    full_report += "San Jac Tips:           " + format_money(sales["sjs_tips"])   + "\n"
    full_report += "Jack's Tips:            " + format_money(sales["jacks_tips"]) + "\n"
    # add splice in the total transactions and return the report.
    return full_report

def get_sales_hours(message):
        try:
            tmp=message.find('-')
            if tmp == -1: return "Please use proper syntax. eg. sales 05-14 (Use army time)"
            hours = message[tmp-2:tmp+3]
            start = hours[:2]
            end   = hours[3:]
        except:
            return "Please use proper syntax. eg. sales 03-14 (Use army time)"         
        #try: 
        payments = square_api.get_payments(current=True,hours=(start,end))

        #except: return "Square is fucking up. Try again"

        try:drawers = square_api.get_cash_drawer(report_date)
        except:drawers = []
        sales = square_api.sales_totals(payments,drawers,'')
        full_report = "SALES:\n"
        full_report += 'San Jac:           ' + format_money(sales['sjs_total'])+'\n'
        full_report += "Jack's:            " + format_money(sales['jacks_total'])+'\n'
        full_report += 'Total:             ' + format_money(sales['jacks_total']+sales['sjs_total'])+'\n'
        total_tips = int(sales['jacks_tips'])+int(sales['sjs_tips'])
        try: transactions = square_api.print_transactions_report(square_api.get_transactions(current=True))
        except: transactions = int(-111)
        full_report += "Total Transactions:\n" + format_money(transactions-total_tips)+'\n'
        return full_report

def get_week ():
        weekdays = \
        {
            "Sun" : 0,
            "Mon" : 1,
            "Tue" : 2,
            "Wed" : 3,
            "Thu" : 4,
            "Fri" : 5,
            "Sat" : 6,
        }

        # do some magic to calculate this time last year? @LOGAN?
        date = (datetime.today() - timedelta(days=weekdays[datetime.today().strftime("%a")])).strftime("%Y-%m-%d")

        try:
            payments = square_api.get_payments(date=date,current=True)
        except Exception as e:
            return "square_api.get_payments(): %s" % str(e)

        try:
            drawers = square_api.get_cash_drawer()
        except:
            drawers = []

        sales = square_api.sales_totals(payments, drawers, "")
        total_discount = -1.0*(sales["sjs_dcounts"]+sales["jacks_dcounts"]+sales["sjs_comps"]+sales["jacks_comps"])
        total_sales = sales["sjs_total"]+sales["jacks_total"]
        try:discount_percentage = "%.02f"%((total_discount/total_sales)*100)
        except:discount_percentage = "Error"
    
        full_report = "WTD SALES:\n"
        full_report += "San Jac:           " + format_money(sales["sjs_total"])   + "\n"
        full_report += "Jack's:            " + format_money(sales["jacks_total"]) + "\n"
        full_report += "Total:             " + format_money(sales["jacks_total"]  + sales["sjs_total"]) + "\n"
        full_report += "Discount Percentage: %s"%discount_percentage

        return full_report


# I'M PICKLE RIIIIICK!
# TODO: remove pickle rick.
def return_month ():
    return pickle.load(open("/opt/sjs/financial-automations/month.p", "rb"))

def return_year ():
    return pickle.load(open("/opt/sjs/financial-automations/year.p", "rb"))


########################################################################################################################
##### FLASK ROUTES
########################################################################################################################

@app.route("/")
def check_app():
    return Response("It works!"), 200

@app.route("/twilio", methods=["POST"])
def inbound_sms():
    response        = twiml.Response()
    inbound_message = request.form.get("Body")
    number          = request.form.get("From")

    # "arg" parsing.
    if "sales" in inbound_message.lower():
        if '-' in inbound_message.lower():
            send_sms(get_sales_hours(inbound_message.lower()),number)
        else:send_sms(get_sales(),number)

    elif "wtd" in inbound_message.lower():
        send_sms(get_week(),number)

    elif "mtd" in inbound_message.lower():
        response.message(return_month())

    elif "ytd" in inbound_message.lower():
        response.message(return_year())

    elif "increase" in inbound_message.lower():
        send_sms("Increasing prices by $1...",number)
        square_api.update_item_price(100)
        send_sms("Done Processing",number)

    elif "decrease" in inbound_message.lower():
        send_sms("Decreasing prices by $1...",number)
        square_api.update_item_price(-100)
        send_sms("Done Processing",number)

    elif "restore" in inbound_message.lower():
        send_sms("Restoring default prices...",number)
        square_api.restore_item_price("regular")
        send_sms("Done Processing",number)

    elif "report" in inbound_message.lower():
        send_sms("Processing report...",number)
        os.system("python /opt/sjs/financial-automations/square_api.py")
        send_sms("Done Processing",number)

    else:
        msg  = "Hi! All I understand for now is: \n"
        msg += "'sales':Current Sales\n"
        msg += "'sales hr-hr':Sales during hours in army time\n"
        msg += "'wtd':Week to date sales\n"
        msg += "'mtd':Month to date sales\n"
        msg += "'ytd': Year to date sales\n"
        msg += "'increase':Increase prices by $1\n"
        msg += "'decrease':Decrease prices by $1\n"
        msg += "'restore':Restore default prices\n"
        msg += "'report':Generate the sales report"

        response.message(msg)

    return Response(str(response), mimetype="application/xml"), 200

########################################################################################################################
##### MAIN LINE
########################################################################################################################

if __name__ == "__main__":
    app.run(debug=False)
