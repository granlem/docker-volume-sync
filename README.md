# docker-volume-sync
## Description:
Automatic distributed sync between volumes on different hosts in docker swarm as alternative to nfs and similar solutions. Good solution if real-time parity is not required and especialy efficient if changes are not that often. E.g. Blogs, Websites, File-Cloud-Systems etc.

## Quick Start:
An easy way to start quickly is by using the docker-compose.yml.
```
wget https://raw.githubusercontent.com/granlem/docker-volume-sync/master/examples/wordpress/docker-compose.yml
docker-compose up
``` 
Then you can access the sychronized Wordpress CMS on each host. You may also use a load balancer like Traefik.

