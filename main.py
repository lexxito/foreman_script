import json
import requests
import yaml
from bs4 import BeautifulSoup
import logging


f = open('data.yaml')
data_file = yaml.safe_load(f)
f.close()

file = open('PXE.txt')
data_f = file.read()
file.close()

headers = {'Content-type': 'application/json'}
safe_headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
operating_system_map = {'Ubuntu': {'os': {
    'templates': ['Preseed Default', 'Preseed Default Finish', 'Preseed default PXElinux'],
    'ptables': ['Ubuntu default']}, 'templates': {'name': 'PXE Default File', 'kind': 1}}}


def main():
    LoggingLevel = logging.WARNING
    logging.basicConfig(level=LoggingLevel)
    log = logging.getLogger('main')
    log.setLevel(logging.DEBUG)
    try:
        requests.get('http://' + data_file['ip'] + '/?format=json')
        log.info('connect to ' + data_file['ip'])
    except IOError:
        log.error('Can not connect to ' + data_file['ip'])
        exit()
    port = data_file['proxy_address'].split(':')[2]
    id_proxy = create_smart_proxie(log)
    id_domain = create_domain(log, id_proxy)
    networks = get_subnets(log, port)
    for count in range(len(networks)):
        create_subnet(log, count, networks[count]['network'], networks[count]['netmask'], id_domain, id_proxy)
    id_arch = create_architecture(log)
    id_media = create_media(log)
    id_os = create_operating_system(log, id_arch, id_media)
    templates_for_operating_system(log, id_os)
    change_template_for_pxe(log)
    import_puppets(log, id_proxy)


def get_address(address):
    return 'http://' + data_file['ip'] + '/' + address + '/?format=json'


def check_errors(log, r):
    if 'errors' in r.text and not 'has already been taken' in r.text:
        for error in json.loads(r.text)['errors']:
            log.error(error)
        exit()
    elif 'has already been taken' in r.text:
        log.warning(json.loads(r.text)['errors'][0])


def create_smart_proxie(log):
    #smart proxy
    log.info('Smart proxy configurations...')
    smart_proxy = {'smart_proxy': {'name': data_file['proxy_name'], 'url': data_file['proxy_address']}}
    r = requests.post(get_address('smart_proxies'), json.dumps(smart_proxy), headers=headers)
    check_errors(log, r)
    data = requests.get(get_address('smart_proxies'))
    for smart_proxy in json.loads(data.text):
        if smart_proxy['smart_proxy']['name'] == data_file['proxy_name']:
            id_proxy = int(smart_proxy['smart_proxy']['id'])
    return id_proxy


def create_domain(log, id_proxy):
    # domain
    log.info('Domain configurations...')
    domain = {'domain': {'dns_id': id_proxy, 'name': data_file['domain_name']}}
    r = requests.post(get_address('domains'), json.dumps(domain), headers=headers)
    check_errors(log, r)
    data = requests.get(get_address('domains'))
    for domain in json.loads(data.text):
        if domain['domain']['name'] == data_file['domain_name']:
            id_domain = int(domain['domain']['id'])
    return id_domain


def get_subnets(log, port):
    # subnet
    log.info('Subnets configurations...')
    try:
        data = requests.get('https://' + data_file['ip'] + ':' + port + 'dhcp', headers=safe_headers, verify=False)
    except IOError:
        log.error('Can not connect to https://' + data_file['ip'] + ':' + port + 'dhcp')
        exit()
    networks = json.loads(data.text)
    return networks


def create_subnet(log, count, ip, mask, id_domain, id_proxy):
    sub_net = {'subnet': {'name': str(count + 1), 'network': ip,
                          'mask': mask, 'domain_ids': [id_domain],
                          'tftp_id': id_proxy, 'dhcp_id': id_proxy, 'dns_id': id_proxy}}
    r = requests.post(get_address('subnets'), json.dumps(sub_net), headers=headers)
    check_errors(log, r)


def create_architecture(log):
    # architecture
    log.info('Architecture configurations...')
    architecture = {'architecture': {'name': data_file['architecture_name']}}
    r = requests.post(get_address('architectures'), data=json.dumps(architecture), headers=headers)
    check_errors(log, r)
    data = requests.get(get_address('architectures'))
    for arch in json.loads(data.text):
        if arch['architecture']['name'] == data_file['architecture_name']:
            id_arch = int(arch['architecture']['id'])
    return id_arch


def create_media(log):
    # media
    log.info('Media configurations...')
    media = {'medium': {'name': data_file['media_name'], 'path': data_file['media_path']}}
    r = requests.post(get_address('media'), data=json.dumps(media), headers=headers)
    check_errors(log, r)
    data = requests.get(get_address('media'))
    for media in json.loads(data.text):
        if media['medium']['name'] == data_file['media_name']:
            id_media = int(media['medium']['id'])
    return id_media


