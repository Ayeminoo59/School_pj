# SCOPE — Smart Collaborative Oriented Peer Education
### Final Application · Flask · AYE MIN OO (201941) · Twinkle College

This is the **complete final application** (built from the Initial + Intermediate
versions). Everything runs **on your own computer** — no internet server needed.

---

## 1. What you need (one time only)

| Requirement | Download link |
|---|---|
| **Python 3.10 or newer** | https://www.python.org/downloads/ |

> 💡 **Windows users:** on the first Python installer screen,
> **tick the checkbox "Add Python to PATH"** before clicking Install.

---

## 2. How to run on YOUR computer

### Step 1 — Unzip this folder
Unzip `SCOPE_final_application.zip` anywhere, e.g.:

- Windows: `C:\Users\<yourname>\Documents\scope_app`
- macOS / Linux: `~/Documents/scope_app`

### Step 2 — Open a terminal inside the folder

- **Windows:** open the `scope_app` folder in File Explorer → click the
  address bar → type `cmd` → press Enter.
- **macOS:** right-click the `scope_app` folder → *Services* → *New Terminal at Folder*.
- **Linux:** right-click inside the folder → *Open in Terminal*.

### Step 3 — Install the required libraries (one time only)

```bash
pip install -r requirements.txt
```

This installs: Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, bcrypt, python-dotenv.

### Step 4 — (Optional) Personal settings with a .env file

The app works fine **without** this step — `config.py` has safe defaults.
If you want your own secret key and settings, copy the template and edit it:

```bash
# Windows:
copy .env.example .env
# macOS / Linux:
cp .env.example .env
```

Keep the `.env` file in the `scope_app` folder (next to `config.py`),
edit it, then restart the app. Available variables:

| Variable | Purpose | Default if not set |
|---|---|---|
| `SCOPE_SECRET_KEY` | Signs login sessions (security) | `scope-dev-secret-key-change-me` |
| `SCOPE_DATABASE_URL` | Where the SQLite file lives | `db/scope.db` inside the folder |
| `SCOPE_DEBUG` | `1` = auto-reload while coding | `0` (off) |

> ⚠️ **Never share or upload your `.env` file** — it holds secrets.
> The included `.gitignore` already keeps it out of Git. After editing
> `.env`, stop the app (Ctrl+C) and run `python run.py` again.

### Step 5 — (Optional) Reset the database with demo data

The `db/scope.db` file already contains demo users. If you ever want a
**fresh database with demo accounts again**, delete `db/scope.db` and run:

```bash
python seed.py
```

### Step 6 — Start the application

```bash
python run.py
```

You will see something like:

```
 * Running on http://127.0.0.1:5000
```

### Step 7 — Open it in your browser

Go to: **http://127.0.0.1:5000/scope**

That's it — the whole application now runs on your own machine. 🎉

---

## 3. Demo accounts (already in the database)

**Admin account** (opens the Admin 🛠️ panel in the navbar):

| Email | Password |
|---|---|
| `admin@university.com` | `admin123` |

From the Admin panel you can: see platform statistics, manage users
(promote / demote / delete), add or delete modules, oversee all study
groups and review every study request. You can give more people admin
rights from **Admin → Users → Make Admin**.

> Older databases (created before the admin feature) are migrated
> automatically on the next start — the `is_admin` column is added and
> the admin account is created for you.

The database also comes with **8 demo students**. All use the same password:
`password123`. A few you can try:

| Email | Password |
|---|---|
| `sarah.chen@university.com` | `password123` |
| `michael.brown@university.com` | `password123` |
| `emma.wilson@university.com` | `password123` |
| `thiri.aung@university.com` | `password123` |

*(The login page also shows the demo accounts, or you can register your
own new account from the Sign Up page.)*

---

## 4. Project folder structure (clean & organized)

```
scope_app/
├── run.py                  ← START HERE (python run.py)
├── seed.py                 ← demo data loader (optional)
├── config.py               ← app settings (secret key, DB path, matching weights)
├── requirements.txt        ← Python libraries to install
├── .env.example            ← template for your own .env (optional)
├── .gitignore              ← keeps .env / db out of Git
├── HOW_TO_RUN.md           ← this guide
│
├── app/                    ← the Flask application package
│   ├── __init__.py         ← app factory (create_app)
│   ├── extensions.py       ← db / login manager singletons
│   ├── models.py           ← database models (User, Module, Group, ...)
│   ├── seed.py             ← demo data logic (runs automatically on startup)
│   │
│   ├── auth/               ← login / logout / sign up
│   ├── profile/            ← user profile management
│   ├── admin/              ← ADMIN PANEL (users / modules / groups / requests)
│   ├── modules/            ← enrolled modules per student
│   ├── availability/       ← weekly free-time grid
│   ├── matches/            ← study-partner matching results
│   ├── matching/           ← matching ENGINE (2-stage algorithm + cache)
│   ├── requests/           ← partner requests (send / accept / decline)
│   ├── groups/             ← study groups
│   ├── scheduling/         ← group session scheduler (greedy algorithm)
│   ├── main/               ← dashboard / home pages
│   │
│   ├── templates/          ← HTML pages (Jinja2)
│   │   ├── base.html       ← shared layout (navbar, footer)
│   │   ├── index.html      ← landing page
│   │   ├── auth/ profile/ modules/ availability/
│   │   ├── matches/ requests/ groups/ errors/
│   │   └── main/
│   │
│   └── static/
│       ├── css/            ← stylesheets
│       └── js/             ← client-side scripts
│
└── db/
    └── scope.db            ← SQLite database (auto-created if missing)
```

---

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognized | Reinstall Python and tick **"Add to PATH"**, or use `py run.py` on Windows |
| `ModuleNotFoundError: flask` | Run `pip install -r requirements.txt` inside the folder |
| Port 5000 already in use | Edit the last line of `run.py`: change `port=5000` → `port=5001` |
| Forgot a password | Just register a new account, or delete `db/scope.db` and run `python seed.py` |
| Page looks broken | Hard-refresh the browser (Ctrl+Shift+R) |
| Edited `.env` but nothing changed | Stop the app (Ctrl+C) and run `python run.py` again |

---

*AYE MIN OO (201941) — Twinkle College.*
