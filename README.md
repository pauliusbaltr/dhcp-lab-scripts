# Lab scripts

Scripts for the required path and the optional winning attack. All run on
**Kali**. Read the **Know the script** blocks in the self-paced guide / pre-read
before running any of them.

### Required path

- `rogue-dhcp.sh` — rogue DHCP + lab-only DNS for the **controlled test** (after
  VirtualBox DHCP is disabled). Edit the two placeholders (`<KALI_LAB_IF>`,
  `<KALI_IP>`). Start: `sudo bash ~/scripts/rogue-dhcp.sh`; `Ctrl+C` stops it. Uses
  `--dhcp-authoritative`.
- `catcher.py` — Challenge 2 **Path B**: serves a styled "CompanyX Portal" login
  page and captures submissions (prints them, and saves to a log file). Start:
  `sudo python3 ~/scripts/catcher.py`. The exact log path is printed at startup —
  under `sudo` it is `/root/harvest.log`, not your user's home. Robust,
  self-contained, no external assets.

### Challenge 2 Path A (optional, SET)

- `portal-source/` — a ready-made source login page to clone with SET. It is
  served on **Ubuntu**, so copy it there **during readiness**, before the attack:
  once Option 6 = Kali, Ubuntu loses external DNS and cannot fetch anything. Then
  `python3 -m http.server 8000` and give SET that URL. See `portal-source/README.md`.

### Optional winning attack

- `dhcp_starve.py` — bounded, **full-DORA** DHCP starvation: collects *all*
  offers (not just the first) and claims only verified legitimate leases
  (server `.3`, in-pool, real ACK), so it pressures the legitimate pool without
  miscounting the rogue's own offers. Edit `IFACE` and `COUNT` (= legitimate pool
  size). Proves the server handed out those addresses (Observed), not that the
  pool is empty. Needs Promiscuous Mode = Allow All and the small-pool addressing
  — see `../../instructor/virtualbox-lab-setup-LT.md` and
  `../optional/rogue-dhcp-win.md`.

The optional two-server race uses a **different** dnsmasq command (without
`--dhcp-authoritative`); see `../optional/two-server-race.md`.
