# Optional — make the rogue DHCP actually win (starvation + authoritative rogue)

This is a separate **experiment**, not a guaranteed win: both DHCP servers stay
up, and the aim is to pressure the legitimate server (by starving its pool) so
that a forced client re-request is answered by the rogue instead. Unlike the
required controlled path (which disables VirtualBox DHCP), here the competition is
real — so the result must be read from evidence, not assumed.

Keep two claims strictly separate throughout:

- **"Ubuntu accepted the rogue lease."** This is *confirmable* from Ubuntu's own
  ACK and `nmcli` state (address in the rogue range, Option 54/6 = Kali).
- **"The legitimate pool was exhausted."** This is a *stronger* claim about the
  other server; a single missing `.3` offer does not prove it. Confirming it needs
  server-side lease state or logs, which you do not have here — so label it
  **Observed** at best.

It is bounded and stays in your own sandbox, but it needs two environment
changes, so it is optional. Keep its evidence separate from the required
controlled result.

## Why this works (and why it needs setup)

A straight two-server race is unreliable: the client may take either offer or
just renew. Two things tilt it toward the rogue here. First, **starvation**: if
the legitimate server has no free address, it cannot offer, so a re-requesting
client is more likely to end up with the rogue. Second, the rogue runs
**authoritative**, so when the victim broadcasts a REQUEST to reuse its old
legitimate lease, the rogue answers with a **NAK** — pushing the victim into a
fresh DISCOVER the rogue can serve. (This is a different use of `--dhcp-authoritative`
than the required path, where it is justified by Kali being the only server; here
it is used deliberately as an attack lever, with the legitimate server still up.)

To keep starvation **bounded** (the rules forbid an unbounded flood), the
legitimate pool must be small. The recommended lab addressing shrinks it to
**`10.0.2.10–.19` (10 addresses)**. Claiming those 10 leases puts the pool under
pressure — but "under pressure" is not the same as "provably empty" (see the
evidence note above). You also need **Promiscuous Mode = Allow All** so Kali sees
the offers sent to your spoofed MACs. Both are one-time changes to your own
sandbox — the exact steps are in **Set up your sandbox** below.

> **Prerequisites (confirm before starting):**
> - Legitimate NAT Network DHCP pool = `10.0.2.10–.19`; VirtualBox DHCP **enabled**.
> - Promiscuous Mode = Allow All on both VM lab adapters.
> - Kali static `10.0.2.2`; rogue pool `.100–.110` (clearly distinct, so the
>   address Ubuntu ends up with tells you which server won).
> - Scapy on Kali: `python3 -c "import scapy.all"`.

## Set up your sandbox for this variant (one-time)

These two changes are only for this optional variant, and only on **your own**
sandbox. Do them on your **Windows host**: the pool change in PowerShell
(`VBoxManage`), the Promiscuous change in VM settings. **Write your current pool
down first**, so you can put it back exactly in step 5.

**1. Note your current DHCP pool (so you can restore it):**

```powershell
& 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' list dhcpservers
```

Write down the current `LowerIP`, `UpperIP`, `ServerIP` and `NetworkMask` for your
NAT network.

**2. Shrink the legitimate pool to 10 addresses (`.10–.19`):**

Replace `NatNetwork` in the commands below (here and in step 5) with **your** NAT
network's name if it differs — `VBoxManage list natnetworks` shows it.

```powershell
& 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' dhcpserver modify `
    --network="NatNetwork" `
    --server-ip=10.0.2.3 --netmask=255.255.255.0 `
    --lower-ip=10.0.2.10 --upper-ip=10.0.2.19 --enable