def check_operating_system(log):
    data = requests.get(get_address('operatingsystems'))
    for os in json.loads(data.text):
        if os['operatingsystem']['name'] == data_file['operating_system']:
            log.warning('Operating system with same name already exist')
            if data_file['create_new_operating_system'] == 'y' or data_file['create_new_operating_system'] == 'n':
                answer = data_file['create_new_operating_system']
            else:
                answer = raw_input('Operating system with same name already exist. Do you want create the new one(yes),'
                                   ' or you want overwrite it(not) y/n ')
            if answer == 'y':
                log.warning('Create the new operating system with same name')
                break
            elif answer == 'n':
                log.warning('Overwriting operating system')
                requests.delete('http://' + data_file['ip'] + '/operatingsystems/' +
                                str(os['operatingsystem']['id']) + '/', headers=headers)
            else:
                print 'Please choose y/n'
                check_operating_system(log)


def create_operating_system(log, id_arch, id_media):
    # operating system
    log.info('Operating System configurations...')
    os_name = data_file['operating_system'].split(' ')[0]
    os_major = data_file['operating_system'].split(' ')[1].split('.')[0]
    os_minor = data_file['operating_system'].split(' ')[1].split('.')[1]
    check_operating_system(log)
    template_ids = []
    ptable_ids = []
    data = requests.get(get_address('config_templates'))
    for temp in json.loads(data.text):
        for name in operating_system_map['Ubuntu']['os']['templates']:
            if temp['config_template']['name'] == name:
                template_ids.append(temp['config_template']['id'])
    data = requests.get(get_address('ptables'))
    for table in json.loads(data.text):
        for name in operating_system_map['Ubuntu']['os']['ptables']:
            if table['ptable']['name'] == name:
                ptable_ids.append(table['ptable']['id'])
    os = {'operatingsystem': {'name': os_name, 'major': os_major, 'minor': os_minor, 'family': data_file['os_family'],
                              'release_name': data_file['os_release'], 'architecture_ids': [id_arch],
                              'ptable_ids': ptable_ids, 'medium_ids': [id_media],
                              'config_template_ids': template_ids,
                              }}
    r = requests.post(get_address('operatingsystems'), data=json.dumps(os), headers=headers)
    check_errors(log, r)
    data = requests.get(get_address('operatingsystems'))
    for os in json.loads(data.text):
        if os['operatingsystem']['name'] == data_file['operating_system']:
            id_os = int(os['operatingsystem']['id'])
    return id_os


def templates_for_operating_system(log, id_os):
    # templates for operating system
    log.info('Templates for operating system configurations...')

    ids = {'kind': [], 'temp': []}
    data = requests.get('http://' + data_file['ip'] + '/operatingsystems/' + str(id_os) + '/')
    for kind in json.loads(data.text)['operatingsystem']['config_templates']:
        ids['kind'].append(kind['config_template']['template_kind']['id'])
        ids['temp'].append(kind['config_template']['id'])
    os = {'operatingsystem': {'os_default_templates_attributes': {}}}
    for id in range(len(ids['kind'])):
        os['operatingsystem']['os_default_templates_attributes'][id] =\
            {'template_kind_id': ids['kind'][id], 'config_template_id': ids['temp'][id]}
    r = requests.put('http://' + data_file['ip'] + '/operatingsystems/' + str(id_os) + '/',
                     data=json.dumps(os), headers=headers)
    check_errors(log, r)


def change_template_for_pxe(log):
    # PXELinux for template
    log.info('PXELinux for template configurations...')
    templates = requests.get(get_address('config_templates'))
    for temp in json.loads(templates.text):
        if temp['config_template']['name'] == operating_system_map['Ubuntu']['templates']['name']:
            id_template = temp['config_template']['id']
    template = {'config_template': {'template': data_f,
                                    'template_kind_id': operating_system_map['Ubuntu']['templates']['kind']}}
    r = requests.put('http://' + data_file['ip'] + '/config_templates/' + str(id_template) + '/',
                     data=json.dumps(template), headers=headers)
    check_errors(log, r)


def import_puppets(log, id_proxy):
    # import puppets
    log.info('import puppets...')
    puppets = requests.get('http://' + data_file['ip'] + '/puppetclasses/import_environments?proxy='
                           + str(id_proxy) + '-' + data_file['proxy_name'])
    soup = BeautifulSoup(puppets.content)
    puppets = soup.findAll(checked="checked")
    if not puppets:
        log.warning('No puppets to add')
    for puppet in puppets:
        data = {puppet['name']: puppet['value']}
        r = requests.post('http://' + data_file['ip'] + '/puppetclasses/obsolete_and_new', data)
        check_errors(log, r)


if __name__ == "__main__":
    main()
