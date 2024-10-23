Cloudflare SPF Flattener
====================

## Finding sender-policy-flattener (spflat)

A few weeks ago one of our SaaS vendors added a couple of additional DNS entries to their SPF record (without telling us...). 

We started to get reports of email deliver failures. Looking into it we discovered the number of DNS entries in our SPF record was the problem. The SaaS vendors change put us over the maximum of 10. 

We've decided future SaaS vendors and partners will send from a subdomain, but for existing ones there are too many actors - both internal and external to accomplish this change any time soon.

Hence we started researching SPF flattening as the best solution, but were concerned about the vendors making changes to the sender records.

Looking for a solution to that probkem we stumbled upon the [sender-policy-flattener](https://github.com/cetanu/sender_policy_flattener) project.  This tool - `spflat` - solved many problems and has some excellent features and characteristics.  
* The project is opensource
* It will query your list of approved sendors and flatten these into a list of appropriately formatted and sized spf records composed of `ip4` and `ip6` spf entries.
* Provide these entries as a chain of spf `include` entries. 
* Should any of your the senders dns entries change, it sends email indicating the changes and the the corrections required to your spf records. 
* `spflat` works reliably and accurately
* Can run entirely from a JSON configuration file.
* Written in Python, and easy to install and configure.

`sendier-policy-flattner` did ***90%*** of what we desired for flattening and managing our SPF records.

## Requirements that led to this project
After using `splat` for a bit we come up with a wish list - the other ***10%*** of what we needed.

Here is the wishlist of requirements we came up with:
* The ability to run `spflat` in the command line, without the email being sent. (a `--no-email` switch)
* Our public DNS zones are in Cloudflare. We wanted `spflat` to **AUTOMATICALLY** update the necessary resource records in Cloudflare when a  change is detected. (a `--update` switch). 
* Ability to have `spflat` re-create the SPF zone records in Cloudflare DNS for zone repair (and initial configuration.) (a `--force-update` switch)
* Have the output status file (sums file) update ONLY if the zones are updated.
  
  * original `spflat` replaces the sums file each time it ran, so in monitoring mode a change was reported only once.

* `sender-policy-flattener` is a fine tool, so we did not want to reinvent the wheel:
  
  * Utilized `spflat` by supplementing its functionality.
  
  * A supplement, not a replacement.

* Keep the changes opensource:
  * Recognize the debt to `sender-policy-flattener`
  * Make the changes avialable under the same licenses.

  * To limit confusion, change the command from `spflat` to `cfspflat`

Hence `cfspflat` - ***CloudFlare Sender Policy Flattener*** was created.

## `cfspflat` - Cloudflare Sender Policy Flattener

Quick overview:
```bash
% cfspflat -h
usage: cfspflat [-h] [-c CONFIG] [-o OUTPUT] [--update-records] [--force-update]
          [--no-email]

A script that crawls and compacts SPF records into IP networks. This helps to
avoid exceeding the DNS lookup limit of the Sender Policy Framework (SPF)
https://tools.ietf.org/html/rfc7208#section-4.6.4

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Name/path of JSON configuration file (default:
                        spfs.json)
  -o OUTPUT, --output OUTPUT
                        Name/path of output file (default spf_sums.json)
  --update-records      Update SPF records in CloudFlare
  --force-update        Force an update of SPF records in Cloudflare
  --no-email            don't send the email
```
* The `sender-policy-flattener` module is installed as part of `cfspflat`
* The existing core of `spflat` is kept mostly intact, so the basic features are maintained by `cfspflat`.  
* The changes to accomodate `cfspflat` were in the parameter handling and adding the Cloudflare updates to the processing look.
* The `cloudflare` library, with some abstraction classes, is used to make the zone updates.
* `cfspflat` eliminates many of the command arguments of spflat in favor of using the json config file.
* Cloudflare TXT records are automatically generated and updated when the configuration changes.
* With `cfspflat` you can completely automate your SPF flattening using cfspflat with the `--update` switch in a cron job, even silently with the `--no-email` switch

## Installing and Configuring  cfspflat

### 1. pip install the cfspflat
```bash
% pip install cfspflat
```
* But it's advisable to do this in its own venv:
```bash
% python3 -m venv spfenv
% source spfenv/bin/activate
% pip install cfspflat
```
* pip will install the prerequisites, including the `sender-policy-flattner` (spflat), `dnspython`, `netaddr`, and `cloudflare` python modules.
* The executable is installed in bin of the venv as `cfspflat`
### 2. Create an anchor SPF record for the zone apex in Cloudflare

Create the TXT SPF record on zone apex used (e.g. example.com), At the end of this anchor record include the first SPF record that slpat will write - spf0.example.com
 * we also include our own `ip4` and `ip6` entries in this anchor record. 
```
example.com TXT "v=spf1 mx include:spf0.example.com -all"
```
* This anchor record is never changed by `cfspflat`. It's purpose is to link to the first SPF record in the chain that `cfspflat` manages.

### 2. Edit the cfspflat configuration file
Create a spfs.json file.  Add all the entries required:
* `cfspflat` uses the same configuration and sums file formats as the original `spflat`.
* If you already use spflat you can use thos files as is with cfspflat.
* There is one extension - the "update_subject" entry containing the subject of the email sent when cfspflat has updated your SPF records.  This message will contain the same detail spflat provides.
* `spfs.json` is the default name of the config file, but it can be specified with the `--config` switch.
* Here is an example config file:
#### Example spfs.json configuration file:
```json
{
    "sending domains": {
        "example.edu": {
              "amazonses.com": "txt",
              "goodwebsolutions.net": "txt",
              .... more sender spf's here ....
              "delivery.xyz.com": "txt",
              "spf.protection.outlook.com": "txt"
        }
    },
    "resolvers": [
            "1.1.1.1", "8.8.8.8"
    ],
    "email": {
        "to": "dnsadmins@example.com",
        "from": "spf_monitor@example.com",
        "subject": "[WARNING] SPF Records for {zone} have changed and should be updated.",
        "update_subject" : "[NOTICE] SPF Records for {zone} have been updated.",
        "server": "smtp.example.com"
    },
    "output": "monitor_sums.json"
}
```
#### Config file details
* The `sending domains` section is **required** and contains sending domain entries: this is your sender domain (e.g. example.com for j.smith@example.com, noreply.example.com for deals@noreply.example.com )  There can be multiple sending domains in the config file.
* Each sending domain contains dns spf records for the dns `include` records of your approved senders.These dns names are resolved and flattened:
  * These entries are in the key-value pairs of <fqdn> : <record type>.
  * Record type can be "txt" (other SPF records),  "A" and "AAAA" records (for specific hosts).
* The `resolvers` section is **optional** (using the system default DNS resolvers if none are supplied)
* The `email` stanza is **required** and is global (i.e. for all `sending domains`).  This section includes:
  * `subject` **(optional)** is the email subject if a change was detected but no updates were made. The default message is the one shown in the example.
  * `update_subject` **(optional)** is the email subject if a change was detected and the dns records were updated. The default message is shown in the example.
    * `to` - is **required** - this is the destination for emails sent by `cfspflat` 
    * `from` - is **required** - the source email of the messages `cfspflat` sends
    * `server` - is **required** - your mail relay.
* `output` is the file that maintains the existing state and checksum of sender records. If this is not specified `spfs_sum.json` is used.
#### Output file details
* The `output` file is a JSON file only updated if it is new (empty) or the records have been updated. 
* Likewise the default output file is `spf_sums.json` but can be changed in the config file or by the `--output` switch.
* This contains the list of flattened spf records and a checksum used to assess changes in senders records. 
* Because you recieve emails of detected changes or updates, there is little reason to care about the output file.
### 3. Create a credentials file for Cloudflare
There are a couple of locations and formats for the API credentials Cloudfare requires.
* Consult cloudflare documentation and the dashboard for creating API credentials
* Consult the python-cloudflare site for documentation on passing credentials.
* For simplicity you can use the `.cloudflare.cfg` file in either your home directory or in the directory you will run cfspflat.
```
[CloudFlare]
email = "dnsadmin@example.org"
api_key = "1234567890abc...abc"
# or alternatively you can use a API token
api_token = "your-generated..API-token"
```
* It should go without saying - protect the API keys and this file.
* It's also possible to pass the credentials as environment variables (`CLOUDFLARE_EMAIL`, `CLOUDFLARE_API_KEY`, `CLOUDFLARE_API_TOKEN`).

### 4. Run `cfspflat` to build the sums file and SPF entries
* Run cfspflat twice:
```bash
% cfspflat --no-email
% cfspflat --force 
```
* The first time constructs the base records and the second time forces the dns updates.
* With force update the DNS records are created even if a change hasn't been detected.
* A list of the records will be sent to your email.

### 5. Automate `cfspflat` to the level you are comfortable with
* You are up and running:
  * You can run `cfspflat` in advisory mode (like `spflat`) sending you emails notifying of changes
  * Or you can run it with the `--update-records` switch and update your records automatically whenever they change (still giving you notifications of the changes made.)

Example email format
--------------------
* Example from `sender-policy-flattener` README:

<img src='https://raw.githubusercontent.com/cetanu/sender_policy_flattener/master/example/email_example.png' alt='example screenshot'></img>
