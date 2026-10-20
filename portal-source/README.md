# Source portal page (for SET Path A only)

`index.html` is a self-contained login page you can serve as the **source** for
SET Site Cloner, so Path A has something real to clone. Not needed for Path B
(the Flask catcher already serves its own styled page).

Serve it on **Ubuntu** (the "legitimate" site being impersonated), on a port
other than 80 if Kali will use 80:

```bash
cd path/to/portal-source
python3 -m http.server 8000     # then the source URL is http://<UBUNTU_IP>:8000/
```

In SET, give that URL as the **URL to clone**, and `<KALI_IP>` as the POST-back
IP. SET copies the look and rewrites the form to post back to Kali. The page uses
only inline CSS (no external resources), so the clone does not break on missing
assets.

If SET is unavailable or the clone misbehaves, use Path B — it is the more robust
path and satisfies the same learning objective.
