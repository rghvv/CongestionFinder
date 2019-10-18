'''
   Author:  Raghav Verma
  Created:  May 18, 2019
 Modified:  May 19, 2019
'''


'''
    congestion_finder.py

    This program finds instances of interdomain congestion in the given number of preceeding months between
    network-ASN pairs, and outputs the resulting time period, congestion measurement and visualization links
    to a .xls file in a new directory titled 'congestion' followed by the date and time of the program's
    execution.

    The number of preceeding months the search is conducted on can be changed by altering
    the MONTHS variable. The difference between the start and end dates can be a maximum of 30 days, so the
    final result is constructed by parsing as many queries as there are months.

    The program uses the input to contruct a query for the /asrt method in the MANIC API. The result is parsed
    to find instances of nonzero congestion. It also creates an appropriate URL to the MANIC visualization tool,
    which can be found in the .xls file titled with network name. Each sheet in .xls file refers to an ASN that
    the network is associated with. If no instances of congestion are found, the file is not saved.

    Two visualization links per detected instance of congestion are generated. One link specifies day-level
    granularity and displays the visualization on the day of instance of congestion. The other link specifies
    month level granularity, displaying the visualizaion of the month surrounding the instance (15 days prior
    to and following instance).
    
    The .xls file is manipulated using the xlwt library [pip install xlwt].
    The names of the network-ASN pairs are generated by calling the /monitors method of the MANIC API.
'''


import json
import urllib.request
import urllib
import sys
import pprint
import datetime
import xlwt
from xlwt import Workbook
import time
import os


MONTHS = 60


def get_result(url: str) -> 'json':
    '''
    Returns JSON response at supplied url, or exits program if a HTTP error is encountered.
    '''
    try:
        response = urllib.request.urlopen(url)
        json_text = response.read().decode(encoding = 'utf-8')
        return json.loads(json_text)
    except urllib.error.HTTPError as err:
        if err.code == 500:
            print('Internal Server Error: The server did not respond')
            sys.exit()
        elif err.code == 400:
            print('Parameter Error: Invalid input')
            sys.exit()
        else:
            print('ERROR CODE: ' + str(err.code))
            sys.exit()
    return ""


class JSON_Printer(pprint.PrettyPrinter):
    def format(self, object, context, maxlevels, level) -> None:
        '''
        Prints JSON text in a human-readable format. Useful for debugging.
        
        If type of 'object' is bytes, it will be decoded and subsequently printed using the 'encoding' parameters.

        This is necessary because:
            1. In Python 2, str == bytes.
            2. In Python 3, bytes remains unchanged but str means unicode, while unicode is not defined anymore.
        '''
        if type(object) == bytes:
            return (object.encode('utf8'), True, False)
        return pprint.PrettyPrinter.format(self, object, context, maxlevels, level)


def save_congestion(near_asn: str, far_asn: str, wb: xlwt.Workbook, near_name: str, filename: str,) -> None:
    '''
    Constructs /asrt query and visualization URL and fetches JSON data, before outputting to appropriate .xls file.
    '''

    #Base URLs for both the /asrt API query and visualization tool
    BASE_URL = "https://api.manic.caida.org/v1/asrt"
    VIS_BASE = "https://viz.manic.caida.org/d/cmCi50Umz/all-links-from-vp-network-to-neighbor-network?orgId=2"

    near_url = "?near_org_asn=" + near_asn
    far_url = "&far_asn=" + far_asn

    # Get name of the ASN using the /monitors method
    FAR_MONITOR_URL = "https://api.manic.caida.org/v1/asns/{}?verbose=true".format(far_asn)
    far_name = get_result(FAR_MONITOR_URL)['data']['name']
    print("\n\tNETWORK NAME:\t{}".format(near_name))
    print("\t    ASN NAME:\t{}".format(far_name))
    
    # Get list of dates going back given number of months, each 30 days apart
    times = [datetime.datetime.now()]
    for i in range(MONTHS):
        new_time = times[0] - datetime.timedelta(days = 30)
        times.insert(0, new_time)

    # Creating new sheet in .xls file with appropriate column names
    if far_asn in asns.keys():
        far_name = asns[far_asn]
    sheet1 = wb.add_sheet(far_name)
    sheet1.write(0, 0, 'Time')
    sheet1.write(0, 1, 'Congestion')
    sheet1.write(0, 2, 'Visualization - Day Granularity')
    sheet1.write(0, 3, 'Visualization - Month Granularity')
    # Variables to keep track of index in .xls file
    x_val = 0
    old_x = 0
    for i in range(len(times) - 1):
        
        # Construct /asrt query URL
        start_url = "&start=" + times[i].strftime("%Y") + times[i].strftime("%m") + times[i].strftime("%d")
        end_url = "&end=" + times[i + 1].strftime("%Y") + times[i + 1].strftime("%m") + times[i + 1].strftime("%d")
        QUERY_URL = BASE_URL + near_url + far_url + start_url + end_url + "&is_congested=true"
        json_result = get_result(QUERY_URL)

        network_url = "&var-network=" + near_asn
        asn_url = "&var-asn=" + far_asn

        # Write data to .xls file if applicable
        for data in json_result['data']:
            old_x = x_val
            if data['data'] != []:
                for assertions in data['data']:
                    sheet1.write(x_val + 1, 0, str(assertions['time']))
                    sheet1.write(x_val + 1, 1, str(assertions['congestion']))

                    # Construct MANIC visualization URL for day of instance of congestion and write to .xls file
                    day_granularity = datetime.datetime.strptime(str(assertions['time'])[0:10], '%Y-%m-%d')
                    day_from_url = "&from=" + day_granularity.strftime("%Y") + day_granularity.strftime("%m") + day_granularity.strftime("%d")
                    day_granularity = day_granularity + datetime.timedelta(days = 2)
                    day_to_url = "&to=" + day_granularity.strftime("%Y") + day_granularity.strftime("%m") + day_granularity.strftime("%d")
                    DAY_VIS_QUERY = VIS_BASE + day_from_url + day_to_url + network_url + asn_url
                    sheet1.write(x_val + 1, 2, DAY_VIS_QUERY)

                    # Construct MANIC visualization URL for month surrounding instance of congestion and write to .xls file
                    month_granularity = datetime.datetime.strptime(str(assertions['time'])[0:10], '%Y-%m-%d')
                    month_granularity = month_granularity - datetime.timedelta(days = 15)
                    month_from_url = "&from=" + month_granularity.strftime("%Y") + month_granularity.strftime("%m") + month_granularity.strftime("%d")
                    month_granularity = month_granularity + datetime.timedelta(days = 30)
                    month_to_url = "&to=" + month_granularity.strftime("%Y") + month_granularity.strftime("%m") + month_granularity.strftime("%d")
                    MONTH_VIS_QUERY = VIS_BASE + month_from_url + month_to_url + network_url + asn_url
                    sheet1.write(x_val + 1, 3, MONTH_VIS_QUERY)
                    
                    x_val += 1
                    #print(str(x_val) + ") " + assertions['time'] + "," + str(assertions['congestion']))
            #sheet1.write_merge(old_x + 1, x_val, 2, 2, VIS_QUERY)

        # Uncomment to see full JSON output:
        #JSON_Printer().pprint(json_result)

    # File is not saved if there are no instances of congestion
    if x_val != 0:
        wb.save(filename)
        if x_val == 1:
        	        print("\n\tRESULT: 1 instance of congestion found.")
        else:
        	print("\n\tRESULT: {:,} instances of congestion found.".format(x_val))
    else:
        print("\n\tRESULT: No instances of congestion found.");


