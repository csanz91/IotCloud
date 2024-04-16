# OVH DynHost client for Docker

Docker container to automatically update DynHost records with your public IP address, for [OVH](https://www.ovh.com/world/domains/dns_management_service.xml) DNS.

## Usage

1 - [Create a DynHost user and configure a dynamic DNS record](https://help.ovhcloud.com/csm/en-ie-dns-dynhost?id=kb_article_view&sysparm_article=KB0051641) for the domain of your choice.

2 - Using information from the previous step, run DynHost client container to continuously update your DNS record.

### Using docker compose.

```yaml
version: "3"

services:
  dynhost-updater:
    image: pbe-axelor/ovh-dynhost-updater
    environment:
      HOSTNAME: "<host>.<domain>"
      IDENTIFIER: "<domain>-<suffix>"
      PASSWORD: "<password>"
      LOG_LEVEL: "debug"
```

### Environment variables

|Variable|Description|Is required?|Default|
|-|-|-|-|
|HOSTNAME|Subdomain on which DNS record must be updated dynamically. Multiple hostnames can be set using `;` separator.|**Yes**|-|
|IDENTIFIER|DynHost management username.|**Yes**|-|
|PASSWORD|DynHost management password.|**Yes**|-|
|LOG_LEVEL|String used to configure verbosity (must be one of: 'debug', 'info', 'error')|No|info|
