import requests
import json
import os.path
from requests.auth import HTTPBasicAuth
from shutil import copyfile
from jinja2 import Template

peeringdb_username = ''
peeringdb_password = ''
ASNtoMatch = '29802'
prefixlimitipv4 = 0
prefixlimitipv6 = 0

if not os.path.isfile('config.json'):
    if os.path.isfile('config.example.json'): copyfile ('config.example.json','config.json')
try:
    with open('config.json') as json_data_file:
        settings = json.load(json_data_file)
        #print(settings['peeringdb_creds'])
        if settings['peeringdb_creds']['username']:
            peeringdb_username = settings['peeringdb_creds']['username']
        else: print('You do not have a peeringdb username configured! We may be unable to get contact information depending on the organizations privacy settings.')
        if settings['peeringdb_creds']['password']: 
            peeringdb_password = settings['peeringdb_creds']['password']
        else: print('You do not have a peeringdb password configured! We may be unable to get contact information depending on the organizations privacy settings.')
        if settings['ASN']: ASNtoMatch = settings['ASN']
except Exception as ex:
        print("Couldn't load configuration file config.json! Details: " + str(ex))

def getIXInfo(id):
    HTTP_OK = 200
    pdb_url = 'https://api.peeringdb.com/api/ix?id__in=%s&depth=2' % id
    #print("Fetching PeeringDB IX info for %s" % id)
    r = requests.get(pdb_url)
    if r.status_code != HTTP_OK:
        print("Got unexpected status code, exiting")
        print("%s - %s" % (r.status, r.text))
        exit(1)
    pdb_res = r.json()
    return pdb_res

def getPeeringDB(ASN):
    HTTP_OK = 200
    pdb_url = 'https://api.peeringdb.com/api/net?asn__in=%s&depth=2' % ASN
    #print("Fetching PeeringDB info for %s" % ASN)
    r = ''
    if peeringdb_username and peeringdb_password: 
        r = requests.get(pdb_url, auth=HTTPBasicAuth(peeringdb_username,peeringdb_password))
        print('Connecting to peeringdb with account ' + peeringdb_username)
    else: r = requests.get(pdb_url)
    if r.status_code != HTTP_OK:
        print("Got unexpected status code, exiting")
        print("%s - %s" % (r.status, r.text))
        exit(1)
    pdb_res = r.json()
    return pdb_res


def intersection(list1,list2):
    returnList = [value for value in list1 if value in list2]
    return returnList

def check_dupes(dict1,dict2):
    dupes = []
    for ix in dict1:
        for ix2 in dict2:
            if ix['ix_id'] == ix2['ix_id']: 
                #print('Peering point found! ID ' + str(ix2['ix_id']))
                #print(dupes)
                in_list = False
                for peer in dupes:
                    if peer['ipaddr4'] == ix2['ipaddr4']: in_list = True
                    if peer['ipaddr6'] == ix2['ipaddr6']: in_list = True
                if not in_list: dupes.append(ix2)
                #dupes.append(ix2)
    #print(str(dupes))
    #print('check_dupes completed')
    #print('dict1 is ' + str(dict1))
    #print('dict2 is ' + str(dict2))
    #print(str(dupes))
    return dupes
valid_ASN = False
while valid_ASN == False:
    ASN = input('Please enter the ASN: ')
    try:
        ASNinfo = getPeeringDB(ASN)['data'][0]
        valid_ASN = True
    except Exception as ex:
        print('Exception occurred looking up ASN! Details: ' + str(ex))
ixs = ASNinfo['netixlan_set']
commands = ''
try:
    ASNdesc = ASNinfo['name']
    ASNdesc = ASNinfo['name'] + ' (' + ASNinfo['poc_set'][0]['email'] + ')'
    prefixlimitipv4 = ASNinfo['info_prefixes4']
    prefixlimitipv6 = ASNinfo['info_prefixes6']

except Exception as ex:
    print('Exception occurred getting contact information! Details: ' + str(ex))
    userInput = input('Continuing may cause configuration generated to be incomplete (likely missing contact information / email addresses). Continue? y / n : ')
    if userInput != 'y':
        exit(1)

MATCH_IX_LIST = getPeeringDB(ASNtoMatch)['data'][0]['netixlan_set']
ixs_in_common = check_dupes(MATCH_IX_LIST,ixs)
#print('Common IXs: ' + str(ixs_in_common))
#print('Converting to friendly names')
for ix in ixs_in_common:
    for IX_NAME in settings['FRIENDLY_IX_NAMES']:
        #print('IX Name: ' + IX_NAME + '\n' + 'IX Friendly Name: ' + settings['FRIENDLY_IX_NAMES'].get(FRIENDLY_NAME))
        #print('Checking for ' + ix['name'] + ', against ' + IX_NAME)
        if ix['name'] == IX_NAME:
            #print('Found matching IX! ' + ix['name'])
            #print(ix)
            ix['name'] = settings['FRIENDLY_IX_NAMES'].get(IX_NAME)

#print('Common IXs: ' + str(ixs_in_common))

#print('Without Dupes: ' + str(list(dict.fromkeys(ixs_in_common))))
for ix in ixs_in_common:
    groupname = ix['name']
    groupipv4 = ix['ipaddr4']
    groupipv6 = ix['ipaddr6']
    f = open('template.j2','r')
    groupFilename = groupname + '-AS' + str(ix['asn']) + '.set'
    groupFile = open(groupFilename,'a+')
    template = Template(f.read()).render(groupname=groupname,groupipv4=groupipv4,groupipv6=groupipv6,asn=ASN,ASNdesc=ASNdesc,prefixlimitipv4=prefixlimitipv4,prefixlimitipv6=prefixlimitipv6)
    commands += template
    groupFile.write(template)
    #groupFile.append(template)
    groupFile.close()
    print('Commands written to file ' + groupFilename + '!')

#print(commands)
f = open('config_full.set','w+')
f.write(commands)
f.close()
print('Commands written to file config_full.set!')
userInput = input('Would you like to view the full commands? ')
if userInput.lower().strip()[0] == 'y': print(commands)
#print('prefixlimitipv4 is ' + str(prefixlimitipv4))
#print('prefixlimitipv6 is ' + str(prefixlimitipv6))
#print(getPeeringDB(ASN))