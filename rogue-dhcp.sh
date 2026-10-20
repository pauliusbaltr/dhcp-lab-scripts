#!/bin/bash
# Rogue DHCP + lab-only DNS for the CONTROLLED test (VirtualBox DHCP disabled).
#
# Use this ONLY after you have disabled VirtualBox DHCP in your own sandbox and
# Kali holds its static IP. It is NOT the script for the optional two-server
# race (that one omits --dhcp-authoritative).
#
# Before running:
#   - replace <KALI_LAB_IF> with Kali's lab interface (e.g. eth0, from `ip -br link`)
#   - replace BOTH <KALI_IP> occurrences with Kali's current static IP
#   - do not leave any angle brackets, and no spaces after a line-ending backslash
#
# Ctrl+C stops the server. Re-run the same command to restart it. If Kali's IP
# changes, update both <KALI_IP> values first. Do not start a second copy.

dnsmasq --conf-file=/dev/null --no-daemon \
  --interface=<KALI_LAB_IF> --bind-interfaces \
  --except-interface=lo --dhcp-authoritative \
  --dhcp-range=10.0.2.100,10.0.2.110,255.255.255.0,10m \
  --dhcp-option=3,10.0.2.1 --dhcp-option=6,<KALI_IP> \
  --no-resolv --no-hosts \
  --address=/training.test/<KALI_IP> --log-queries --log-dhcp
