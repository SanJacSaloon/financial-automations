#!/opt/sjs/bin/python

import dateutil.relativedelta
import calendar
import gspread
import locale
import time
import json
import os

from datetime           import datetime, timedelta
from apiclient          import discovery, errors
from oauth2client       import client
from oauth2client       import tools
from oauth2client.file import Storage

from gspread_formatting import *


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
secrets            = json.loads(open("/opt/sjs/secrets.json").read())
SCOPES             = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME   = 'Google Sheets API Python Quickstart'
PARENT_FOLDER_ID   = secrets["google"]["parent_folder_id"]
CALLS              = 0

################FORMATS###################
currency = cellFormat(
        numberFormat=numberFormat(type='currency',pattern='[Red][<0]-$###,##0.00;[Black][>=0]$###,##0.00')
        )

percent = cellFormat(
        numberFormat=numberFormat(type='percent',pattern='##.#%')
        )

calculated = cellFormat(
        backgroundColor=color(40, 40, 40),
        textFormat=textFormat(bold=True)
)

calculated_currency = cellFormat(
        backgroundColor=color(40, 40, 40),
        textFormat=textFormat(bold=True),
        numberFormat=numberFormat(type='currency',pattern='[Red][<0]-$###,##0.00;[Black][>=0]$###,##0.00')
)

bold = cellFormat(
        textFormat=textFormat(bold=True)
)

heading = cellFormat(
        textFormat=textFormat(bold=True,underline=True),
        horizontalAlignment='CENTER',
        )