& 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' natnetwork stop  --netname "NatNetwork"
& 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' natnetwork start --netname "NatNetwork"
```

The small pool is what keeps the starvation **bounded** — you claim at most 10
addresses, not an unbounded flood. If `dhcpserver modify` says "not found", your
version may use `--netname="NatNetwork"` instead of `--network=...`;
`list dhcpservers` shows the name it is bound to. If your VirtualBox cannot change
the NAT pool at all (older 6.x), this variant needs a different setup — ask your
instructor.

**3. Turn on Promiscuous Mode = Allow All** on the lab adapter of **both** VMs, so
Kali can see the offers sent to your fake MACs:

```powershell
& 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' modifyvm "Kali"   --nicpromisc1 allow-all
& 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' modifyvm "Ubuntu" --nicpromisc1 allow-all
```

GUI instead: VM → **Settings → Network → Adapter (lab) → Advanced → Promiscuous
Mode → Allow All**. If the lab adapter is not Adapter 1, change `--nicpromisc1` to
the right number.

## Step 1 — start the authoritative rogue (Kali)

Start the rogue DHCP/DNS first, so it is ready to answer the moment the victim
rediscovers. Use the required-path script (`scripts/rogue-dhcp.sh`) with your
values — it is authoritative and serves the `.100–.110` pool and the
`training.test` mapping:

```bash
sudo bash ~/scripts/rogue-dhcp.sh
```

Leave it running in its terminal.

## Step 2 — starve the legitimate pool (Kali)

In a second Kali terminal, edit the supplied script and run it. Set `IFACE` to
your lab interface and `COUNT` to the legitimate pool size (10 for `.10–.19`):

```bash
nano ~/scripts/dhcp_starve.py      # set IFACE and COUNT
sudo python3 ~/scripts/dhcp_starve.py
```

**🔎 Know the script (before running).** Open `scripts/dhcp_starve.py` and read it
against the DORA you learned in the pre-read:

- `COUNT` bounds the run (set it to the legitimate pool size); the loop sends
  exactly `COUNT` exchanges and stops — it is not a flood.
- `RandMAC()` gives each iteration a **fresh fake MAC**, so each looks like a new
  client; `xid` is randomised so each exchange is distinct.
- `srp(discover, ..., multi=True)` sends the DISCOVER and collects **all** replies
  within the timeout — not just the first. This matters because the rogue is also
  running: a first-answer-only read could catch the rogue's reply and miss the
  legitimate offer. From the collected replies the script then selects the right
  one.
- It **only selects offers from the legitimate server** (`LEGIT_SERVER = 10.0.2.3`)
  for an address **inside the legitimate pool** (`POOL_LO..POOL_HI`). Offers from
  the rogue, or out-of-range, are reported and ignored — so the "claimed" count
  cannot be inflated by the rogue's own offers, and a faster rogue reply does not
  make it miss the legitimate one.
- It then REQUESTs that address and inspects the reply's **message-type**: only a
  real **DHCPACK (type 5)** from `.3` counts as a held lease; a **NAK (type 6)** or
  anything else is reported, not counted. (Checking the type matters — a NAK also
  has a DHCP layer.)
- `flags=0x8000` asks the server to **broadcast** its offers; combined with
  Promiscuous = Allow All, that is why Kali can see offers sent to the fake MACs.

Predict: why does counting a reply as "claimed" require checking both the server
identity and the message type? And why is a DISCOVER-only burst (the lighter
`dhcp-starvation.md` exercise) *not* enough to hold a lease?

The output lists only verified legitimate leases. A high claimed count means the
legitimate server handed those addresses to fake clients — **Observed pressure on
its pool**, not proof it is empty. A "no OFFER" line can also be timing or loss,
not exhaustion. **Leases are held until they expire**, so move promptly to step 3,
where the decisive evidence is which server *Ubuntu* ends up accepting.

## Step 3 — force the victim to rediscover (Ubuntu)

On Ubuntu, start Wireshark on the lab interface, then apply display filter
`dhcp || dns`. Release and reconnect so Ubuntu re-requests rather than sitting on
its old lease:

```bash
sudo dhclient -r <UBUNTU_LAB_IF> 2>/dev/null   # release, if dhclient present
sudo nmcli device disconnect <UBUNTU_LAB_IF>
sudo nmcli device connect <UBUNTU_LAB_IF>      # triggers a new request
```

A reconnect does **not** guarantee a broadcast DISCOVER — Ubuntu may first send a
broadcast REQUEST for its old address (INIT-REBOOT). The *intended* path is: the
authoritative rogue NAKs that REQUEST, Ubuntu then DISCOVERs, and the rogue serves
it — but do not assume this happened. **Read the actual captured sequence and
describe what you see:** if the capture shows a NAK followed by a DISCOVER,
document that sequence; otherwise record the exchange that actually occurred
(renewal, a different server's reply, etc.). If it worked, Ubuntu ends up with a
`10.0.2.100–.110` address and Kali as DNS.

## Step 4 — confirm the win

```bash
nmcli device show <UBUNTU_LAB_IF>
getent ahostsv4 training.test
```

Two separate conclusions, with the evidence each one actually needs:

| Conclusion | Evidence (what it is) | Status you can claim |
|---|---|---|
| **Ubuntu accepted the rogue lease** | Ubuntu address in `10.0.2.100–.110`; ACK Option 54 = `<KALI_IP>` (not `.3`), Option 6 = `<KALI_IP>`; `nmcli device show` matches | **Confirmed** (from Ubuntu's own state) |
| **Actual DNS use** | Ubuntu → Kali `training.test` A query and matching reply in the capture | **Confirmed** when captured |
| **No legitimate-server OFFER captured in this exchange** | no usable `.3` OFFER in *this* capture | **Observed but not confirmed** — absence in one exchange is not proof the server could not answer |
| **Legitimate pool exhausted** | would need the legitimate server's lease state / logs | **Inconclusive** here (not available) |

The address range is the clearest single signal that *Ubuntu* accepted the rogue:
`10.0.2.10x` = rogue; `10.0.2.1x` = legitimate server still answered.

> **If Ubuntu still took a `.1x` address:** the legitimate server answered this
> time (e.g. it re-offered the address Ubuntu just released). Re-run step 2 to
> re-pressure the pool, then repeat step 3 promptly. This is a bounded retry, not
> an unbounded flood. If it keeps happening, confirm the pool really is `.10–.19`
> and that starvation reported verified claimed leases.

When Ubuntu has accepted the rogue lease **and** you have the DNS query/reply, you
may report a **Confirmed rogue DHCP takeover of the victim** — stating plainly
that pool exhaustion itself is Observed/Inconclusive, not Confirmed. Then continue
to the website stage (self-paced guide, **stage 7 — website cloning and credential
capture**); the `training.test → Kali` mapping is already live.

## Step 5 — restore

1. Stop `dhcp_starve.py` (it exits on its own) and leave the rogue running only
   if you continue to the website stage; otherwise Ctrl+C it.
2. The starved leases expire after the lease time. A NAT Network restart may
   help but is **not** a guaranteed lease flush — confirm the legitimate server
   actually hands out normal addresses again before assuming it is clean.
3. Restore Ubuntu and Kali as in the required-path cleanup (self-paced guide,
   **stage 8 — restore the environment**).
4. Put your sandbox back: restore the DHCP pool to the values you wrote down in
   **Set up your sandbox**, and turn Promiscuous back off:

   ```powershell
   & 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' dhcpserver modify `
       --network="NatNetwork" --lower-ip=<YOUR_LOWER> --upper-ip=<YOUR_UPPER> --enable
   & 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' modifyvm "Kali"   --nicpromisc1 deny
   & 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' modifyvm "Ubuntu" --nicpromisc1 deny
   ```

   Use the lower/upper values you **recorded**, not a generic range. After the NAT
   restart, check the VMs really get normal addresses again (a restart does not
   always flush old leases).

**Evidence note.** The confirmable result is **"Ubuntu accepted the rogue lease
and used Kali for DNS"** — Ubuntu in the rogue range, Option 54/6 = Kali, and a
real `training.test` query/reply to Kali. **Pool exhaustion is a separate claim**
that this exercise can only mark **Observed** or **Inconclusive**, because you
have no legitimate-server lease state. Do not conflate the two.
