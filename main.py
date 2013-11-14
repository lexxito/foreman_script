import json
import requests
import yaml
from bs4 import BeautifulSoup

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


def get_address(address):
    return 'http://' + data_file['ip'] + '/' + address + '/?format=json'

def main():
    #smart proxy
    print 'Smart proxy configurations...'
    smart_proxy = {'smart_proxy': {'name': data_file['proxy_name'], 'url': data_file['proxy_address']}}
    requests.post(get_address('smart_proxies'), json.dumps(smart_proxy), headers=headers)
    data = requests.get(get_address('smart_proxies'))
    for smart_proxy in json.loads(data.text):
      if smart_proxy['smart_proxy']['name'] == data_file['proxy_name']:
          id_proxy = int(smart_proxy['smart_proxy']['id'])

    # domain
    print 'Domain configurations...'
    domain = {'domain': {'dns_id': id_proxy, 'name': data_file['domain_name']}}
    requests.post(get_address('domains'), json.dumps(domain), headers=headers)
    data = requests.get(get_address('domains'))
    for domain in json.loads(data.text):
     if domain['domain']['name'] == data_file['domain_name']:
         id_domain = int(domain['domain']['id'])

    # subnet
    print 'Subnets configurations...'
    port = data_file['proxy_address'].split(':')[2]
    data = requests.get('https://' + data_file['ip'] + ':' + port + 'dhcp', headers=safe_headers, verify=False)
    networks = json.loads(data.text)
    for count in range(len(networks)):
     sub_net = {'subnet': {'name': str(count + 1), 'network': networks[count]['network'],
                           'mask': networks[count]['netmask'], 'domain_ids': [id_domain],
                           'tftp_id': id_proxy, 'dhcp_id': id_proxy, 'dns_id': id_proxy}}
     requests.post(get_address('subnets'), json.dumps(sub_net), headers=headers)

    # architecture
    print 'Architecture configurations...'
    architecture = {'architecture': {'name': data_file['architecture_name']}}
    requests.post(get_address('architectures'), data=json.dumps(architecture), headers=headers)
    data = requests.get(get_address('architectures'))
    for arch in json.loads(data.text):
     if arch['architecture']['name'] == data_file['architecture_name']:
         id_arch = int(arch['architecture']['id'])

    # media
    print 'Media configurations...'
    media = {'medium': {'name': data_file['media_name'], 'path': data_file['media_path']}}
    requests.post(get_address('media'), data=json.dumps(media), headers=headers)
    data = requests.get(get_address('media'))
    for media in json.loads(data.text):
     if media['medium']['name'] == data_file['media_name']:
         id_media = int(media['medium']['id'])

    # operating system
    print 'Operating System configurations...'
    os_name = data_file['operating_system'].split(' ')[0]
    os_major = data_file['operating_system'].split(' ')[1].split('.')[0]
    os_minor = data_file['operating_system'].split(' ')[1].split('.')[1]
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
    requests.post(get_address('operatingsystems'), data=json.dumps(os), headers=headers)

    # templates for operating system
    print 'Templates for operating system configurations...'
    data = requests.get(get_address('operatingsystems'))
    for os in json.loads(data.text):
     if os['operatingsystem']['name'] == data_file['operating_system']:
         id_os = int(os['operatingsystem']['id'])
    ids = {'kind': [], 'temp': []}
    data = requests.get('http://' + data_file['ip'] + '/operatingsystems/' + str(id_os) + '/')
    for kind in json.loads(data.text)['operatingsystem']['config_templates']:
     ids['kind'].append(kind['config_template']['template_kind']['id'])
     ids['temp'].append(kind['config_template']['id'])
    os = {'operatingsystem': {'os_default_templates_attributes': {}}}
    for id in range(len(ids['kind'])):
     os['operatingsystem']['os_default_templates_attributes'][id] = \
         {'template_kind_id': ids['kind'][id], 'config_template_id': ids['temp'][id]}
    requests.put('http://' + data_file['ip'] + '/operatingsystems/' + str(id_os) + '/',
              data=json.dumps(os), headers=headers)

    # PXELinux for template
    print 'PXELinux for template configurations...'
    templates = requests.get('http://160.85.4.65/config_templates/?format=json')
    for temp in json.loads(templates.text):
     if temp['config_template']['name'] == operating_system_map['Ubuntu']['templates']['name']:
         id_template = temp['config_template']['id']
    template = {'config_template': {'template': data_f,
                                 'template_kind_id': operating_system_map['Ubuntu']['templates']['kind']}}
    requests.put('http://' + data_file['ip'] + '/config_templates/' + str(id_template) + '/',
              data=json.dumps(template), headers=headers)

"""
    # import puppets
    print 'import puppets...'
    puppets = requests.get('http://' + data_file['ip'] + '/puppetclasses/import_environments?proxy='+str(id_proxy)+'-' +
                        data_file['proxy_name'])
    soup = BeautifulSoup(puppets.content)
    dev = soup.find(id="changed_new_development")
    prod = soup.find(id="changed_new_production")
    data = {'changed[new][development]': dev['value'], 'changed[new][production]': prod['value']}
    requests.post('http://' + data_file['ip'] + '/puppetclasses/obsolete_and_new', data)
  """

if __name__ == "__main__":
    main()

"""
for i in range(1400, 1450):
  try:
      requests.delete('http://' + data_file['ip'] + '/puppetclasses/' + str(i) + '/')
  except:
      pass
 """