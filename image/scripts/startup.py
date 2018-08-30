#!/usr/bin/env python3

import socket
import os
import struct
import logging
import subprocess
import shlex
import shutil
import time
import sys

# Application constants
DEV_NULL = open(os.devnull, 'w')
SYNC_TYPES = ["NEXT", "FIRST", "ALL"]
SYNC_SERVER_PORT = 2222
SYNC_SERVER = ["unison","-socket", str(SYNC_SERVER_PORT)]
SYNC_CLIENT = ["unison", "-auto", "-batch","-fastcheck",\
               "-group","-owner","-prefer=newer","-silent",\
               "-times","-confirmbigdel=false", "-confirmmerge=false"]
# Pre setting
if os.getenv('DEBUG'):
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Debugging log level is enabled")
else:
    logging.basicConfig(level=logging.INFO)

# Application environments
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', "0")) # MAX interval in seconds
SYNC_TIMEOUT = int(os.getenv('SYNC_TIMEOUT', -1))
if SYNC_TIMEOUT < 0:
    SYNC_TIMEOUT = None
HOSTNAME_GROUP = os.getenv('HOSTNAME', 'sync')
SYNC_TYPE = os.getenv('SYNC_TYPE', SYNC_TYPES[0]).upper() # Sync type for distributed sync
if not SYNC_TYPE in SYNC_TYPES:
    logging.info("%s is no valid sync type. Set to default %s" % (SYNC_TYPE, SYNC_TYPE[0]))
    SYNC_TYPE = SYNC_TYPES[0]
WAIT_BEFORE_SYNC = int(os.getenv('WAIT_BEFORE_SYNC', "10")) # Wait before servers are ready
SYNC_FOLDER = os.getenv('SYNC_FOLDER', "/volumes")
ADDITIONAL_OPTIONS = shlex.split(os.getenv('ADDITIONAL_OPTIONS', ""))
if os.getenv('ONLY_ADDITIONAL_OPTIONS'):
    SYNC_CLIENT = ["unison"]

# Vars
shutdown = False
server_process = None

def get_group_ips():
    # Get the ips of all replicas without that of this container
    sync_group_ips = socket.gethostbyname_ex(HOSTNAME_GROUP + ".")[2]
    logging.debug(("IPs of group are %s") % sync_group_ips)
    if sync_group_ips is None:
        sync_group_ips = []
    return sync_group_ips

def get_sorted_group_ips():
    group_ips = get_group_ips()
    # Sort ips from 0.0.0.0 to 255.255.255.255 by each byte value
    return sorted(group_ips, key=lambda ip: struct.unpack("!L", socket.inet_aton(ip))[0])

def get_container_ip():
    return socket.gethostbyname_ex(socket.gethostname()+".")[2][0]

def check_sync_server():
    # Shutdown if sync server has stopped
    global server_process
    global SHUTDOWN
    if server_process and server_process.poll() != None:
        logging.warn("Sync server is not running anymore. Shutting down!")
        SHUTDOWN = True

def cleanup():
    shutil.rmtree('/root/.unison', ignore_errors=True)

def start_sync_server():
    global server_process
    args = SYNC_SERVER
    server_process = subprocess.Popen(args)
    logging.debug("Sync server started with args: %s" % args)

def try_kill_process(process):
    try:
        process.kill()
    except Exception as e:
        logging.info("Could not kill process %s: " % (str(process), str(e)))


def sync():
    sync_source = SYNC_FOLDER
    all_sync_ips = get_sorted_group_ips()
    logging.debug("Group ips are %s" % all_sync_ips)
    container_ip = get_container_ip()
    logging.debug("Container ip is %s" % container_ip)
    if container_ip not in all_sync_ips:
        logging.error("IP of Container %s not part of group %s. Do you have all connected the hosts via network?" % (container_ip, all_sync_ips))
    container_ip_pos = all_sync_ips.index(container_ip)
    # This container must be part of the network
    if container_ip_pos < 0:
        logging.warn("Container ip %s not in group ip %s" % (container_ip, all_sync_ips))
    # Create list of sync targets
    sync_ips = []
    if SYNC_TYPE == "FIRST":
        sync_ips = [all_sync_ips[0]]
    elif SYNC_TYPE == "NEXT":
        next_index = (container_ip_pos + 1) % len(all_sync_ips)
        sync_ips = [all_sync_ips[next_index]]
    elif SYNC_TYPE == "ALL":
        sync_ips = all_sync_ips

    # Container should not sync to itself
    if container_ip in sync_ips:
        sync_ips.remove(container_ip)

    # If there is no sync partner then cancel
    if not sync_ips:
        logging.info("No ips to sync.")
        return

    for sync_ip in sync_ips:
        # Cancel when shutdown
        global shutdown
        if shutdown:
            return

        sync_target = "socket://%s:%s/%s" % (sync_ip, SYNC_SERVER_PORT, SYNC_FOLDER)
        args = SYNC_CLIENT + ADDITIONAL_OPTIONS + [sync_source] + [sync_target]
        logging.info("Running sync (Timeout: %s) with args: %s " % (SYNC_TIMEOUT, args))
        sync_process = subprocess.Popen(args)
        returncode = sync_process.wait(timeout = SYNC_TIMEOUT)
        if (returncode == None):
            logging.warn("Could not finish sync in timeout %s" % SYNC_TIMEOUT)
            try_kill_process(sync_process)
        logging.debug("Sync process stopped with exit code %s" % returncode)

## MAIN
cleanup()
start_sync_server()
time.sleep(WAIT_BEFORE_SYNC)

lastSync = time.time()
while not shutdown:
    check_sync_server()
    if (time.time()-lastSync > SYNC_INTERVAL):
        logging.debug("Now syncing")
        lastSync = time.time()
        sync()
    nextSync = SYNC_INTERVAL - (time.time()-lastSync)
    if nextSync > 0:
        logging.debug("Next sync in %ss" % nextSync)
        time.sleep(nextSync)

# Shutdown server
try_kill_process(server_process)
