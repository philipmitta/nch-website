# Narsapur Christian Hospital — Website

Public website for **Narsapur Christian Hospital**, Roypet, Narsapur – 534 275,
West Godavari District, Andhra Pradesh. Serving since 1915.

Live site: _(add the URL once deployed)_

---

## What this repository holds

| Path | What it is |
|---|---|
| `index.html` | The whole website — one self-contained page. Edit this. |
| `assets/images/` | Logo, doctor portraits, staff photo, Google Business QR |
| `assets/fonts/` | Lora and Source Sans 3, self-hosted as woff2 |
| `tools/unbundle.py` | Converts a Claude Design export into the above |
| `design-export/` | The original Claude Design bundle, kept for re-import |

The site is a single HTML page with its CSS and JavaScript inline. There is no
build step, no framework and no dependencies — open `index.html` in a browser
and it works.

---

## Editing

### Option A — edit the HTML directly

Open `index.html`, change what you need, commit. Useful landmarks:

- `:root { … }` near the top holds every colour as a CSS variable
- Each page section is marked with an HTML comment (`<!-- DOCTORS -->`, etc.)
- Doctor biographies live in the `doctorData` object in the script at the bottom
- Phone, WhatsApp and email appear in the appointment section, the contact
  section and the footer — change all three

To preview locally:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

Use a local server rather than opening the file directly, so the fonts and
images load with the right paths.

### Option B — edit visually in Claude Design, then re-import

Claude Design exports a *bundled* HTML file: the entire page is stored as a
JSON-encoded string inside a `<script type="__bundler/template">` tag, with
fonts in a separate manifest and images inlined as base64.

**Do not commit that file as the site, and do not try to edit it by hand.**
Inside the bundle every `</` is escaped as `</`; ordinary find-and-replace
silently corrupts it and the page stops loading.

Instead, unpack it:

```bash
python3 tools/unbundle.py path/to/new-export.html .
```

That rewrites `index.html` and refreshes `assets/`, and fails loudly if any
reference does not resolve. Review the diff, then commit.

---

## Deploying

### GitHub Pages (free, no bandwidth limits on public repos)

Settings → Pages → Source: *Deploy from a branch* → `main` / `root`.
The site publishes at `https://philipmitta.github.io/<repo>/` within a minute
of each push. Add a custom domain on the same screen if you point the DNS at
GitHub.

### Netlify

Connect the repository instead of drag-and-dropping a file, and Netlify will
rebuild on every push. Publish directory: the repository root.

---

## Things worth knowing

- **Google Analytics** (`G-FQ94YNRL4L`) is in the `<head>`. If you re-export
  from Claude Design while an ad blocker is running, the blocker can replace
  the analytics script with a dummy that then gets baked into the bundle.
  After any re-import, confirm the tag still points at
  `googletagmanager.com`.
- **Appointments** do not go to a server. The form opens WhatsApp with the
  patient's details pre-filled, addressed to +91 82972 74529.
- **Donations** — the page lists the SBI account, the UPI ID, the 80G
  exemption, the MCA CSR registration (CSR00114660) and the Benevity listing.
  These are the kind of details worth double-checking after any edit.