def get_credentials():
    """
    Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    global CALLS
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print 'Storing credentials to ' + credential_path
    return credentials

def find_folder(name,drive_api=False):
    if not drive_api:
        credentials = get_credentials()
        drive_api = discovery.build('drive', 'v3', credentials=credentials)
    page_token = None
    while True:
        response = drive_api.files().list(q="mimeType='application/vnd.google-apps.spreadsheet'",
                                              spaces='drive',
                                              fields='nextPageToken, files(id, name)',
                                              pageToken=page_token).execute()
        for file in response.get('files', []):
            if name in file.get('name'):
                print 'Found file: %s (%s)' % (file.get('name'), file.get('id'))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

def colnum_string(col=False,day=False):
    if col:
        string = ""
        while col > 0:
            col, remainder = divmod(col - 1, 26)
            string = chr(65 + remainder) + string
        return string
    elif day:
        days = {
            "sunday" :  [2,'B'],
            "monday" :  [3,'C'],
            "tuesday" :  [4,'D'],
            "wednesday" :  [5,'E'],
            "thursday" :  [6,'F'],
            "friday" :  [7,'G'],
            "saturday" :  [8,'H']
            }
        return days[day]


    else: return

def last_sunday_of_month(month):
    year = datetime.now().year
    last_sunday = max(week[-1] for week in calendar.monthcalendar(year, month))
    last_sunday = '{}-{}-{:2}'.format(year, calendar.month_abbr[month], last_sunday)
    last_sunday = datetime.strptime(last_sunday,"%Y-%b-%d")
    return last_sunday

def first_day_of_month(date,first_spreadsheet=False):
    global CALLS
    first_day = date + dateutil.relativedelta.relativedelta(months=1)
    first_day = first_day.replace(day=1)
    if first_spreadsheet: sheet = first_spreadsheet
    else: sheet = open_google_spreadsheet(spreadsheet_title= "%s-SplitLevel_Operations_Week"%date.strftime("%m%d%y"))
    wsheet = sheet.worksheet("San Jac")
    try:cell = wsheet.find(first_day.strftime("%m/%d/%y"))
    except:cell = wsheet.find(first_day.strftime("%m/%d/%y").replace('0',''))
    cell_letter = colnum_string(col=cell.col)
    CALLS += 2
    return cell_letter

def last_day_of_month(date,last_spreadsheet=False):
    global CALLS
    last_day = date + dateutil.relativedelta.relativedelta(months=1)
    last_day = last_day.replace(day=1)
    last_day = last_day+timedelta(days=-1)
    last_sunday = last_sunday_of_month(int(date.strftime("%m")))
    if last_spreadsheet: sheet = last_spreadsheet
    else: sheet = open_google_spreadsheet(spreadsheet_title= "%s-SplitLevel_Operations_Week"%last_sunday.strftime("%m%d%y"))
    wsheet = sheet.worksheet("San Jac")
    try:cell = wsheet.find(last_day.strftime("%m/%d/%y"))
    except:cell = wsheet.find(last_day.strftime("%m/%d/%y").replace('0',''))
    cell_letter = colnum_string(col=cell.col)
    CALLS += 3
    return cell_letter

def last_spreadsheet_of_month(month):
    global CALLS
    CALLS += 1
    return open_google_spreadsheet(spreadsheet_title= "%s-SplitLevel_Operations_Week"%last_sunday_of_month(month).strftime("%m%d%y"))

def last_year_sales(month=False,week=False):
    global CALLS
    value = 0
    if month:
        date = datetime.strptime(month,"%B-%Y")
        name = date + dateutil.relativedelta.relativedelta(years=-1)
        name = name.strftime("%B-%Y")
        sheet = open_google_spreadsheet(spreadsheet_title=name)
        wsheet = sheet.sheet1
        cell = wsheet.find("Gross Sales")
        gross_sales = wsheet.cell(int(cell.row),int(cell.col)+1,value_render_option='UNFORMATTED_VALUE')
        value = gross_sales.value
        CALLS += 4
    if week:
        date = datetime.strptime(month,"%B-%Y")
        date = date + dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.WE(1))
        name = date + dateutil.relativedelta.relativedelta(years=-1)
        if name.strftime("%A") != "Sunday":
            name = name + dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.SU(-1))
        name = "%s-SplitLevel_Operations_Week"%name.strftime("%m%d%y")
        sheet = open_google_spreadsheet(spreadsheet_title=name)
        wsheet = sheet.sheet1
        cell = wsheet.find("Gross Revenue")
        CALLS += 4
        gross_revenue = wsheet.cell(int(cell.row),int(cell.col)+1,value_render_option='UNFORMATTED_VALUE')
        value = gross_revenue.value
    return value

def find_date_cell(date,spreadsheet=False):
    if spreadsheet:sheet = spreadsheet
    else:
        last_sun = date + dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.SU(-1))
        name = "%s-SplitLevel_Operations_Week"%last_sun.strftime("%m%d%y")
        sheet = open_google_spreadsheet(spreadsheet_title=name)
    wsheet = sheet.worksheet("San Jac")
    short= date.strftime("%m/%d/%y").split('/')
    shorter='%02d/%02d/%02d'%(int(short[0]),int(short[1]), int(short[2]))
    shortest='%d/%d/%d'%(int(short[0]),int(short[1]), int(short[2]))
    short= date.strftime("%m/%d/%Y").split('/')
    longer='%d/%d/%s'%(int(short[0]),int(short[1]), int(short[2]))
    try:cell = wsheet.find(shorter)
    except:
        try:cell = wsheet.find(shortest)
        except:cell = wsheet.find(longer)
    return (sheet,cell.row,cell.col)

def retrieve_all_files(service,returnfiles=False):
  """Retrieve a list of File resources.

  Args:
    service: Drive API service instance.
  Returns:
    List of File resources.
  """
  result = {}
  page_token = None
  while True:
    try:
      param = {'supportsTeamDrives':True}
      if page_token:
        param['pageToken'] = page_token
      files = service.files().list(**param).execute()
      if returnfiles: return files
      for f in files['files']:
          result[f['name']]=f['id']
      page_token = files.get('nextPageToken')
      if not page_token:
        break
    except errors.HttpError, error:
      print 'An error occurred: %s' % error
      break
  return result

def return_all_files():
    credentials = get_credentials()
    drive_api = discovery.build('drive', 'v3', credentials=credentials)
    return retrieve_all_files(drive_api,returnfiles=True)

def open_google_spreadsheet(spreadsheet_id=False,spreadsheet_title=False):
    """Open sheet using gspread.
    :param spreadsheet_id: Grab spreadsheet id from URL to open. Like *1jMU5gNxEymrJd-gezJFPv3dQCvjwJs7QcaB-YyN_BD4*.
    """
    global CALLS
    CALLS += 3
    credentials = get_credentials()
    gs = gspread.authorize(credentials)
    if spreadsheet_id: return gs.open_by_key(spreadsheet_id)
    elif spreadsheet_title:
        try:return gs.open(spreadsheet_title)
        except:
            try:
                drive_api = discovery.build('drive', 'v3', credentials=credentials)
                files = retrieve_all_files(drive_api)
                return gs.open_by_key(files[spreadsheet_title])
            except:return False
    else: return False

def delete_google_spreadsheet(spreadsheet_id):
    global CALLS
    CALLS += 3
    credentials = get_credentials()
    gs = gspread.authorize(credentials)
    gs.del_spreadsheet(spreadsheet_id)

def create_google_spreadsheet(title, share_domains=False):
    """Create a new spreadsheet and open gspread object for it.
    .. note ::
        Created spreadsheet is not instantly visible in your Drive search and you need to access it by direct link.
    :param title: Spreadsheet title
    :param parent_folder_ids: A list of strings of parent folder ids (if any).
    :param share_domains: List of Google Apps domain whose members get full access rights to the created sheet. Very handy, otherwise the file is visible only to the service worker itself. Example:: ``["redinnovation.com"]``.
    """
    global CALLS
    credentials = get_credentials()
    drive_api = discovery.build('drive', 'v3', credentials=credentials)

    body = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
    }


    body["parents"] = [
        {
            'kind': 'drive#fileLink',
            'id': PARENT_FOLDER_ID
        }
    ]

    req = drive_api.files().create(body=body)
    new_sheet = req.execute()

    # Get id of fresh sheet
    spread_id = new_sheet["id"]

    # Grant permissions
    if share_domains:
        for domain in share_domains:

            # https://developers.google.com/drive/v3/web/manage-sharing#roles
            # https://developers.google.com/drive/v3/reference/permissions#resource-representations
            domain_permission = {
                'type': 'domain',
                'role': 'writer',
                'domain': domain,
                # Magic almost undocumented variable which makes files appear in your Google Drive
                'allowFileDiscovery': True,
            }

            req = drive_api.permissions().create(
                fileId=spread_id,
                body=domain_permission,
                fields="id"
            )

            req.execute()
    drive_api.files().update(fileId=spread_id,addParents=PARENT_FOLDER_ID[0],fields='id,parents').execute()
    spread = open_google_spreadsheet(spread_id)
    CALLS += 3
    return spread

# Uses the locale to format currency amounts correctly
locale.setlocale(locale.LC_ALL, '')

# Helper function to convert cent-based money amounts to dollars and cents
def format_money(amount):
  return locale.currency(amount / 100.)

def fill_sales(date,total):
    tmp = find_date_cell(date)
    sheet = tmp[0]
    row = tmp[1]
    col = tmp[2]
    colnum_string(col=col)

    print_date = date.strftime("%m%d%y")
    if date < datetime.strptime('Feb 14 2021', '%b %d %Y'):
        ###SAN JAC###
        print "[%s]: Populating sales for San Jac worksheet"%print_date
        san_jac_worksheet = sheet.worksheet("San Jac")
        san_jac_worksheet.update_cell(3,col,format_money(abs(total['sjs_liquor'])).replace('$',''))
        san_jac_worksheet.update_cell(4,col,format_money(abs(total['sjs_beer'])).replace('$',''))
        san_jac_worksheet.update_cell(5,col,format_money(abs(total['sjs_wine'])).replace('$',''))
        san_jac_worksheet.update_cell(7,col,format_money(abs(total['sjs_nonalc'])).replace('$',''))
        san_jac_worksheet.update_cell(8,col,format_money(abs(total['sjs_service'])).replace('$',''))
        san_jac_worksheet.update_cell(9,col,format_money(abs(total['sjs_retail'])).replace('$',''))
        san_jac_worksheet.update_cell(11,col,format_money(abs(total['sjs_credit'])).replace('$',''))
        san_jac_worksheet.update_cell(43,col,format_money(abs(total['sjs_comps'])).replace('$',''))
        san_jac_worksheet.update_cell(44,col,format_money(abs(total['sjs_dcounts'])).replace('$',''))
        san_jac_worksheet.update_cell(66,col,format_money(abs(total['sjs_cash'])).replace('$',''))
        san_jac_worksheet.update_cell(67,col,format_money(abs(total['sjs_paidout'])).replace('$',''))
        san_jac_worksheet.update_cell(68,col,format_money(abs(total['sjs_tip_credit'])).replace('$',''))
        san_jac_worksheet.update_cell(69,col,format_money(abs(total['sjs_tip_credit']*.025)).replace('$',''))
    else:
        ###SAN JAC###
        print "[%s]: Populating sales for San Jac worksheet"%print_date
        san_jac_worksheet = sheet.worksheet("San Jac")
        san_jac_worksheet.update_cell(3,col,format_money(abs(total['sjs_liquor'])).replace('$',''))
        san_jac_worksheet.update_cell(4,col,format_money(abs(total['sjs_beer'])).replace('$',''))
        san_jac_worksheet.update_cell(5,col,format_money(abs(total['sjs_wine'])).replace('$',''))
        san_jac_worksheet.update_cell(7,col,format_money(abs(total['sjs_nonalc'])).replace('$',''))
        san_jac_worksheet.update_cell(8,col,format_money(abs(total['sjs_service'])).replace('$',''))
        san_jac_worksheet.update_cell(9,col,format_money(abs(total['sjs_retail'])).replace('$',''))
        san_jac_worksheet.update_cell(11,col,format_money(abs(total['sjs_credit'])).replace('$',''))
        san_jac_worksheet.update_cell(43,col,format_money(abs(total['sjs_comps'])).replace('$',''))
        san_jac_worksheet.update_cell(44,col,format_money(abs(total['sjs_dcounts'])).replace('$',''))
        san_jac_worksheet.update_cell(85,col,format_money(abs(total['sjs_cash'])).replace('$',''))
        san_jac_worksheet.update_cell(86,col,format_money(abs(total['sjs_paidout'])).replace('$',''))
        san_jac_worksheet.update_cell(87,col,format_money(abs(total['sjs_tip_credit'])).replace('$',''))
        san_jac_worksheet.update_cell(88,col,format_money(abs(total['sjs_tip_credit']*.025)).replace('$',''))

    if date < datetime.strptime('Apr 1 2018', '%b %d %Y'):
        ###JACK'S###
        print "[%s]: Populating sales for Jack's worksheet"%print_date
        jacks_worksheet = sheet.worksheet("Jack's")
        jacks_worksheet.update_cell(3,col,format_money(abs(total['jacks_liquor'])).replace('$',''))
        jacks_worksheet.update_cell(4,col,format_money(abs(total['jacks_beer'])).replace('$',''))
        jacks_worksheet.update_cell(5,col,format_money(abs(total['jacks_wine'])).replace('$',''))
        jacks_worksheet.update_cell(7,col,format_money(abs(total['jacks_nonalc'])).replace('$',''))
        jacks_worksheet.update_cell(8,col,format_money(abs(total['jacks_service'])).replace('$',''))
        jacks_worksheet.update_cell(9,col,format_money(abs(total['jacks_retail'])).replace('$',''))
        jacks_worksheet.update_cell(11,col,format_money(abs(total['jacks_credit'])).replace('$',''))
        jacks_worksheet.update_cell(40,col,format_money(abs(total['jacks_comps'])).replace('$',''))
        jacks_worksheet.update_cell(41,col,format_money(abs(total['jacks_dcounts'])).replace('$',''))
        jacks_worksheet.update_cell(63,col,format_money(abs(total['jacks_cash'])).replace('$',''))
        jacks_worksheet.update_cell(64,col,format_money(abs(total['jacks_paidout'])).replace('$',''))
        jacks_worksheet.update_cell(65,col,format_money(abs(total['jacks_tip_credit'])).replace('$',''))
        jacks_worksheet.update_cell(66,col,format_money(abs(total['jacks_tip_credit']*.025)).replace('$',''))
    elif date < datetime.strptime('Feb 14 2021', '%b %d %Y'):
        ###JACK'S###
        print "[%s]: Populating sales for Jack's worksheet"%print_date
        jacks_worksheet = sheet.worksheet("Jack's")
        jacks_worksheet.update_cell(3,col,format_money(abs(total['jacks_liquor'])).replace('$',''))
        jacks_worksheet.update_cell(4,col,format_money(abs(total['jacks_beer'])).replace('$',''))
        jacks_worksheet.update_cell(5,col,format_money(abs(total['jacks_wine'])).replace('$',''))
        jacks_worksheet.update_cell(7,col,format_money(abs(total['jacks_nonalc'])).replace('$',''))
        jacks_worksheet.update_cell(8,col,format_money(abs(total['jacks_service'])).replace('$',''))
        jacks_worksheet.update_cell(9,col,format_money(abs(total['jacks_retail'])).replace('$',''))
        jacks_worksheet.update_cell(11,col,format_money(abs(total['jacks_credit'])).replace('$',''))
        jacks_worksheet.update_cell(43,col,format_money(abs(total['jacks_comps'])).replace('$',''))
        jacks_worksheet.update_cell(44,col,format_money(abs(total['jacks_dcounts'])).replace('$',''))
        jacks_worksheet.update_cell(66,col,format_money(abs(total['jacks_cash'])).replace('$',''))
        jacks_worksheet.update_cell(67,col,format_money(abs(total['jacks_paidout'])).replace('$',''))
        jacks_worksheet.update_cell(68,col,format_money(abs(total['jacks_tip_credit'])).replace('$',''))
        jacks_worksheet.update_cell(69,col,format_money(abs(total['jacks_tip_credit']*.025)).replace('$',''))
    else:
        ###JACK'S###
        print "[%s]: Populating sales for Jack's worksheet"%print_date
        jacks_worksheet = sheet.worksheet("Jack's")
        jacks_worksheet.update_cell(3,col,format_money(abs(total['jacks_liquor'])).replace('$',''))
        jacks_worksheet.update_cell(4,col,format_money(abs(total['jacks_beer'])).replace('$',''))
        jacks_worksheet.update_cell(5,col,format_money(abs(total['jacks_wine'])).replace('$',''))
        jacks_worksheet.update_cell(7,col,format_money(abs(total['jacks_nonalc'])).replace('$',''))
        jacks_worksheet.update_cell(8,col,format_money(abs(total['jacks_service'])).replace('$',''))
        jacks_worksheet.update_cell(9,col,format_money(abs(total['jacks_retail'])).replace('$',''))
        jacks_worksheet.update_cell(11,col,format_money(abs(total['jacks_credit'])).replace('$',''))
        jacks_worksheet.update_cell(43,col,format_money(abs(total['jacks_comps'])).replace('$',''))
        jacks_worksheet.update_cell(44,col,format_money(abs(total['jacks_dcounts'])).replace('$',''))
        jacks_worksheet.update_cell(85,col,format_money(abs(total['jacks_cash'])).replace('$',''))
        jacks_worksheet.update_cell(86,col,format_money(abs(total['jacks_paidout'])).replace('$',''))
        jacks_worksheet.update_cell(87,col,format_money(abs(total['jacks_tip_credit'])).replace('$',''))
        jacks_worksheet.update_cell(88,col,format_money(abs(total['jacks_tip_credit']*.025)).replace('$',''))


    sheet = open_google_spreadsheet(spreadsheet_title="Averages")
    if date.strftime("%A").lower() != "sunday":
            date = date + dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.SU(-1))
    tmp = find_date_cell(date,spreadsheet=sheet)
    row = tmp[1]
    ###SAN JAC###
    print "[%s]: Populating Averages sheet with San Jac sales"%print_date
    san_jac_worksheet = sheet.worksheet("San Jac")
    san_jac_worksheet.update_cell(row,col,format_money(abs(total['sjs_total'])).replace('$',''))

    ###JACK'S###
    print "[%s]: Populating Averages sheet with Jack's sales"%print_date
    jacks_worksheet = sheet.worksheet("Jack's")
    jacks_worksheet.update_cell(row,col,format_money(abs(total['jacks_total'])).replace('$',''))

def update_annual_sheet(year):
    date = datetime.strptime(year,"%Y")
    sheets = []
    for month in xrange(12):
        try:sheets.append(open_google_spreadsheet(spreadsheet_title=date.strftime("%B-%Y")).id)
        except:break
        date = date + dateutil.relativedelta.relativedelta(months=1)
    spreadsheet_title = datetime.strptime(year,"%Y").strftime("%Y")
    sheet = open_google_spreadsheet(spreadsheet_title=spreadsheet_title)
    worksheet = sheet.worksheet("Overview")
    cell_list = worksheet.range("A1:A15")
    cell_list[1].value = "Gross Sales: San Jac"
    cell_list[2].value = "Gross Sales: Jack's"
    cell_list[3].value = "Net Profit: San Jac"
    cell_list[4].value = "Net Profit: Jack's"
    cell_list[5].value = "Opp Cost: San Jac"
    cell_list[6].value = "Opp Cost: Jack's "
    cell_list[8].value = "Gross Sales"
    cell_list[9].value = "Net Profit"
    cell_list[10].value = "Opp Cost"
    cell_list[12].value = "Merch Sales:"
    cell_list[13].value = "Entertainment:"
    worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')

    gs_sjs = "="
    gs_jacks = "="
    np_sjs = "="
    np_jacks = "="
    oc_sjs = "="
    oc_jacks = "="
    gs = "=sum(B2:B3)"
    np = "=sum(B4:B5)"
    oc = "=sum(B6:B7)"
    merch = ""
    entertainment = ""

    for sheet_id in sheets:
        gs_sjs += '+sum(IMPORTRANGE("%s","Sheet1!B1"))'%sheet_id
        gs_jacks += '+sum(IMPORTRANGE("%s","Sheet1!B2"))'%sheet_id
        np_sjs += '+sum(IMPORTRANGE("%s","Sheet1!B3"))'%sheet_id
        np_jacks += '+sum(IMPORTRANGE("%s","Sheet1!B4"))'%sheet_id
        oc_sjs += '+sum(IMPORTRANGE("%s","Sheet1!B5"))'%sheet_id
        oc_jacks += '+sum(IMPORTRANGE("%s","Sheet1!B6"))'%sheet_id
        merch += '+sum(IMPORTRANGE("%s","Sheet1!B12"))'%sheet_id
        entertainment += '+sum(IMPORTRANGE("%s","Sheet1!B14"))'%sheet_id

    cell_list = worksheet.range("B1:B15")
    cell_list[1].value = gs_sjs
    cell_list[2].value = gs_jacks
    cell_list[3].value = np_sjs
    cell_list[4].value = np_jacks
    cell_list[5].value = oc_sjs
    cell_list[6].value = oc_jacks
    cell_list[8].value = gs
    cell_list[9].value = np
    cell_list[10].value = oc
    cell_list[12].value = merch
    cell_list[13].value = entertainment
    worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')

    cell_list = worksheet.range("C1:C15")
    cell_list[1].value ="=B2/month(now())"
    cell_list[2].value ="=B3/month(now())"
    cell_list[3].value ="=B4/month(now())"
    cell_list[4].value ="=B5/month(now())"
    cell_list[5].value ="=B6/month(now())"
    cell_list[6].value ="=B7/month(now())"
    cell_list[8].value ="=B9/month(now())"
    cell_list[9].value ="=B10/month(now())"
    cell_list[10].value ="=B11/month(now())"
    cell_list[12].value ="=B13/month(now())"
    cell_list[13].value ="=B14/month(now())"
    worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')

def test():
    global CALLS
    date=datetime.today()
    if date.strftime("%A").lower() != "sunday":
            date = date + dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.SU(-1))
    last_week_date = date + timedelta(days=-7)
    last_week_sheet_title="%s-SplitLevel_Operations_Week"%last_week_date.strftime("%m%d%y")
    last_week_sheet = open_google_spreadsheet(spreadsheet_title=last_week_sheet_title)
    #last_week_sheet_id = last_week_sheet.id
    overview_worksheet = last_week_sheet.worksheet("Overview") 
    san_jac_worksheet = last_week_sheet.worksheet("San Jac")
    jacks_worksheet = last_week_sheet.worksheet("Jack's")
    checks_worksheet = last_week_sheet.worksheet("Checks Written")
    debits_worksheet = last_week_sheet.worksheet("Debit Card Charges")
    #overview_worksheet = last_week_sheet.worksheet("Overview")
    
    '''
    fmt = cellFormat(
        backgroundColor=color(222, 217, 217),
        textFormat=textFormat(bold=True),
        horizontalAlignment='CENTER',
        #numberFormat=numberFormat(type='percent',pattern='##.#%'),
        numberFormat=numberFormat(type='currency',pattern='[Red][<0]$###,##0.00;[Black][>=0]$###,##0.00')
        )
    '''
    format_cell_ranges(overview_worksheet,[("A2:A8",bold),
                                            ("B2:B8",currency),
                                            ("C8",percent)])

    format_cell_ranges(san_jac_worksheet, [("A3:A73",bold),
                                            ("B1:I1",bold),
                                            ("B2:I2",heading),
                                            ("B3:I20",currency),
                                            ("B10:I10",calculated_currency),
                                            ("B23:I23",currency),
                                            ("B26:I26",currency),
                                            ("B29:I29",currency),
                                            ("B32:I45",currency),
                                            ("B39:I39",calculated_currency),
                                            ("B40:I40",calculated_currency),
                                            ("B49:I90",currency),
                                            ("B81:I81",calculated_currency),
                                            ("B82:I82",calculated_currency),
                                            ("B89:I89",calculated_currency),
                                            ("B90:I90",calculated_currency)])

    format_cell_ranges(jacks_worksheet, [("A3:A73",bold),
                                            ("B1:I1",bold),
                                            ("B2:I2",heading),
                                            ("B3:I20",currency),
                                            ("B10:I10",calculated_currency),
                                            ("B23:I23",currency),
                                            ("B26:I26",currency),
                                            ("B29:I29",currency),
                                            ("B32:I45",currency),
                                            ("B39:I39",calculated_currency),
                                            ("B40:I40",calculated_currency),
                                            ("B49:I90",currency),
                                            ("B81:I81",calculated_currency),
                                            ("B82:I82",calculated_currency),
                                            ("B89:I89",calculated_currency),
                                            ("B90:I90",calculated_currency)])

    format_cell_ranges(checks_worksheet, [("A1",bold),
                                            ("A2:F2",heading),
                                            ("A3:A90",bold),
                                            ("D3:D90",currency)])

    format_cell_ranges(debits_worksheet, [("A1",bold),
                                            ("A2:F2",heading),
                                            ("A3:A90",bold),
                                            ("C3:C90",currency)])

    #cell = san_jac_worksheet.cell(3,1)
    #print dir(cell)
    #cell.text_format['bold'] = True
    #cell.update()
    #return sheet

def build_weekly_sheet(date):
    global CALLS
    if date.strftime("%A").lower() != "sunday":
            date = date + dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.SU(-1))
    last_week_date = date + timedelta(days=-7)
    last_week_sheet_title="%s-SplitLevel_Operations_Week"%last_week_date.strftime("%m%d%y")
    last_week_sheet = open_google_spreadsheet(spreadsheet_title=last_week_sheet_title)
    last_week_sheet_id = last_week_sheet.id

    print_date = date.strftime("%m%d%y")
    print "Creating weekly sheet: %s-SplitLevel_Operations_Week"%print_date
    sheet = create_google_spreadsheet("%s-SplitLevel_Operations_Week"%print_date)
    try:
        #wsheet.update_cell(row,col,value)
        ###OVERVIEW###
        overview_worksheet = sheet.sheet1

        ###SAN JAC###
        print "[%s]: Populating San Jac worksheet"%print_date
        san_jac_worksheet = sheet.add_worksheet("San Jac",95,12)
        cell_list = san_jac_worksheet.range("A1:A90")
        cell_list[3-1].value = "Liquor Sales"
        cell_list[4-1].value = "Beer Sales"
        cell_list[5-1].value = "Wine Sales"
        cell_list[6-1].value = "Red Bull Sales"
        cell_list[7-1].value = "Non-Alcohol Sales"
        cell_list[8-1].value = "Room Rental"
        cell_list[9-1].value = "Merch Sales"
        cell_list[10-1].value = "Total:"
        cell_list[11-1].value = "Credit"
        cell_list[12-1].value = "Processing Fees"
        cell_list[14-1].value = "Liquor cost"
        cell_list[16-1].value = "Beer cost"
        cell_list[18-1].value = "Wine cost"
        cell_list[19-1].value = "Merch cost"
        cell_list[20-1].value = "Taxes"
        cell_list[22-1].value = "Door Hours"
        cell_list[23-1].value = "Cost @10"
        cell_list[25-1].value = "Bar Tender Hours"
        cell_list[26-1].value = "Cost @2.13"
        cell_list[28-1].value = "Happy Hour Bar Tender Hours"
        cell_list[29-1].value = "Cost @5.5"
        cell_list[31-1].value = "Happy Hour Bar Tender Hours"
        cell_list[32-1].value = "Cost @8"
        cell_list[34-1].value = "Management"
        cell_list[36-1].value = "Payroll Taxes"
        cell_list[38-1].value = "Entertainment"
        cell_list[39-1].value = "Total Operational Expenses:"
        cell_list[40-1].value = "Net Operating Revenue:"
        cell_list[43-1].value = "Comps"
        cell_list[44-1].value = "Discount"
        cell_list[45-1].value = "Total Opportunity Cost:"
        cell_list[47-1].value = "Days in month"
        cell_list[48-1].value = "DAILY STATIC COSTS"
        cell_list[49-1].value = "Advertising & Marketing"
        cell_list[50-1].value = "Auto"
        cell_list[51-1].value = "Bank & Credit Card Charges"
        cell_list[52-1].value = "Bank Charges & Fees"
        cell_list[53-1].value = "Bar & Office Supplies"
        cell_list[54-1].value = "Cash Back Expense"
        cell_list[55-1].value = "Cash Short/(Over)"
        cell_list[56-1].value = "Cleaning Service"
        cell_list[57-1].value = "Contract Labor"
        cell_list[58-1].value = "Donation"
        cell_list[59-1].value = "Dues & Subscriptions"
        cell_list[60-1].value = "Equipment Rent & Lease"
        cell_list[61-1].value = "Event Catering"
        cell_list[62-1].value = "Guaranteed Payment"
        cell_list[63-1].value = "Ice"
        cell_list[64-1].value = "Insurance"
        cell_list[65-1].value = "Legal & Professional Services"
        cell_list[66-1].value = "Licenses & Permits"
        cell_list[67-1].value = "Maintenance & Repairs"
        cell_list[68-1].value = "Miscellaneous"
        cell_list[69-1].value = "Payroll Prep"
        cell_list[70-1].value = "Postage & Freight"
        cell_list[71-1].value = "Printing"
        cell_list[72-1].value = "Property Taxes"
        cell_list[73-1].value = "Rent"
        cell_list[74-1].value = "Staff Outings"
        cell_list[75-1].value = "Telephone"
        cell_list[76-1].value = "Utilities"
        cell_list[77-1].value = "  Cable"
        cell_list[78-1].value = "  Electricity"
        cell_list[79-1].value = "  Gas"
        cell_list[81-1].value = "Total"
        cell_list[82-1].value = "Net Profit:"
        cell_list[85-1].value = "Cash in"
        cell_list[86-1].value = "Paid out"
        cell_list[87-1].value = "Tip out"
        cell_list[88-1].value = "Tip credit card fee"
        cell_list[89-1].value = "Net Cash:"
        cell_list[90-1].value = "Credit:"
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 6

        sjs_date = date
        cell_list = san_jac_worksheet.range("B1:B90")
        cell_list[1-1].value = sjs_date.strftime("%m/%d/%y")
        cell_list[2-1].value = sjs_date.strftime("%A")
        cell_list[10-1].value = "=SUM(B3:B9)"
        cell_list[12-1].value = "=B11*0.025"
        cell_list[14-1].value = "=B3*0.165"
        cell_list[16-1].value = "=B4*0.27"
        cell_list[18-1].value = "=B5*0.14"
        cell_list[19-1].value = "=B9*0.54"
        cell_list[20-1].value = "=((sum(B3:B5)/1.0825)*0.067)+((sum(B3:B5)/1.0825)*0.0825+sum(B6:B9)*0.0825)"
        cell_list[23-1].value = "=B22*10"
        cell_list[26-1].value = "=B25*2.13"
        cell_list[29-1].value = "=B28*5.5"
        cell_list[32-1].value = "=B31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((sjs_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(B34,B29,B26,B23)*0.165012146"
        cell_list[39-1].value = "=SUM(B12:B20,B23,B26,B29:B38)"
        cell_list[40-1].value = "=if(now()>B1,B10-B39,0)"
        cell_list[45-1].value = "=sum(B43:B44)"
        cell_list[47-1].value = "=DAY(EOMONTH(B1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/B$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/B$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/B$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/B$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/B$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/B$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/B$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/B$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/B$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/B$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/B$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/B$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/B$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/B$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/B$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/B$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/B$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/B$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/B$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/B$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/B$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/B$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/B$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/B$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/B$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/B$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/B$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/B$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/B$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/B$47/2'
        cell_list[81-1].value = '=sum(B49:B79)'
        cell_list[82-1].value = '=if(now()>B1,B40-B81,0)'
        cell_list[89-1].value = '=B85-B86+B88'
        cell_list[90-1].value = '=B11'
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2
        #format_cell_range(san_jac_worksheet, 'c8', calculated)
        

        sjs_date = sjs_date+timedelta(days=1)
        cell_list = san_jac_worksheet.range("c1:c90")
        cell_list[1-1].value = sjs_date.strftime("%m/%d/%y")
        cell_list[2-1].value = sjs_date.strftime("%A")
        cell_list[10-1].value = "=SUM(c3:c9)"
        cell_list[12-1].value = "=c11*0.025"
        cell_list[14-1].value = "=c3*0.165"
        cell_list[16-1].value = "=c4*0.27"
        cell_list[18-1].value = "=c5*0.14"
        cell_list[19-1].value = "=c9*0.54"
        cell_list[20-1].value = "=((sum(c3:c5)/1.0825)*0.067)+((sum(c3:c5)/1.0825)*0.0825+sum(c6:c9)*0.0825)"
        cell_list[23-1].value = "=c22*10"
        cell_list[26-1].value = "=c25*2.13"
        cell_list[29-1].value = "=c28*5.5"
        cell_list[32-1].value = "=c31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((sjs_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(c34,c29,c26,c23)*0.165012146"
        cell_list[39-1].value = "=SUM(c12:c20,c23,c26,c29:c38)"
        cell_list[40-1].value = "=if(now()>C1,c10-c39,0)"
        cell_list[45-1].value = "=sum(c43:c44)"
        cell_list[47-1].value = "=DAY(EOMONTH(c1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/C$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/C$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/C$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/C$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/C$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/C$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/C$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/C$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/C$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/C$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/C$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/C$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/C$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/C$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/C$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/C$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/C$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/C$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/C$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/C$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/C$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/C$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/C$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/C$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/C$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/C$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/C$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/C$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/C$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/C$47/2'
        cell_list[81-1].value = '=sum(c49:c79)'
        cell_list[82-1].value = '=if(now()>C1,c40-c81,0)'
        cell_list[89-1].value = '=c85-c86+c88'
        cell_list[90-1].value = '=c11'
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        sjs_date = sjs_date+timedelta(days=1)
        cell_list = san_jac_worksheet.range("d1:d90")
        cell_list[1-1].value = sjs_date.strftime("%m/%d/%y")
        cell_list[2-1].value = sjs_date.strftime("%A")
        cell_list[10-1].value = "=SUM(d3:d9)"
        cell_list[12-1].value = "=d11*0.025"
        cell_list[14-1].value = "=d3*0.165"
        cell_list[16-1].value = "=d4*0.27"
        cell_list[18-1].value = "=d5*0.14"
        cell_list[19-1].value = "=d9*0.54"
        cell_list[20-1].value = "=((sum(d3:d5)/1.0825)*0.067)+((sum(d3:d5)/1.0825)*0.0825+sum(d6:d9)*0.0825)"
        cell_list[23-1].value = "=d22*10"
        cell_list[26-1].value = "=d25*2.13"
        cell_list[29-1].value = "=d28*5.5"
        cell_list[32-1].value = "=d31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((sjs_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(d34,d29,d26,d23)*0.165012146"
        cell_list[39-1].value = "=SUM(d12:d20,d23,d26,d29:d38)"
        cell_list[40-1].value = "=if(now()>D1,d10-d39,0)"
        cell_list[45-1].value = "=sum(d43:d44)"
        cell_list[47-1].value = "=DAY(EOMONTH(d1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/D$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/D$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/D$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/D$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/D$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/D$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/D$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/D$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/D$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/D$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/D$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/D$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/D$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/D$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/D$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/D$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/D$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/D$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/D$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/D$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/D$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/D$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/D$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/D$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/D$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/D$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/D$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/D$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/D$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/D$47/2'
        cell_list[81-1].value = '=sum(D49:D79)'
        cell_list[82-1].value = '=if(now()>D1,D40-D81,0)'
        cell_list[89-1].value = '=D85-D86+D88'
        cell_list[90-1].value = '=d11'
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        sjs_date = sjs_date+timedelta(days=1)
        cell_list = san_jac_worksheet.range("e1:e90")
        cell_list[1-1].value = sjs_date.strftime("%m/%d/%y")
        cell_list[2-1].value = sjs_date.strftime("%A")
        cell_list[10-1].value = "=SUM(e3:e9)"
        cell_list[12-1].value = "=e11*0.025"
        cell_list[14-1].value = "=e3*0.165"
        cell_list[16-1].value = "=e4*0.27"
        cell_list[18-1].value = "=e5*0.14"
        cell_list[19-1].value = "=e9*0.54"
        cell_list[20-1].value = "=((sum(e3:e5)/1.0825)*0.067)+((sum(e3:e5)/1.0825)*0.0825+sum(e6:e9)*0.0825)"
        cell_list[23-1].value = "=e22*10"
        cell_list[26-1].value = "=e25*2.13"
        cell_list[29-1].value = "=e28*5.5"
        cell_list[32-1].value = "=e31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((sjs_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(e34,e29,e26,e23)*0.165012146"
        cell_list[39-1].value = "=SUM(e12:e20,e23,e26,e29:e38)"
        cell_list[40-1].value = "=if(now()>E1,e10-e39,0)"
        cell_list[45-1].value = "=sum(e43:e44)"
        cell_list[47-1].value = "=DAY(EOMONTH(e1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/E$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/E$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/E$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/E$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/E$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/E$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/E$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/E$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/E$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/E$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/E$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/E$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/E$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/E$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/E$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/E$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/E$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/E$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/E$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/E$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/E$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/E$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/E$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/E$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/E$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/E$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/E$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/E$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/E$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/E$47/2'
        cell_list[81-1].value = '=sum(E49:E79)'
        cell_list[82-1].value = '=if(now()>E1,E40-E81,0)'
        cell_list[89-1].value = '=E85-E86+E88'
        cell_list[90-1].value = '=e11'
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        sjs_date = sjs_date+timedelta(days=1)
        cell_list = san_jac_worksheet.range("f1:f90")
        cell_list[1-1].value = sjs_date.strftime("%m/%d/%y")
        cell_list[2-1].value = sjs_date.strftime("%A")
        cell_list[10-1].value = "=SUM(f3:f9)"
        cell_list[12-1].value = "=f11*0.025"
        cell_list[14-1].value = "=f3*0.165"
        cell_list[16-1].value = "=f4*0.27"
        cell_list[18-1].value = "=f5*0.14"
        cell_list[19-1].value = "=f9*0.54"
        cell_list[20-1].value = "=((sum(f3:f5)/1.0825)*0.067)+((sum(f3:f5)/1.0825)*0.0825+sum(f6:f9)*0.0825)"
        cell_list[23-1].value = "=f22*10"
        cell_list[26-1].value = "=f25*2.13"
        cell_list[29-1].value = "=f28*5.5"
        cell_list[32-1].value = "=f31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((sjs_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(f34,f29,f26,f23)*0.165012146"
        cell_list[39-1].value = "=SUM(f12:f20,f23,f26,f29:f38)"
        cell_list[40-1].value = "=if(now()>F1,f10-f39,0)"
        cell_list[45-1].value = "=sum(f43:f44)"
        cell_list[47-1].value = "=DAY(EOMONTH(f1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/F$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/F$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/F$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/F$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/F$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/F$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/F$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/F$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/F$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/F$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/F$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/F$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/F$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/F$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/F$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/F$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/F$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/F$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/F$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/F$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/F$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/F$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/F$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/F$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/F$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/F$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/F$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/F$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/F$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/F$47/2'
        cell_list[81-1].value = '=sum(F49:F79)'
        cell_list[82-1].value = '=if(now()>F1,F40-F81,0)'
        cell_list[89-1].value = '=F85-F86+F88'
        cell_list[90-1].value = '=f11'
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        sjs_date = sjs_date+timedelta(days=1)
        cell_list = san_jac_worksheet.range("g1:g90")
        cell_list[1-1].value = sjs_date.strftime("%m/%d/%y")
        cell_list[2-1].value = sjs_date.strftime("%A")
        cell_list[10-1].value = "=SUM(g3:g9)"
        cell_list[12-1].value = "=g11*0.025"
        cell_list[14-1].value = "=g3*0.165"
        cell_list[16-1].value = "=g4*0.27"
        cell_list[18-1].value = "=g5*0.14"
        cell_list[19-1].value = "=g9*0.54"
        cell_list[20-1].value = "=((sum(g3:g5)/1.0825)*0.067)+((sum(g3:g5)/1.0825)*0.0825+sum(g6:g9)*0.0825)"
        cell_list[23-1].value = "=g22*10"
        cell_list[26-1].value = "=g25*2.13"
        cell_list[29-1].value = "=g28*5.5"
        cell_list[32-1].value = "=g31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((sjs_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(g34,g29,g26,g23)*0.165012146"
        cell_list[39-1].value = "=SUM(g12:g20,g23,g26,g29:g38)"
        cell_list[40-1].value = "=if(now()>G1,g10-g39,0)"
        cell_list[45-1].value = "=sum(g43:g44)"
        cell_list[47-1].value = "=DAY(EOMONTH(g1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/G$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/G$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/G$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/G$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/G$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/G$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/G$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/G$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/G$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/G$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/G$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/G$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/G$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/G$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/G$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/G$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/G$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/G$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/G$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/G$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/G$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/G$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/G$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/G$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/G$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/G$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/G$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/G$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/G$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/G$47/2'
        cell_list[81-1].value = '=sum(G49:G79)'
        cell_list[82-1].value = '=if(now()>G1,G40-G81,0)'
        cell_list[89-1].value = '=G85-G86+G88'
        cell_list[90-1].value = '=g11'
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        sjs_date = sjs_date+timedelta(days=1)
        cell_list = san_jac_worksheet.range("h1:h90")
        cell_list[1-1].value = sjs_date.strftime("%m/%d/%y")
        cell_list[2-1].value = sjs_date.strftime("%A")
        cell_list[10-1].value = "=SUM(h3:h9)"
        cell_list[12-1].value = "=h11*0.025"
        cell_list[14-1].value = "=h3*0.165"
        cell_list[16-1].value = "=h4*0.27"
        cell_list[18-1].value = "=h5*0.14"
        cell_list[19-1].value = "=h9*0.54"
        cell_list[20-1].value = "=((sum(h3:h5)/1.0825)*0.067)+((sum(h3:h5)/1.0825)*0.0825+sum(h6:h9)*0.0825)"
        cell_list[23-1].value = "=h22*10"
        cell_list[26-1].value = "=h25*2.13"
        cell_list[29-1].value = "=h28*5.5"
        cell_list[32-1].value = "=h31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((sjs_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(h34,h29,h26,h23)*0.165012146"
        cell_list[39-1].value = "=SUM(h12:h20,h23,h26,h29:h38)"
        cell_list[40-1].value = "=if(now()>H1,h10-h39,0)"
        cell_list[45-1].value = "=sum(h43:h44)"
        cell_list[47-1].value = "=DAY(EOMONTH(h1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/H$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/H$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/H$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/H$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/H$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/H$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/H$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/H$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/H$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/H$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/H$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/H$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/H$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/H$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/H$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/H$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/H$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/H$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/H$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/H$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/H$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/H$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/H$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/H$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/H$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/H$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/H$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/H$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/H$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/H$47/2'
        cell_list[81-1].value = '=sum(H49:H79)'
        cell_list[82-1].value = '=if(now()>H1,H40-H81,0)'
        cell_list[89-1].value = '=H85-H86+H88'
        cell_list[90-1].value = '=h11'
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        cell_list = san_jac_worksheet.range("i1:i90")
        cell_list[2-1].value = "Week"
        cell_list[3-1].value = "=sum(B3:H3)"
        cell_list[4-1].value = "=sum(B4:H4)"
        cell_list[5-1].value = "=sum(B5:H5)"
        cell_list[6-1].value = "=sum(B6:H6)"
        cell_list[7-1].value = "=sum(B7:H7)"
        cell_list[8-1].value = "=sum(B8:H8)"
        cell_list[9-1].value = "=sum(B9:H9)"
        cell_list[10-1].value = "=sum(B10:H10)"
        cell_list[11-1].value = "=sum(B11:H11)"
        cell_list[12-1].value = "=sum(B12:H12)"
        cell_list[14-1].value = "=sum(B14:H14)"
        cell_list[16-1].value = "=sum(B16:H16)"
        cell_list[18-1].value = "=sum(B18:H18)"
        cell_list[19-1].value = "=sum(B19:H19)"
        cell_list[20-1].value = "=sum(B20:H20)"
        cell_list[22-1].value = "=sum(B22:H22)"
        cell_list[23-1].value = "=sum(B23:H23)"
        cell_list[25-1].value = "=sum(B25:H25)"
        cell_list[26-1].value = "=sum(B26:H26)"
        cell_list[28-1].value = "=sum(B28:H28)"
        cell_list[29-1].value = "=sum(B29:H29)"
        cell_list[31-1].value = "=sum(B31:H31)"
        cell_list[32-1].value = "=sum(B32:H32)"
        cell_list[34-1].value = "=sum(B34:H34)"
        cell_list[36-1].value = "=sum(B36:H36)"
        cell_list[38-1].value = "=sum(B38:H38)"
        cell_list[39-1].value = "=sum(B39:H39)"
        cell_list[40-1].value = "=sum(B40:H40)"
        cell_list[43-1].value = "=sum(B43:H43)"
        cell_list[44-1].value = "=sum(B44:H44)"
        cell_list[45-1].value = "=sum(B45:H45)"
        cell_list[49-1].value = "=sum(B49:H49)"
        cell_list[50-1].value = "=sum(B50:H50)"
        cell_list[51-1].value = "=sum(B51:H51)"
        cell_list[52-1].value = "=sum(B52:H52)"
        cell_list[53-1].value = "=sum(B53:H53)"
        cell_list[54-1].value = "=sum(B54:H54)"
        cell_list[55-1].value = "=sum(B55:H55)"
        cell_list[56-1].value = "=sum(B56:H56)"
        cell_list[57-1].value = "=sum(B57:H57)"
        cell_list[58-1].value = "=sum(B58:H58)"
        cell_list[59-1].value = "=sum(B59:H59)"
        cell_list[60-1].value = "=sum(B60:H60)"
        cell_list[61-1].value = "=sum(B61:H61)"
        cell_list[62-1].value = "=sum(B62:H62)"
        cell_list[63-1].value = "=sum(B63:H63)"
        cell_list[64-1].value = "=sum(B64:H64)"
        cell_list[65-1].value = "=sum(B65:H65)"
        cell_list[66-1].value = "=sum(B66:H66)"
        cell_list[67-1].value = "=sum(B67:H67)"
        cell_list[68-1].value = "=sum(B68:H68)"
        cell_list[69-1].value = "=sum(B69:H69)"
        cell_list[70-1].value = "=sum(B70:H70)"
        cell_list[71-1].value = "=sum(B71:H71)"
        cell_list[72-1].value = "=sum(B72:H72)"
        cell_list[73-1].value = "=sum(B73:H73)"
        cell_list[74-1].value = "=sum(B74:H74)"
        cell_list[75-1].value = "=sum(B75:H75)"
        cell_list[76-1].value = "=sum(B76:H76)"
        cell_list[77-1].value = "=sum(B77:H77)"
        cell_list[78-1].value = "=sum(B78:H78)"
        cell_list[79-1].value = "=sum(B79:H79)"
        cell_list[81-1].value = "=sum(B81:H81)"
        cell_list[82-1].value = "=sum(B82:H82)"
        cell_list[89-1].value = "=sum(B89:H89)"
        cell_list[90-1].value = "=sum(B90:H90)"
        san_jac_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        ###JACK'S###
        print "[%s]: Populating Jack's worksheet"%print_date
        jacks_worksheet = sheet.add_worksheet("Jack's",95,12)
        cell_list = jacks_worksheet.range("A1:A90")
        cell_list[3-1].value = "Liquor Sales"
        cell_list[4-1].value = "Beer Sales"
        cell_list[5-1].value = "Wine Sales"
        cell_list[6-1].value = "Red Bull Sales"
        cell_list[7-1].value = "Non-Alcohol Sales"
        cell_list[8-1].value = "Room Rental"
        cell_list[9-1].value = "Merch Sales"
        cell_list[10-1].value = "Total:"
        cell_list[11-1].value = "Credit"
        cell_list[12-1].value = "Processing Fees"
        cell_list[14-1].value = "Liquor cost"
        cell_list[16-1].value = "Beer cost"
        cell_list[18-1].value = "Wine cost"
        cell_list[19-1].value = "Merch cost"
        cell_list[20-1].value = "Taxes"
        cell_list[22-1].value = "Door Hours"
        cell_list[23-1].value = "Cost @10"
        cell_list[25-1].value = "Bar Tender Hours"
        cell_list[26-1].value = "Cost @2.13"
        cell_list[28-1].value = "Happy Hour Bar Tender Hours"
        cell_list[29-1].value = "Cost @5.5"
        cell_list[31-1].value = "Happy Hour Bar Tender Hours"
        cell_list[32-1].value = "Cost @8"
        cell_list[34-1].value = "Management"
        cell_list[36-1].value = "Payroll Taxes"
        cell_list[38-1].value = "Entertainment"
        cell_list[39-1].value = "Total Operational Expenses:"
        cell_list[40-1].value = "Net Operating Revenue:"
        cell_list[43-1].value = "Comps"
        cell_list[44-1].value = "Discount"
        cell_list[45-1].value = "Total Opportunity Cost:"
        cell_list[47-1].value = "Days in month"
        cell_list[48-1].value = "DAILY STATIC COSTS"
        cell_list[49-1].value = "Advertising & Marketing"
        cell_list[50-1].value = "Auto"
        cell_list[51-1].value = "Bank & Credit Card Charges"
        cell_list[52-1].value = "Bank Charges & Fees"
        cell_list[53-1].value = "Bar & Office Supplies"
        cell_list[54-1].value = "Cash Back Expense"
        cell_list[55-1].value = "Cash Short/(Over)"
        cell_list[56-1].value = "Cleaning Service"
        cell_list[57-1].value = "Contract Labor"
        cell_list[58-1].value = "Donation"
        cell_list[59-1].value = "Dues & Subscriptions"
        cell_list[60-1].value = "Equipment Rent & Lease"
        cell_list[61-1].value = "Event Catering"
        cell_list[62-1].value = "Guaranteed Payment"
        cell_list[63-1].value = "Ice"
        cell_list[64-1].value = "Insurance"
        cell_list[65-1].value = "Legal & Professional Services"
        cell_list[66-1].value = "Licenses & Permits"
        cell_list[67-1].value = "Maintenance & Repairs"
        cell_list[68-1].value = "Miscellaneous"
        cell_list[69-1].value = "Payroll Prep"
        cell_list[70-1].value = "Postage & Freight"
        cell_list[71-1].value = "Printing"
        cell_list[72-1].value = "Property Taxes"
        cell_list[73-1].value = "Rent"
        cell_list[74-1].value = "Staff Outings"
        cell_list[75-1].value = "Telephone"
        cell_list[76-1].value = "Utilities"
        cell_list[77-1].value = "  Cable"
        cell_list[78-1].value = "  Electricity"
        cell_list[79-1].value = "  Gas"
        cell_list[81-1].value = "Total"
        cell_list[82-1].value = "Net Profit:"
        cell_list[85-1].value = "Cash in"
        cell_list[86-1].value = "Paid out"
        cell_list[87-1].value = "Tip out"
        cell_list[88-1].value = "Tip credit card fee"
        cell_list[89-1].value = "Net Cash:"
        cell_list[90-1].value = "Credit:"
        jacks_worksheet.update_cells(cell_list)
        CALLS += 3

        jacks_date = date
        cell_list = jacks_worksheet.range("B1:B90")
        cell_list[1-1].value = jacks_date.strftime("%m/%d/%y")
        cell_list[2-1].value = jacks_date.strftime("%A")
        cell_list[10-1].value = "=SUM(B3:B9)"
        cell_list[12-1].value = "=B11*0.025"
        cell_list[14-1].value = "=B3*0.165"
        cell_list[16-1].value = "=B4*0.27"
        cell_list[18-1].value = "=B5*0.14"
        cell_list[19-1].value = "=B9*0.54"
        cell_list[20-1].value = "=((sum(B3:B5)/1.0825)*0.067)+((sum(B3:B5)/1.0825)*0.0825+sum(B6:B9)*0.0825)"
        cell_list[23-1].value = "=B22*10"
        cell_list[26-1].value = "=B25*2.13"
        cell_list[29-1].value = "=B28*5.5"
        cell_list[32-1].value = "=B31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((jacks_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(B34,B29,B26,B23)*0.165012146"
        cell_list[39-1].value = "=SUM(B12:B20,B23,B26,B29:B38)"
        cell_list[40-1].value = "=if(now()>B1,B10-B39,0)"
        cell_list[45-1].value = "=sum(B43:B44)"
        cell_list[47-1].value = "=DAY(EOMONTH(B1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/B$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/B$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/B$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/B$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/B$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/B$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/B$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/B$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/B$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/B$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/B$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/B$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/B$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/B$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/B$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/B$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/B$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/B$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/B$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/B$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/B$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/B$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/B$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/B$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/B$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/B$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/B$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/B$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/B$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/B$47/2'
        cell_list[81-1].value = '=sum(B49:B79)'
        cell_list[82-1].value = '=if(now()>B1,B40-B81,0)'
        cell_list[89-1].value = '=B85-B86+B88'
        cell_list[90-1].value = '=B11'
        jacks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        jacks_date = jacks_date+timedelta(days=1)
        cell_list = jacks_worksheet.range("c1:c90")
        cell_list[1-1].value = jacks_date.strftime("%m/%d/%y")
        cell_list[2-1].value = jacks_date.strftime("%A")
        cell_list[10-1].value = "=SUM(c3:c9)"
        cell_list[12-1].value = "=c11*0.025"
        cell_list[14-1].value = "=c3*0.165"
        cell_list[16-1].value = "=c4*0.27"
        cell_list[18-1].value = "=c5*0.14"
        cell_list[19-1].value = "=c9*0.54"
        cell_list[20-1].value = "=((sum(c3:c5)/1.0825)*0.067)+((sum(c3:c5)/1.0825)*0.0825+sum(c6:c9)*0.0825)"
        cell_list[23-1].value = "=c22*10"
        cell_list[26-1].value = "=c25*2.13"
        cell_list[29-1].value = "=c28*5.5"
        cell_list[32-1].value = "=c31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((jacks_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(c34,c29,c26,c23)*0.165012146"
        cell_list[39-1].value = "=SUM(c12:c20,c23,c26,c29:c38)"
        cell_list[40-1].value = "=if(now()>C1,c10-c39,0)"
        cell_list[45-1].value = "=sum(c43:c44)"
        cell_list[47-1].value = "=DAY(EOMONTH(c1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/C$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/C$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/C$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/C$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/C$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/C$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/C$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/C$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/C$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/C$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/C$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/C$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/C$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/C$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/C$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/C$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/C$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/C$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/C$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/C$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/C$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/C$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/C$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/C$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/C$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/C$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/C$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/C$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/C$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/C$47/2'
        cell_list[81-1].value = '=sum(c49:c79)'
        cell_list[82-1].value = '=if(now()>C1,c40-c81,0)'
        cell_list[89-1].value = '=c85-c86+c88'
        cell_list[90-1].value = '=c11'
        jacks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        jacks_date = jacks_date+timedelta(days=1)
        cell_list = jacks_worksheet.range("d1:d90")
        cell_list[1-1].value = jacks_date.strftime("%m/%d/%y")
        cell_list[2-1].value = jacks_date.strftime("%A")
        cell_list[10-1].value = "=SUM(d3:d9)"
        cell_list[12-1].value = "=d11*0.025"
        cell_list[14-1].value = "=d3*0.165"
        cell_list[16-1].value = "=d4*0.27"
        cell_list[18-1].value = "=d5*0.14"
        cell_list[19-1].value = "=d9*0.54"
        cell_list[20-1].value = "=((sum(d3:d5)/1.0825)*0.067)+((sum(d3:d5)/1.0825)*0.0825+sum(d6:d9)*0.0825)"
        cell_list[23-1].value = "=d22*10"
        cell_list[26-1].value = "=d25*2.13"
        cell_list[29-1].value = "=d28*5.5"
        cell_list[32-1].value = "=d31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((jacks_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(d34,d29,d26,d23)*0.165012146"
        cell_list[39-1].value = "=SUM(d12:d20,d23,d26,d29:d38)"
        cell_list[40-1].value = "=if(now()>D1,d10-d39,0)"
        cell_list[45-1].value = "=sum(d43:d44)"
        cell_list[47-1].value = "=DAY(EOMONTH(d1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/D$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/D$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/D$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/D$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/D$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/D$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/D$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/D$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/D$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/D$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/D$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/D$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/D$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/D$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/D$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/D$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/D$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/D$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/D$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/D$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/D$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/D$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/D$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/D$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/D$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/D$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/D$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/D$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/D$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/D$47/2'
        cell_list[81-1].value = '=sum(D49:D79)'
        cell_list[82-1].value = '=if(now()>D1,D40-D81,0)'
        cell_list[89-1].value = '=D85-D86+D88'
        cell_list[90-1].value = '=d11'
        jacks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        jacks_date = jacks_date+timedelta(days=1)
        cell_list = jacks_worksheet.range("e1:e90")
        cell_list[1-1].value = jacks_date.strftime("%m/%d/%y")
        cell_list[2-1].value = jacks_date.strftime("%A")
        cell_list[10-1].value = "=SUM(e3:e9)"
        cell_list[12-1].value = "=e11*0.025"
        cell_list[14-1].value = "=e3*0.165"
        cell_list[16-1].value = "=e4*0.27"
        cell_list[18-1].value = "=e5*0.14"
        cell_list[19-1].value = "=e9*0.54"
        cell_list[20-1].value = "=((sum(e3:e5)/1.0825)*0.067)+((sum(e3:e5)/1.0825)*0.0825+sum(e6:e9)*0.0825)"
        cell_list[23-1].value = "=e22*10"
        cell_list[26-1].value = "=e25*2.13"
        cell_list[29-1].value = "=e28*5.5"
        cell_list[32-1].value = "=e31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((jacks_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(e34,e29,e26,e23)*0.165012146"
        cell_list[39-1].value = "=SUM(e12:e20,e23,e26,e29:e38)"
        cell_list[40-1].value = "=if(now()>E1,e10-e39,0)"
        cell_list[45-1].value = "=sum(e43:e44)"
        cell_list[47-1].value = "=DAY(EOMONTH(e1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/E$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/E$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/E$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/E$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/E$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/E$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/E$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/E$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/E$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/E$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/E$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/E$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/E$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/E$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/E$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/E$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/E$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/E$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/E$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/E$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/E$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/E$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/E$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/E$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/E$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/E$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/E$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/E$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/E$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/E$47/2'
        cell_list[81-1].value = '=sum(E49:E79)'
        cell_list[82-1].value = '=if(now()>E1,E40-E81,0)'
        cell_list[89-1].value = '=E85-E86+E88'
        cell_list[90-1].value = '=e11'
        jacks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        jacks_date = jacks_date+timedelta(days=1)
        cell_list = jacks_worksheet.range("f1:f90")
        cell_list[1-1].value = jacks_date.strftime("%m/%d/%y")
        cell_list[2-1].value = jacks_date.strftime("%A")
        cell_list[10-1].value = "=SUM(f3:f9)"
        cell_list[12-1].value = "=f11*0.025"
        cell_list[14-1].value = "=f3*0.165"
        cell_list[16-1].value = "=f4*0.27"
        cell_list[18-1].value = "=f5*0.14"
        cell_list[19-1].value = "=f9*0.54"
        cell_list[20-1].value = "=((sum(f3:f5)/1.0825)*0.067)+((sum(f3:f5)/1.0825)*0.0825+sum(f6:f9)*0.0825)"
        cell_list[23-1].value = "=f22*10"
        cell_list[26-1].value = "=f25*2.13"
        cell_list[29-1].value = "=f28*5.5"
        cell_list[32-1].value = "=f31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((jacks_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(f34,f29,f26,f23)*0.165012146"
        cell_list[39-1].value = "=SUM(f12:f20,f23,f26,f29:f38)"
        cell_list[40-1].value = "=if(now()>F1,f10-f39,0)"
        cell_list[45-1].value = "=sum(f43:f44)"
        cell_list[47-1].value = "=DAY(EOMONTH(f1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/F$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/F$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/F$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/F$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/F$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/F$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/F$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/F$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/F$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/F$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/F$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/F$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/F$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/F$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/F$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/F$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/F$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/F$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/F$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/F$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/F$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/F$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/F$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/F$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/F$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/F$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/F$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/F$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/F$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/F$47/2'
        cell_list[81-1].value = '=sum(F49:F79)'
        cell_list[82-1].value = '=if(now()>F1,F40-F81,0)'
        cell_list[89-1].value = '=F85-F86+F88'
        cell_list[90-1].value = '=f11'
        jacks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        jacks_date = jacks_date+timedelta(days=1)
        cell_list = jacks_worksheet.range("g1:g90")
        cell_list[1-1].value = jacks_date.strftime("%m/%d/%y")
        cell_list[2-1].value = jacks_date.strftime("%A")
        cell_list[10-1].value = "=SUM(g3:g9)"
        cell_list[12-1].value = "=g11*0.025"
        cell_list[14-1].value = "=g3*0.165"
        cell_list[16-1].value = "=g4*0.27"
        cell_list[18-1].value = "=g5*0.14"
        cell_list[19-1].value = "=g9*0.54"
        cell_list[20-1].value = "=((sum(g3:g5)/1.0825)*0.067)+((sum(g3:g5)/1.0825)*0.0825+sum(g6:g9)*0.0825)"
        cell_list[23-1].value = "=g22*10"
        cell_list[26-1].value = "=g25*2.13"
        cell_list[29-1].value = "=g28*5.5"
        cell_list[32-1].value = "=g31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((jacks_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(g34,g29,g26,g23)*0.165012146"
        cell_list[39-1].value = "=SUM(g12:g20,g23,g26,g29:g38)"
        cell_list[40-1].value = "=if(now()>G1,g10-g39,0)"
        cell_list[45-1].value = "=sum(g43:g44)"
        cell_list[47-1].value = "=DAY(EOMONTH(g1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/G$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/G$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/G$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/G$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/G$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/G$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/G$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/G$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/G$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/G$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/G$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/G$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/G$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/G$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/G$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/G$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/G$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/G$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/G$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/G$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/G$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/G$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/G$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/G$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/G$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/G$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/G$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/G$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/G$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/G$47/2'
        cell_list[81-1].value = '=sum(G49:G79)'
        cell_list[82-1].value = '=if(now()>G1,G40-G81,0)'
        cell_list[89-1].value = '=G85-G86+G88'
        cell_list[90-1].value = '=g11'
        jacks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        jacks_date = jacks_date+timedelta(days=1)
        cell_list = jacks_worksheet.range("h1:h90")
        cell_list[1-1].value = jacks_date.strftime("%m/%d/%y")
        cell_list[2-1].value = jacks_date.strftime("%A")
        cell_list[10-1].value = "=SUM(h3:h9)"
        cell_list[12-1].value = "=h11*0.025"
        cell_list[14-1].value = "=h3*0.165"
        cell_list[16-1].value = "=h4*0.27"
        cell_list[18-1].value = "=h5*0.14"
        cell_list[19-1].value = "=h9*0.54"
        cell_list[20-1].value = "=((sum(h3:h5)/1.0825)*0.067)+((sum(h3:h5)/1.0825)*0.0825+sum(h6:h9)*0.0825)"
        cell_list[23-1].value = "=h22*10"
        cell_list[26-1].value = "=h25*2.13"
        cell_list[29-1].value = "=h28*5.5"
        cell_list[32-1].value = "=h31*8"
        cell_list[34-1].value = "=3000/%d/2"%int((jacks_date + dateutil.relativedelta.relativedelta(day=1, months=+1, days=-1)).strftime("%d"))
        cell_list[36-1].value = "=sum(h34,h29,h26,h23)*0.165012146"
        cell_list[39-1].value = "=SUM(h12:h20,h23,h26,h29:h38)"
        cell_list[40-1].value = "=if(now()>H1,h10-h39,0)"
        cell_list[45-1].value = "=sum(h43:h44)"
        cell_list[47-1].value = "=DAY(EOMONTH(h1,0))"
        cell_list[49-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D33"))/H$47/2'
        cell_list[50-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D34"))/H$47/2'
        cell_list[51-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D35"))/H$47/2'
        cell_list[52-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D36"))/H$47/2'
        cell_list[53-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D37"))/H$47/2'
        cell_list[54-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D38"))/H$47/2'
        cell_list[55-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D39"))/H$47/2'
        cell_list[56-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D40"))/H$47/2'
        cell_list[57-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D41"))/H$47/2'
        cell_list[58-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D42"))/H$47/2'
        cell_list[59-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D43"))/H$47/2'
        cell_list[60-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D44"))/H$47/2'
        cell_list[61-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D45"))/H$47/2'
        cell_list[62-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D46"))/H$47/2'
        cell_list[63-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D47"))/H$47/2'
        cell_list[64-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D48"))/H$47/2'
        cell_list[65-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D49"))/H$47/2'
        cell_list[66-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D50"))/H$47/2'
        cell_list[67-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D52"))/H$47/2'
        cell_list[68-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D53"))/H$47/2'
        cell_list[69-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D55"))/H$47/2'
        cell_list[70-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D57"))/H$47/2'
        cell_list[71-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D58"))/H$47/2'
        cell_list[72-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D60"))/H$47/2'
        cell_list[73-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D61"))/H$47/2'
        cell_list[74-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D62"))/H$47/2'
        cell_list[75-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D64"))/H$47/2'
        cell_list[76-1].value = ''
        cell_list[77-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D67"))/H$47/2'
        cell_list[78-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D68"))/H$47/2'
        cell_list[79-1].value = '=sum(IMPORTRANGE("1L5LdMeXzuDRNroMm1syTOOB9pmO3UdPnu51dflsf5dc","Profit and Loss!D69"))/H$47/2'
        cell_list[81-1].value = '=sum(H49:H79)'
        cell_list[82-1].value = '=if(now()>H1,H40-H81,0)'
        cell_list[89-1].value = '=H85-H86+H88'
        cell_list[90-1].value = '=h11'
        jacks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        cell_list = jacks_worksheet.range("i1:i90")
        cell_list[2-1].value = "Week"
        cell_list[3-1].value = "=sum(B3:H3)"
        cell_list[4-1].value = "=sum(B4:H4)"
        cell_list[5-1].value = "=sum(B5:H5)"
        cell_list[6-1].value = "=sum(B6:H6)"
        cell_list[7-1].value = "=sum(B7:H7)"
        cell_list[8-1].value = "=sum(B8:H8)"
        cell_list[9-1].value = "=sum(B9:H9)"
        cell_list[10-1].value = "=sum(B10:H10)"
        cell_list[11-1].value = "=sum(B11:H11)"
        cell_list[12-1].value = "=sum(B12:H12)"
        cell_list[14-1].value = "=sum(B14:H14)"
        cell_list[16-1].value = "=sum(B16:H16)"
        cell_list[18-1].value = "=sum(B18:H18)"
        cell_list[19-1].value = "=sum(B19:H19)"
        cell_list[20-1].value = "=sum(B20:H20)"
        cell_list[22-1].value = "=sum(B22:H22)"
        cell_list[23-1].value = "=sum(B23:H23)"
        cell_list[25-1].value = "=sum(B25:H25)"
        cell_list[26-1].value = "=sum(B26:H26)"
        cell_list[28-1].value = "=sum(B28:H28)"
        cell_list[29-1].value = "=sum(B29:H29)"
        cell_list[31-1].value = "=sum(B31:H31)"
        cell_list[32-1].value = "=sum(B32:H32)"
        cell_list[34-1].value = "=sum(B34:H34)"
        cell_list[36-1].value = "=sum(B36:H36)"
        cell_list[38-1].value = "=sum(B38:H38)"
        cell_list[39-1].value = "=sum(B39:H39)"
        cell_list[40-1].value = "=sum(B40:H40)"
        cell_list[43-1].value = "=sum(B43:H43)"
        cell_list[44-1].value = "=sum(B44:H44)"
        cell_list[45-1].value = "=sum(B45:H45)"
        cell_list[49-1].value = "=sum(B49:H49)"
        cell_list[50-1].value = "=sum(B50:H50)"
        cell_list[51-1].value = "=sum(B51:H51)"
        cell_list[52-1].value = "=sum(B52:H52)"
        cell_list[53-1].value = "=sum(B53:H53)"
        cell_list[54-1].value = "=sum(B54:H54)"
        cell_list[55-1].value = "=sum(B55:H55)"
        cell_list[56-1].value = "=sum(B56:H56)"
        cell_list[57-1].value = "=sum(B57:H57)"
        cell_list[58-1].value = "=sum(B58:H58)"
        cell_list[59-1].value = "=sum(B59:H59)"
        cell_list[60-1].value = "=sum(B60:H60)"
        cell_list[61-1].value = "=sum(B61:H61)"
        cell_list[62-1].value = "=sum(B62:H62)"
        cell_list[63-1].value = "=sum(B63:H63)"
        cell_list[64-1].value = "=sum(B64:H64)"
        cell_list[65-1].value = "=sum(B65:H65)"
        cell_list[66-1].value = "=sum(B66:H66)"
        cell_list[67-1].value = "=sum(B67:H67)"
        cell_list[68-1].value = "=sum(B68:H68)"
        cell_list[69-1].value = "=sum(B69:H69)"
        cell_list[70-1].value = "=sum(B70:H70)"
        cell_list[71-1].value = "=sum(B71:H71)"
        cell_list[72-1].value = "=sum(B72:H72)"
        cell_list[73-1].value = "=sum(B73:H73)"
        cell_list[74-1].value = "=sum(B74:H74)"
        cell_list[75-1].value = "=sum(B75:H75)"
        cell_list[76-1].value = "=sum(B76:H76)"
        cell_list[77-1].value = "=sum(B77:H77)"
        cell_list[78-1].value = "=sum(B78:H78)"
        cell_list[79-1].value = "=sum(B79:H79)"
        cell_list[81-1].value = "=sum(B81:H81)"
        cell_list[82-1].value = "=sum(B82:H82)"
        cell_list[89-1].value = "=sum(B89:H89)"
        cell_list[90-1].value = "=sum(B90:H90)"
        jacks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        ###CHECKS###
        print "[%s]: Populating Checks worksheet"%print_date
        checks_worksheet = sheet.add_worksheet("Checks Written",100,12)
        checks_worksheet.update_cell(1,1,"Checks:")
        cell_list = checks_worksheet.range("a2:h2")
        cell_list[1-1].value = "Date Written"
        cell_list[2-1].value = "Check #"
        cell_list[3-1].value = "Payee"
        cell_list[4-1].value = "Amount"
        cell_list[5-1].value = "Date Cashed"
        cell_list[6-1].value = "Notes"
        checks_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 4

        ###DEBITS###
        print "[%s]: Populating Debits worksheet"%print_date
        debits_worksheet = sheet.add_worksheet("Debit Card Charges",50,12)
        cell_list = debits_worksheet.range("a2:h2")
        debits_worksheet.update_cell(1,1,"Debits:")
        cell_list[1-1].value = "Date"
        cell_list[2-1].value = "Payee"
        cell_list[3-1].value = "Amount"
        cell_list[4-1].value = "Notes"
        debits_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 4

        ###OVERVIEW###
        print "[%s]: Populating Overview worksheet"%print_date
        cell_list = overview_worksheet.range("a1:a9")
        cell_list[2-1].value = "Bank Account(Start of week):"
        cell_list[3-1].value = "Thurs/Fri/Sat Credit cards:"
        cell_list[4-1].value = "Thurs/Fri/Sat Cash:"
        cell_list[5-1].value = "Real balance:"
        cell_list[6-1].value = "Net Profit:"
        cell_list[7-1].value = "Gross Revenue:"
        cell_list[8-1].value = "Opportunity costs:"
        overview_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        CALLS += 2

        cell_list = overview_worksheet.range("b1:b9")
        tfs_credit = '=sum(IMPORTRANGE("%s","San Jac!F90:H90"))+sum(IMPORTRANGE("%s","Jack'%(last_week_sheet_id,last_week_sheet_id)
        tfs_credit+= "'"+'s!F90:H90"))'
        cell_list[3-1].value = tfs_credit
        tfs_cash = '=sum(IMPORTRANGE("%s","San Jac!F89:H89"))+sum(IMPORTRANGE("%s","Jack'%(last_week_sheet_id,last_week_sheet_id)
        tfs_cash+= "'"+'s!F89:H89"))'
        cell_list[4-1].value = tfs_cash
        balance = "=sum(B2:B4)+sum('San Jac'!I89:I90)+sum('Jack''s'!I89:I90)-sum('Checks Written'!D3:D90)-sum('Debit Card Charges'!C3:C90)"
        cell_list[5-1].value = balance
        net_profit = "=sumif('San Jac'!B3:H3,"+'">0"'+",'San Jac'!B82:H82)+sumif('Jack''s'!B3:H3,"+'">0"'+",'Jack''s'!B82:H82)"
        cell_list[6-1].value = net_profit
        cell_list[7-1].value = "=sum('San Jac'!I10)+sum('Jack''s'!I10)"
        cell_list[8-1].value = "=sum('San Jac'!I45)+sum('Jack''s'!I45)"
        overview_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        overview_worksheet.update_title("Overview")
        CALLS += 3

        cell_list = overview_worksheet.range("c1:c9")
        cell_list[8-1].value = "=b8/b7"
        overview_worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')
        overview_worksheet.update_title("Overview")

        format_cell_ranges(overview_worksheet,[("A2:A8",bold),
                                            ("B2:B8",currency),
                                            ("C8",percent)])

        format_cell_ranges(san_jac_worksheet, [("A3:A48",bold),
                                                ("A81:A90",bold),
                                                ("B1:I1",bold),
                                                ("B2:I2",heading),
                                                ("B3:I20",currency),
                                                ("B10:I10",calculated_currency),
                                                ("B23:I23",currency),
                                                ("B26:I26",currency),
                                                ("B29:I29",currency),
                                                ("B32:I45",currency),
                                                ("B39:I39",calculated_currency),
                                                ("B40:I40",calculated_currency),
                                                ("B49:I90",currency),
                                                ("B81:I81",calculated_currency),
                                                ("B82:I82",calculated_currency),
                                                ("B89:I89",calculated_currency),
                                                ("B90:I90",calculated_currency)])

        format_cell_ranges(jacks_worksheet, [("A3:A48",bold),
                                                ("A81:A90",bold),
                                                ("B1:I1",bold),
                                                ("B2:I2",heading),
                                                ("B3:I20",currency),
                                                ("B10:I10",calculated_currency),
                                                ("B23:I23",currency),
                                                ("B26:I26",currency),
                                                ("B29:I29",currency),
                                                ("B32:I45",currency),
                                                ("B39:I39",calculated_currency),
                                                ("B40:I40",calculated_currency),
                                                ("B49:I90",currency),
                                                ("B81:I81",calculated_currency),
                                                ("B82:I82",calculated_currency),
                                                ("B89:I89",calculated_currency),
                                                ("B90:I90",calculated_currency)])

        format_cell_ranges(checks_worksheet, [("A1",bold),
                                                ("A2:F2",heading),
                                                ("A3:A70",bold),
                                                ("D3:D70",currency)])

        format_cell_ranges(debits_worksheet, [("A1",bold),
                                                ("A2:F2",heading),
                                                ("A3:A70",bold),
                                                ("C3:C70",currency)])
    except:
        print "Error finishing %s-SplitLevel_Operations_Week"%date.strftime("%m%d%y")
        time.sleep(20)
        CALLS = 0
        delete_google_spreadsheet(sheet.id)
        return build_weekly_sheet(date)
    return sheet

def build_month_sheet(date=False):
    global CALLS
    if not date:date = datetime.today()
    first_day = date + dateutil.relativedelta.relativedelta(months=1)
    first_day = first_day.replace(day=1)

    day_of_week = first_day.strftime('%A').lower()

    if 'sunday' not in day_of_week:
        last_month = int((first_day + timedelta(days=-1)).strftime("%m"))
        first_spreadsheet = last_spreadsheet_of_month(last_month)
    else:first_spreadsheet = build_weekly_sheet(first_day)

    first_spreadsheet_letter = first_day_of_month(date,first_spreadsheet=first_spreadsheet)

    try:last_year_total = last_year_sales(month=first_day.strftime("%B-%Y"))
    except: last_year_total = 0

    ###WEEKLY SHEETS###
    weekly_sheets = {}
    if first_spreadsheet_letter.lower() != 'h':weekly_sheets[first_spreadsheet.id] = [first_spreadsheet_letter,'H']
    else:weekly_sheets[first_spreadsheet.id] = [first_spreadsheet_letter]

    next_week = (first_day + dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.SU(-1)))+ timedelta(days=7)
    print "Creating weekly sheets"
    while next_week:
        print "Calls: ",CALLS
        if next_week < (first_day + dateutil.relativedelta.relativedelta(months=1)):
            sheet = build_weekly_sheet(next_week)
            if (next_week + timedelta(days=7)) < (first_day + dateutil.relativedelta.relativedelta(months=1)):
                weekly_sheets[sheet.id] = ['I']
                next_week = next_week + timedelta(days=7)
            else:
                last_day_letter = last_day_of_month(next_week,last_spreadsheet=sheet)
                if last_day_letter.lower() == 'b': weekly_sheets[sheet.id] = ['B']
                else: weekly_sheets[sheet.id] = ['B',last_day_letter]
                next_week = False
        else: next_week = False
    print "Creating Month worksheet: %s"%first_day.strftime("%B-%Y")
    sheet = create_google_spreadsheet("%s"%first_day.strftime("%B-%Y"))
    CALLS += 1

    print "Populating Month Overview"
    wsheet = sheet.sheet1
    cell_list = wsheet.range("a1:a25")
    cell_list[1-1].value = "Gross Sales: San Jac"
    cell_list[2-1].value = "Gross Sales: Jack's"
    cell_list[3-1].value = "Net Profit: San Jac"
    cell_list[4-1].value = "Net Profit: Jack's"
    cell_list[5-1].value = "Opp Cost: San Jac"
    cell_list[6-1].value = "Opp Cost: Jack's"
    cell_list[8-1].value = "Gross Sales"
    cell_list[9-1].value = "Net Profit"
    cell_list[10-1].value = "Opp Cost"
    cell_list[12-1].value = "Merch Sales:"
    cell_list[14-1].value = "Entertainment Cost"
    cell_list[15-1].value = "Last year"
    cell_list[16-1].value = "Goal"
    cell_list[17-1].value = "Days left"
    cell_list[18-1].value = "Required sales per day"
    wsheet.update_cells(cell_list, value_input_option='USER_ENTERED')
    CALLS += 3

    format_cell_ranges(wsheet,[("A1:A18",bold),
                                            ("B1:B16",currency),
                                            ("B18",currency),
                                            ("C10",percent)])

    gs_sjs = '='
    gs_jacks = '='
    np_sjs = '='
    np_jacks = '='
    oc_sjs = '='
    oc_jacks = '='
    merch= '='
    entertainment = '='

    for sheet_id in weekly_sheets.keys():
        if len(weekly_sheets[sheet_id]) > 1:
            gs_sjs += '+sum(IMPORTRANGE("%s","San Jac!%s10:%s10"))'%(sheet_id,weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            gs_jacks += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s10:%s10"))'%(weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            np_sjs += '+sum(IMPORTRANGE("%s","San Jac!%s82:%s82"))'%(sheet_id,weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            np_jacks += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s82:%s82"))'%(weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            oc_sjs += '+sum(IMPORTRANGE("%s","San Jac!%s45:%s45"))'%(sheet_id,weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            oc_jacks += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s45:%s45"))'%(weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            merch += '+sum(IMPORTRANGE("%s","San Jac!%s9:%s9"))'%(sheet_id,weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            merch += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s9:%s9"))'%(weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            entertainment += '+sum(IMPORTRANGE("%s","San Jac!%s38:%s38"))'%(sheet_id,weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
            entertainment += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s38:%s38"))'%(weekly_sheets[sheet_id][0],weekly_sheets[sheet_id][1])
        else:
            gs_sjs += '+sum(IMPORTRANGE("%s","San Jac!%s10"))'%(sheet_id,weekly_sheets[sheet_id][0])
            gs_jacks += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s10"))'%(weekly_sheets[sheet_id][0])
            np_sjs += '+sum(IMPORTRANGE("%s","San Jac!%s82"))'%(sheet_id,weekly_sheets[sheet_id][0])
            np_jacks += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s82"))'%(weekly_sheets[sheet_id][0])
            oc_sjs += '+sum(IMPORTRANGE("%s","San Jac!%s45"))'%(sheet_id,weekly_sheets[sheet_id][0])
            oc_jacks += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s45"))'%(weekly_sheets[sheet_id][0])
            merch += '+sum(IMPORTRANGE("%s","San Jac!%s9"))'%(sheet_id,weekly_sheets[sheet_id][0])
            merch += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s9"))'%(weekly_sheets[sheet_id][0])
            entertainment += '+sum(IMPORTRANGE("%s","San Jac!%s38"))'%(sheet_id,weekly_sheets[sheet_id][0])
            entertainment += '+sum(IMPORTRANGE("%s","Jack'%sheet_id+"'"+'s!%s38"))'%(weekly_sheets[sheet_id][0])

    cell_list = wsheet.range("b1:b25")
    cell_list[1-1].value = gs_sjs
    cell_list[2-1].value = gs_jacks
    cell_list[3-1].value = np_sjs
    cell_list[4-1].value = np_jacks
    cell_list[5-1].value = oc_sjs
    cell_list[6-1].value = oc_jacks
    cell_list[8-1].value = "=sum(B1:B2)"
    cell_list[9-1].value = "=sum(B3:B4)"
    cell_list[10-1].value = "=sum(B5:B6)"
    cell_list[12-1].value = merch
    cell_list[14-1].value = entertainment
    cell_list[15-1].value = last_year_total
    cell_list[16-1].value = "=B15*1.1"
    cell_list[17-1].value = "=ifs(today()<date(%d,%d,1),day(EOMONTH(date(%d,%d,1),0)),today()>=date(%d,%d,1),0,today()<date(%d,%d,1),day(EOMONTH(date(%d,%d,1),0))-day(today()))"%(int(first_day.strftime("%Y")),int(first_day.strftime("%m")),int(first_day.strftime("%Y")),int(first_day.strftime("%m")),int((first_day+dateutil.relativedelta.relativedelta(months=1)).strftime("%Y")),int((first_day+dateutil.relativedelta.relativedelta(months=1)).strftime("%m")),int((first_day+dateutil.relativedelta.relativedelta(months=1)).strftime("%Y")),int((first_day+dateutil.relativedelta.relativedelta(months=1)).strftime("%m")),int(first_day.strftime("%Y")),int(first_day.strftime("%m")))
    cell_list[18-1].value = "=(B16-B8)/B17"
    wsheet.update_cells(cell_list, value_input_option='USER_ENTERED')
    CALLS += 2
    print "Calls: ",CALLS

    update_annual_sheet(first_day.strftime("%Y"))

def main():
    """Shows basic usage of the Sheets API.

    Creates a Sheets API service object and prints the names and majors of
    students in a sample spreadsheet:
    https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)
    """

    #date = datetime.today()
    #date = date.replace(day=25)
    #new_sheet = build_weekly_sheet(parent_folder_id,date)
    #sunday = last_sunday_of_month(int(date.strftime("%m")))
    #build_month_sheet()



if __name__ == '__main__':
    main()
