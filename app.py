"""IGNITE YOUR VITALITY - Flask app. Run: python app.py"""
import json, os, re, secrets, sqlite3, time
from functools import wraps
from flask import Flask, Response, abort, flash, g, redirect, render_template, request, session, url_for
from fpdf import FPDF
from werkzeug.security import check_password_hash, generate_password_hash
from content import QUESTIONS, SECTIONS
from plan_logic import age_of, gen_plan, scale_plan, steps_goal, streak

app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"), SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.environ.get("PROD") == "1")
DB = os.path.join(os.path.dirname(__file__), "ignite.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL,
  parent_email TEXT, consent INTEGER DEFAULT 0, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS profiles(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL, dob TEXT NOT NULL, managed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS questionnaire_answers(profile_id INTEGER PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE, answers TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS programs(profile_id INTEGER PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE, plan TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS progress_logs(profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE, week INTEGER, day INTEGER, PRIMARY KEY(profile_id, week, day));
"""
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ATTEMPTS = {}  # ip -> [timestamps]; use Redis in production


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row; g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()


def init_db():
    with sqlite3.connect(DB) as c: c.executescript(SCHEMA)


# ---------- security: CSRF on every POST, login rate limit, login_required ----------
@app.before_request
def csrf_protect():
    if request.method == "POST" and not secrets.compare_digest(request.form.get("csrf", ""), session.get("csrf", "x")):
        abort(400, "Invalid CSRF token")


@app.context_processor
def inject():
    session.setdefault("csrf", secrets.token_hex(16))
    return {"csrf": session["csrf"], "logged_in": "uid" in session}


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session: return redirect(url_for("login"))
        return f(*a, **k)
    return w


def profile():
    p = db().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (session.get("pid"), session["uid"])).fetchone()
    return p or abort(404)


# ---------- Step 1: accounts ----------
@app.route("/")
def index():
    return render_template("index.html", sections=SECTIONS)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET": return render_template("signup.html")
    f, errs = request.form, []
    name, email, dob = f.get("name", "").strip(), f.get("email", "").strip().lower(), f.get("dob", "")
    try: age = age_of(dob)
    except ValueError: age = None; errs.append("Enter your date of birth.")
    if not name: errs.append("Please enter your first name.")
    if not EMAIL.match(email): errs.append("Enter a valid email.")
    if len(f.get("password", "")) < 8: errs.append("Password needs at least 8 characters.")
    if f.get("password") != f.get("password2"): errs.append("Passwords do not match.")
    if not f.get("terms"): errs.append("Please accept the Terms and Privacy Policy.")
    if age is not None and age < 18 and (not EMAIL.match(f.get("parent_email", "")) or not f.get("consent")):
        errs.append("A parent/guardian email and consent are required under 18.")
    if not errs and db().execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone(): errs.append("That email is already registered.")
    if errs:
        for e in errs: flash(e)
        return render_template("signup.html"), 400
    cur = db().execute("INSERT INTO users(email,pw_hash,parent_email,consent) VALUES(?,?,?,?)",
                       (email, generate_password_hash(f["password"]), f.get("parent_email"), 1 if f.get("consent") else 0))
    pid = db().execute("INSERT INTO profiles(user_id,name,dob,managed) VALUES(?,?,?,?)", (cur.lastrowid, name, dob, int(age < 13))).lastrowid
    db().commit()
    session.clear(); session.update(uid=cur.lastrowid, pid=pid)
    return redirect(url_for("quiz"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET": return render_template("login.html")
    ip, now = request.remote_addr, time.time()
    ATTEMPTS[ip] = [t for t in ATTEMPTS.get(ip, []) if now - t < 300]
    if len(ATTEMPTS[ip]) >= 5:
        flash("Too many attempts. Try again in a few minutes."); return render_template("login.html"), 429
    u = db().execute("SELECT * FROM users WHERE email=?", (request.form.get("email", "").strip().lower(),)).fetchone()
    if not u or not check_password_hash(u["pw_hash"], request.form.get("password", "")):
        ATTEMPTS[ip].append(now); flash("Wrong email or password."); return render_template("login.html"), 401
    pid = db().execute("SELECT id FROM profiles WHERE user_id=? ORDER BY id LIMIT 1", (u["id"],)).fetchone()["id"]
    session.clear(); session.update(uid=u["id"], pid=pid)
    return redirect(url_for("program"))


@app.post("/logout")
def logout():
    session.clear(); return redirect(url_for("index"))


@app.post("/forgot")
def forgot():  # TODO: send a one-time reset link by email (itsdangerous token)
    flash("If that email exists, a reset link has been sent."); return redirect(url_for("login"))


# ---------- family profiles ----------
@app.post("/profile/add")
@login_required
def add_profile():
    try: age = age_of(request.form["dob"])
    except (ValueError, KeyError): flash("Enter a valid date of birth."); return redirect(url_for("program"))
    pid = db().execute("INSERT INTO profiles(user_id,name,dob,managed) VALUES(?,?,?,?)",
                       (session["uid"], request.form.get("name", "Family member")[:40], request.form["dob"], int(age < 13))).lastrowid
    db().commit(); session["pid"] = pid
    return redirect(url_for("quiz"))


@app.post("/profile/switch/<int:pid>")
@login_required
def switch(pid):
    if db().execute("SELECT 1 FROM profiles WHERE id=? AND user_id=?", (pid, session["uid"])).fetchone(): session["pid"] = pid
    return redirect(url_for("program"))


# ---------- Step 2 + 3: questionnaire -> generated plan ----------
def save_plan(p, answers):
    plan = gen_plan(answers, age_of(p["dob"]))
    db().execute("INSERT OR REPLACE INTO questionnaire_answers VALUES(?,?)", (p["id"], json.dumps(answers)))
    db().execute("INSERT OR REPLACE INTO programs(profile_id,plan) VALUES(?,?)", (p["id"], json.dumps(plan)))
    db().execute("DELETE FROM progress_logs WHERE profile_id=?", (p["id"],)); db().commit()


@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    p = profile()
    if request.method == "POST":
        ans = {k: (request.form.getlist(k) if t == "multi" else request.form.get(k, ""))
               for _, fields in QUESTIONS for k, _, t, _ in fields}
        save_plan(p, ans)
        return redirect(url_for("program"))
    row = db().execute("SELECT answers FROM questionnaire_answers WHERE profile_id=?", (p["id"],)).fetchone()
    return render_template("quiz.html", questions=QUESTIONS, a=json.loads(row["answers"]) if row else {}, age=age_of(p["dob"]), p=p)


@app.post("/regenerate")
@login_required
def regenerate():
    p = profile()
    row = db().execute("SELECT answers FROM questionnaire_answers WHERE profile_id=?", (p["id"],)).fetchone()
    if not row: return redirect(url_for("quiz"))
    save_plan(p, json.loads(row["answers"])); flash("New plan generated. Progress was reset.")
    return redirect(url_for("program"))


# ---------- program + tracking ----------
def load(p):
    row = db().execute("SELECT plan FROM programs WHERE profile_id=?", (p["id"],)).fetchone()
    return json.loads(row["plan"]) if row else None


@app.route("/program")
@login_required
def program():
    p = profile(); plan = load(p)
    if not plan: return redirect(url_for("quiz"))
    wk = min(3, max(0, request.args.get("week", 0, type=int)))
    done = {(r["week"], r["day"]) for r in db().execute("SELECT week,day FROM progress_logs WHERE profile_id=?", (p["id"],))}
    ans = json.loads(db().execute("SELECT answers FROM questionnaire_answers WHERE profile_id=?", (p["id"],)).fetchone()["answers"])
    age = age_of(p["dob"])
    return render_template("program.html", p=p, plan=plan, wk=wk, done=done, total=len(done), streak=streak(done),
                           ring=round(sum((wk, d) in done for d in range(7)) / 7 * 100), steps=steps_goal(age, ans.get("act", "")),
                           profiles=db().execute("SELECT * FROM profiles WHERE user_id=?", (session["uid"],)).fetchall(),
                           days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])


@app.post("/done/<int:w>/<int:d>")
@login_required
def done(w, d):
    p = profile()
    if db().execute("DELETE FROM progress_logs WHERE profile_id=? AND week=? AND day=?", (p["id"], w, d)).rowcount == 0:
        db().execute("INSERT INTO progress_logs VALUES(?,?,?)", (p["id"], w, d))
    db().commit(); return redirect(url_for("program", week=w))


@app.post("/adjust/<int:w>/<direction>")
@login_required
def adjust(w, direction):
    p = profile(); plan = load(p)
    db().execute("UPDATE programs SET plan=? WHERE profile_id=?", (json.dumps(scale_plan(plan, w, 0.85 if direction == "hard" else 1.15)), p["id"]))
    db().commit(); return redirect(url_for("program", week=w))


# ---------- PDF export, data export, deletion (GDPR) ----------
@app.route("/plan.pdf")
@login_required
def plan_pdf():
    p = profile(); plan = load(p) or abort(404)
    pdf = FPDF(); pdf.add_page(); pdf.set_auto_page_break(True, 15)
    pdf.set_font("Helvetica", "B", 20); pdf.set_text_color(255, 122, 26); pdf.cell(0, 10, "IGNITE YOUR VITALITY", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11); pdf.set_text_color(40); pdf.cell(0, 8, f"4-week plan for {p['name']}", new_x="LMARGIN", new_y="NEXT")
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, wk in enumerate(plan):
        pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(0, 100, 180); pdf.ln(3)
        pdf.cell(0, 8, f"WEEK {i + 1}", new_x="LMARGIN", new_y="NEXT")
        for j, d in enumerate(wk["days"]):
            pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(20)
            pdf.multi_cell(0, 5, f"{names[j]}: {d['ty']} - {d['nm']}" + (f" ({d['mn']} min)" if d["mn"] else ""), new_x="LMARGIN", new_y="NEXT")
            if d["mn"]:
                pdf.set_font("Helvetica", "", 9); pdf.set_text_color(70)
                pdf.multi_cell(0, 4.5, "Warm-up 5 min; " + "; ".join(d["ex"]) + "; Cool-down 5 min. " + " ".join(d["nt"]), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9); pdf.set_text_color(10, 140, 70); pdf.multi_cell(0, 5, "Tip: " + wk["tips"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(120, 0, 0); pdf.ln(3)
    pdf.multi_cell(0, 4.5, "General fitness guidance, not medical advice. Check with a doctor first if you have health conditions, are over 60, pregnant or returning from injury. Stop if you feel pain, dizziness or chest discomfort.")
    return Response(bytes(pdf.output()), mimetype="application/pdf", headers={"Content-Disposition": "attachment; filename=ignite-vitality-plan.pdf"})


@app.route("/export.json")
@login_required
def export():
    rows = {t: [dict(r) for r in db().execute(q, (session["uid"],))] for t, q in {
        "profiles": "SELECT * FROM profiles WHERE user_id=?",
        "answers": "SELECT * FROM questionnaire_answers WHERE profile_id IN (SELECT id FROM profiles WHERE user_id=?)",
        "programs": "SELECT * FROM programs WHERE profile_id IN (SELECT id FROM profiles WHERE user_id=?)",
        "progress": "SELECT * FROM progress_logs WHERE profile_id IN (SELECT id FROM profiles WHERE user_id=?)"}.items()}
    return Response(json.dumps(rows, indent=2), mimetype="application/json", headers={"Content-Disposition": "attachment; filename=my-data.json"})


@app.post("/delete")
@login_required
def delete():
    db().execute("DELETE FROM users WHERE id=?", (session["uid"],)); db().commit()  # cascades to all profile data
    session.clear(); flash("Your account and data were deleted."); return redirect(url_for("index"))


init_db()  # create tables at import time so gunicorn (Render) also has them

if __name__ == "__main__":
    app.run(debug=os.environ.get("PROD") != "1")
