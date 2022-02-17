# coding=utf-8
import json
from dns.resolver import Resolver
from sender_policy_flattener.crawler import spf2ips
from sender_policy_flattener.formatting import sequence_hash
from sender_policy_flattener.email_utils import email_changes
from .cf_dns import TXTrec

if "FileNotFoundError" not in locals():
    FileNotFoundError = IOError


def flatten(
    input_records,
    dns_servers,
    email_server,
    email_subject,
    update_subject,
    fromaddress,
    toaddress,
    update=False,
    email=True,
    lastresult=None,
    force_update=False
):
    resolver = Resolver()
    if dns_servers:
        resolver.nameservers = dns_servers
    if lastresult is None:
        lastresult = dict()
    current = dict()
    for domain, spf_targets in input_records.items():
        records = spf2ips(spf_targets, domain, resolver)
        hashsum = sequence_hash(records)
        current[domain] = {"sum": hashsum, "records": records}
        if lastresult.get(domain, False) and current.get(domain, False):
            previous_sum = lastresult[domain]["sum"]
            current_sum = current[domain]["sum"]
            mismatch = previous_sum != current_sum
            if mismatch:
                print(f'\n***WARNING: SPF changes detected for sender domain {domain}\n')
            else:
                print(f'\nNO SPF changes detected for sender domain {domain}\n')
        
            if mismatch and email:                
                print(f'Sending mis-match details email for sender domain {domain}')
                if update or force_update:
                    thesubject = update_subject
                else:
                    thesubject = email_subject
                email_changes(
                    zone=domain,
                    prev_addrs=lastresult[domain]["records"],
                    curr_addrs=current[domain]["records"],
                    subject=thesubject,
                    server=email_server,
                    fromaddr=fromaddress,
                    toaddr=toaddress,
                )
            if (mismatch and update) or force_update:
                cfzone = TXTrec(domain)
                numrecs = len(records)
                print(f'\n**** Updating {numrecs} SPF Records for domain {domain}\n')        
                for i in range(0,numrecs):
                    recname = f'spf{i}.{domain}'
                    print(f'===> Updating {recname} TXT record..', end='')
                    if cfzone.update(recname, records[i],addok=True):
                        print(f'..Successfully updated\n')
                    else:
                        print(f'Failed!\n\n********** WARNING: Update of {recname} TXT record Failed\n')
            

    return current if update or force_update or len(lastresult) == 0 else lastresult


def main(args):
    previous_result = None
    try:
        with open(args.output) as prev_hashes:
            previous_result = json.load(prev_hashes)
    except FileNotFoundError as e:
        print(repr(e))
    except Exception as e:
        print(repr(e))
    finally:
        spf = flatten(
            input_records=args.domains,
            lastresult=previous_result,
            dns_servers=args.resolvers,
            email_server=args.mailserver,
            fromaddress=args.fromaddr,
            toaddress=args.toaddr,
            email_subject=args.subject,
            update_subject=args.update_subject,
            update=args.update,
            email=args.sendemail,
            force_update=args.force_update,
        )
        with open(args.output, "w+") as f:
            json.dump(spf, f, indent=4, sort_keys=True)
