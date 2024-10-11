import os
from pathlib import Path
from cloudflare import Cloudflare
import tomllib


class CFzone:
    """ CloudFlare dns zone """

    def __init__(self, cf_domain, ):

        api_email = os.environ.get('CLOUDFLARE_EMAIL')
        api_key = os.environ.get('CLOUDFLARE_API_KEY')
        api_token = os.environ.get('CLOUDFLARE_API_TOKEN')
        cf_file = Path('.cloudflare.cf')
        if (not cf_file.exists()):
            cf_file = Path.home().joinpath(cf_file)
        if (cf_file.exists()):
            with open(cf_file, 'rb') as f:
                auth_data = tomllib.load(f)
                if ('CloudFlare' in auth_data):
                    api_email = auth_data['CloudFlare'].get('email', None)
                    api_key = auth_data['CloudFlare'].get('api_key', None)
                    api_token = auth_data['CloudFlare'].get('api_token', None)

        self._domain = cf_domain
        self._cf = Cloudflare(api_email=api_email, api_key=api_key, api_token=api_token)

        zone_info = self.get_zoneid(cf_domain)
        if not zone_info:
            emes = f'Can\'t Find a CloudFlare zone for {cf_domain}'
            raise Exception(emes)
        self.zoneid = zone_info.id
        self.zonename = zone_info.name


    def get_zoneid(self,fqdn):
        """ From the fqdn find the CloudFlare zone id """

        fparts = fqdn.split('.')
        while(fparts):
            r = self._cf.zones.list(match='all', name='.'.join(fparts))
            if r and len(r.result) == 1:
                return r.result[0]
            fparts = fparts[1:]
        return None        


    def create(self,params):
        """ Add a record, return the record id """

        r = self._cf.dns.records.create(zone_id=self.zoneid, **params)
        return r.id


    def get(self,params={}):
        """ Get a resouce record """

        r = self._cf.dns.records.list(zone_id=self.zoneid, **params)
        return r


    def getid(self,params={}):
        """ Return a specific resource record values: id, proxied, ttl """

        r = self.get(params)
        recs = 0 if (not r) else len(r.result)
        if recs == 1:
            rr = r.result[0]
            return rr.id, rr.proxied, rr.ttl
        elif recs == 0:
            return 0, False, 0
        else:
            raise Exception('Multiple records found') 


    def set(self,rid,params={}):
        """ Set (update) a specific record id """

        r = self._cf.dns.records.update(dns_record_id=rid, zone_id=self.zoneid, **params)

        return r.id


    def delete(self,rid):
        """ Delete a DNS record """

        r = self._cf.zones.dns_records.delete(dns_record_id=rid, zone_id=self.zoneid)
        return r.id



class CFrec:
    """ CloudFlare DNS record abstraction """
    
    def __init__(self, domain, type='A', ttl=1):

        self.type = type
        self.ttl = ttl
        self.zone = CFzone(domain)
        self.zonename = self.zone.zonename


    def update(self, name, contents, addok=False):
        """ set (update or create) resource record value """

        fqdn = name if name.endswith(self.zonename) else f'{name}.{self.zonename}'

        rid, proxied, ttl = self.zone.getid({'name':fqdn,'type': self.type, 'match': 'all'})
        if rid:
            # update the existing resource record
            return self.zone.set(rid, {
                'name': fqdn, 
                'type': self.type, 
                'proxied': proxied, 
                'ttl' : ttl, 
                'content': contents
                }
            )
        elif addok:
            # rr doesn't exist be we can create a new record
            return self.zone.create({
                'name': fqdn, 
                'type': self.type,
                'ttl' : self.ttl,
                'content': contents
                }
            )
        else:
            # resource record doesn't exist
            return None
    

    def add(self, name, contents):
        """ Add a new record """

        fqdn = name if name.endswith(self.zonename) else f'{name}.{self.zonename}'

        return self.zone.create({'name': fqdn, 'type': self.type, 'content': contents})
        

    def get(self, name):
        """ get contents (value) of a resource record """

        fqdn = name if name.endswith(self.zonename) else f'{name}.{self.zonename}'

        r =  self.zone.get({'name': fqdn, 'type': self.type, 'match': 'all'})

        recs = len(r)
        if recs == 1:
            return r[0]['content']
        elif recs == 0:
            return None
        else:
            raise Exception("Multiple records found")


    def rem(self, name):
        """ remove a TXT record """

        fqdn = name if name.endswith(self.zonename) else f'{name}.{self.zonename}'

        rid, _, _ = self.zone.getid({'name':fqdn,'type': self.type, 'match': 'all'})
        if rid:
            # remove the record
            return self.zone.delete(rid)
        else:
            # couldn't find the record
            return False
    

class TXTrec(CFrec):
    """ CF TXT Record """

    def __init__(self, domain):
        
        super().__init__(domain, 'TXT')
    