if __name__ == '__main__':

    # Set start time
    start = time.time()

    # Make appropriately titled directory
    pathname = 'congestion-' + str(datetime.datetime.now()).replace(" ", "-").replace(":", "-")
    os.mkdir(pathname)
    os.chdir(pathname)

    # Relevant networks and ASNs provided by Prof. Scott Jordan.

    # Dictionary in "ASN":"NAME" format.
    networks = {
        "7018"  :   'AT&T',                 # ATT-INTERNET4
        "209"   :   'CENTURYLINK',          # CENTURYLINK-US-LEGACY-QWEST
        "20115" :   'CHARTER',              # CHARTER-20115
        "7922"  :   'COMCAST',              # COMCAST-7922
        "22773" :   'COX',                  # ASN-CXA-ALL-CCI-22773-RDC
        "6939"  :   'HURRICANE',            # HURRICANE
        "3356"  :   'LEVEL3',               # LEVEL3
        "6079"  :   'RCS',                  # RCN-AS
        "18214" :   'TELUS-INTERNATIONAL',  # TELUS-INTERNATIONAL
        "852"   :   'TELUS-CANADA',         # ASN852
        "7843"  :   'TIME-WARNER-CABLE',    # TWC-7843-BB
        "16115" :   'VERIZON-ASRANK',       # VERIZON-LUNDAIDC-AS
        "701"   :   'VERIZON-MANIC'         # UUNET
    }

    # List of ASNs
    asns = {
        "16509" :   'AMAZON-02',             # AMAZON-02
        "40027" :   'NETFLIX',              # NETFLIX-ASN
        "20940" :   'AKAMAI',               # AKAMAI-ASN1
        "8075"  :   'MICROSOFT',            # MICROSOFT-CORP-MSN-AS-BLOCK
        "174"   :   'CCOGENT'               # COGENT-174
    }
    # Add all keys from networks dictionary (ASNs) to list of ASNs
    for network in networks.keys():
        asns.update({network: networks[network]})

    for network in networks.keys():
        # Set internal execution start time
        start_t = time.time()

        # Get name of the network using the /monitors method
        NEAR_MONITOR_URL = "https://api.manic.caida.org/v1/asns/{}?verbose=true".format(network)
        near_result = get_result(NEAR_MONITOR_URL)
        near_name = near_result['data']['name']

        # Construct filename
        filename = networks[network] + ".xls"

        # Initialize xlwt workbook.
        wb = Workbook()

        # Find congestion between the network and all ASNs from the 'asns' list
        print("\n----------------\n\nORG NAME:\t{}".format(networks[network]))
        for asn in asns:
            print("\n\t----------------")
            save_congestion(network, asn, wb, near_name, filename)

        # Set internal execution end time
        end_t = time.time()
        print("\nExecution time: {} seconds".format(str(round(end_t - start_t, 3))))

    # Set end time
    end = time.time()

    print('\n--------------------------------\n')
    print("\nTotal execution time: {} seconds".format(str(round(end - start, 3))))
