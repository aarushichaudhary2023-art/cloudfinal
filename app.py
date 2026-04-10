from flask import Flask, request, jsonify, redirect, session, send_from_directory, make_response
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from dotenv import load_dotenv

load_dotenv()
from vendors import VENDORS, TEST_SCENARIOS, BASELINE_PRICING, VALID_SIZES, VALID_COMPLIANCE
import random, os, io, csv, json, threading, time
from datetime import datetime

try:
    import requests as http_requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# Config  —  all secrets come from environment variables / .env file
# ─────────────────────────────────────────────────────────────────────────────
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set.")
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'cloudmatch.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)
    role          = db.Column(db.String(50), nullable=False, default="Developer")
    oauth_provider= db.Column(db.String(50), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    recommendations = db.relationship("RecommendationHistory", backref="user", lazy=True)

    def set_password(self, plain_password):
        self.password_hash = bcrypt.hashpw(
            plain_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, plain_password):
        if not self.password_hash:
            return False
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            self.password_hash.encode("utf-8")
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }


class LoginHistory(db.Model):
    __tablename__ = "login_history"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ip_address   = db.Column(db.String(50))
    logged_in_at = db.Column(db.DateTime, default=datetime.utcnow)


class RecommendationHistory(db.Model):
    __tablename__ = "recommendation_history"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    top_pick     = db.Column(db.String(50))
    top_score    = db.Column(db.Float)
    monthly_cost = db.Column(db.Float)
    workload     = db.Column(db.Text)
    full_result  = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "top_pick": self.top_pick,
            "top_score": self.top_score,
            "monthly_cost": self.monthly_cost,
            "workload": json.loads(self.workload) if self.workload else {},
            "full_result": json.loads(self.full_result) if self.full_result else {},
            "created_at": self.created_at.isoformat(),
        }
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID", "YOUR_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={'scope': 'openid email profile'},
)

# Set APP_BASE_URL=https://your-domain.com in production .env
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000")

# ─────────────────────────────────────────────────────────────────────────────
# Live Pricing Cache  (6-hour TTL, falls back to BASELINE_PRICING on error)
# ─────────────────────────────────────────────────────────────────────────────
_pricing_cache = {}
_pricing_lock  = threading.Lock()
_pricing_ts    = 0
CACHE_TTL      = 6 * 3600


def _fetch_live_pricing():
    result = {k: {sk: dict(sv) if isinstance(sv, dict) else sv
                  for sk, sv in v.items()}
              for k, v in BASELINE_PRICING.items()}

    if not REQUESTS_AVAILABLE:
        return result

    # AWS — cloudprice.net open API (no key needed)
    try:
        mapping = {"small": "t3.small", "medium": "t3.xlarge", "large": "m5.4xlarge"}
        aws_prices = {}
        for size, instance in mapping.items():
            r = http_requests.get(
                f"https://cloudprice.net/api/v1/regions/us-east-1/instances/{instance}?os=Linux",
                timeout=5)
            if r.status_code == 200:
                d = r.json()
                price = d.get("onDemandPrice") or d.get("price")
                if price:
                    aws_prices[size] = round(float(price), 6)
        if len(aws_prices) == 3:
            result["aws"]["compute"] = aws_prices
    except Exception:
        pass

    # GCP — public Billing Catalog (no key needed)
    try:
        r = http_requests.get(
            "https://cloudbilling.googleapis.com/v1/services/6F81-5844-456A/skus"
            "?currencyCode=USD&pageSize=50", timeout=6)
        if r.status_code == 200:
            for sku in r.json().get("skus", []):
                desc = sku.get("description", "").lower()
                if "n1 predefined instance" in desc and \
                        "us-central1" in str(sku.get("serviceRegions", [])):
                    tiers = (sku.get("pricingInfo", [{}])[0]
                               .get("pricingExpression", {})
                               .get("tieredRates", []))
                    if tiers:
                        price = tiers[0].get("unitPrice", {}).get("nanos", 0) / 1e9
                        if price > 0:
                            result["gcp"]["compute"] = {
                                "small":  round(price,      6),
                                "medium": round(price * 4,  6),
                                "large":  round(price * 16, 6),
                            }
                    break
    except Exception:
        pass

    return result


def get_pricing():
    global _pricing_cache, _pricing_ts
    now = time.time()
    with _pricing_lock:
        if not _pricing_cache or (now - _pricing_ts) > CACHE_TTL:
            _pricing_cache = _fetch_live_pricing()
            _pricing_ts    = now
        return _pricing_cache


# ─────────────────────────────────────────────────────────────────────────────
# Core logic
# ─────────────────────────────────────────────────────────────────────────────

def validate_request(data):
    errors  = []
    workload = data.get("workload", {})
    if not isinstance(workload, dict):
        errors.append("'workload' must be a JSON object.")
        return errors
    if workload.get("compute_size", "medium") not in VALID_SIZES:
        errors.append(f"compute_size must be one of {sorted(VALID_SIZES)}.")
    for key in ("compute_hours", "storage_gb", "network_gb"):
        val = workload.get(key, 1)
        if not isinstance(val, (int, float)) or val < 0:
            errors.append(f"workload.{key} must be a non-negative number.")
    if workload.get("compute_hours", 730) > 744:
        errors.append("compute_hours cannot exceed 744.")
    budget = data.get("max_budget", 1000)
    if not isinstance(budget, (int, float)) or budget <= 0:
        errors.append("max_budget must be a positive number.")
    unknown = set(data.get("required_compliance", [])) - VALID_COMPLIANCE
    if unknown:
        errors.append(f"Unknown compliance standards: {sorted(unknown)}.")
    return errors


def calculate_monthly_cost(vendor_key, workload):
    pricing = get_pricing()
    p       = pricing.get(vendor_key, BASELINE_PRICING[vendor_key])
    size    = workload.get("compute_size", "medium")
    hours   = workload.get("compute_hours", 730)
    stor_gb = workload.get("storage_gb", 100)
    net_gb  = workload.get("network_gb", 50)
    db_inst = workload.get("db_instances", 1)
    db_size = workload.get("db_size", "small")
    compute  = p["compute"].get(size, p["compute"]["medium"]) * hours
    storage  = p["storage"] * stor_gb
    network  = p["network"] * net_gb
    database = p["database"].get(db_size, p["database"]["small"]) * hours * db_inst
    return round(compute + storage + network + database, 2)


def score_vendor(vendor_key, requirements):
    vendor   = VENDORS[vendor_key]
    scores   = vendor["scores"]
    features = vendor["features"]
    workload = requirements.get("workload", {})
    rw = {
        "reliability": max(0, requirements.get("reliability_weight", 0.20)),
        "performance": max(0, requirements.get("performance_weight", 0.15)),
        "security":    max(0, requirements.get("security_weight",    0.15)),
        "cost":        max(0, requirements.get("cost_weight",        0.20)),
        "support":     max(0, requirements.get("support_weight",     0.10)),
        "innovation":  max(0, requirements.get("innovation_weight",  0.10)),
        "compliance":  max(0, requirements.get("compliance_weight",  0.10)),
    }
    tw = sum(rw.values()) or 1.0
    w  = {k: v / tw for k, v in rw.items()}

    monthly_cost    = calculate_monthly_cost(vendor_key, workload)
    max_budget      = max(1, requirements.get("max_budget", 1000))
    cost_score      = max(0.0, min(10.0, 10.0 - (monthly_cost / max_budget) * 5.0))

    req_compliance  = requirements.get("required_compliance", [])
    compliance_score = (
        0.0 if [c for c in req_compliance if c not in features["compliance"]]
        else 10.0
    ) if req_compliance else 8.0

    feat_adj = 0.0
    if requirements.get("needs_ml"):        feat_adj += 0.5 if features.get("ml_services") else -1.0
    if requirements.get("needs_kubernetes"): feat_adj += 0.3 if features.get("kubernetes")  else -0.8
    if requirements.get("needs_serverless"): feat_adj += 0.2 if features.get("serverless")  else -0.5

    breakdown = {
        "reliability": round(scores["reliability"] * w["reliability"], 3),
        "performance": round(scores["performance"] * w["performance"], 3),
        "security":    round(scores["security"]    * w["security"],    3),
        "cost":        round(cost_score            * w["cost"],        3),
        "support":     round(scores["support"]     * w["support"],     3),
        "innovation":  round(scores["innovation"]  * w["innovation"],  3),
        "compliance":  round(compliance_score      * w["compliance"],  3),
    }
    total = round(min(10.0, max(0.0, sum(breakdown.values()) + feat_adj)), 2)
    return total, monthly_cost, breakdown


def run_recommendation(requirements):
    results = []
    for vk, vendor in VENDORS.items():
        score, cost, breakdown = score_vendor(vk, requirements)
        results.append({
            "vendor": vk, "name": vendor["name"], "logo": vendor["logo"],
            "color": vendor["color"], "score": score, "monthly_cost": cost,
            "breakdown": breakdown, "strengths": vendor["strengths"],
            "weaknesses": vendor["weaknesses"], "features": vendor["features"],
            "scores": vendor["scores"],
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    results[0]["recommended"] = True
    return results


def generate_analysis(results, requirements):
    top, runner_up = results[0], results[1]
    reasoning, trade_offs = [], []
    if requirements.get("needs_ml"):
        reasoning.append("ML/AI requirement: GCP and AWS receive a bonus; absent vendors are penalised.")
    if requirements.get("cost_weight", 0) > 0.25:
        reasoning.append("High cost weight: Oracle Cloud and DigitalOcean offer the lowest compute rates.")
    if requirements.get("security_weight", 0) >= 0.2:
        reasoning.append("Elevated security weight: Azure and IBM Cloud lead with the broadest compliance portfolios.")
    if requirements.get("required_compliance"):
        reasoning.append(
            f"Hard compliance gate applied for: {', '.join(requirements['required_compliance'])}. "
            "Vendors missing any standard received compliance score = 0."
        )
    if not reasoning:
        reasoning.append("Balanced weights applied across all seven criteria.")
    if top["score"] - runner_up["score"] < 0.5:
        trade_offs.append(
            f"{runner_up['name']} is a close alternative "
            f"(score: {runner_up['score']}/10, ${runner_up['monthly_cost']:.0f}/mo)."
        )
    return {
        "summary": (f"{top['name']} is the best fit — score {top['score']}/10, "
                    f"est. ${top['monthly_cost']:.2f}/month."),
        "reasoning":  reasoning,
        "trade_offs": trade_offs,
    }


def baseline_cheapest(workload):
    return min(VENDORS.keys(), key=lambda vk: calculate_monthly_cost(vk, workload))

def baseline_highest_rated(_req):
    return max(VENDORS.keys(),
               key=lambda vk: sum(VENDORS[vk]["scores"].values()) / len(VENDORS[vk]["scores"]))

def baseline_random(_req):
    return random.choice(list(VENDORS.keys()))


def evaluate_scenarios(scenarios):
    methods = {
        "proposed":      lambda req: run_recommendation(req)[0]["vendor"],
        "cheapest":      lambda req: baseline_cheapest(req.get("workload", {})),
        "highest_rated": lambda req: baseline_highest_rated(req),
        "random":        lambda req: baseline_random(req),
    }
    stats  = {m: {"tp": 0, "fp": 0, "fn": 0} for m in methods}
    per_sc = []
    for sc in scenarios:
        req, expected = sc["requirements"], sc["expected_vendor"]
        row = {"id": sc["id"], "name": sc["name"], "expected": expected, "predictions": {}}
        for method, fn in methods.items():
            predicted = fn(req)
            correct   = predicted == expected
            row["predictions"][method] = {"vendor": predicted, "correct": correct}
            if correct: stats[method]["tp"] += 1
            else:       stats[method]["fp"] += 1; stats[method]["fn"] += 1
        per_sc.append(row)
    n = len(scenarios)
    aggregate = {}
    for method, s in stats.items():
        tp, fp, fn = s["tp"], s["fp"], s["fn"]
        acc  = round(tp / n,           4) if n          else 0
        prec = round(tp / (tp + fp),   4) if (tp + fp)  else 0
        rec  = round(tp / (tp + fn),   4) if (tp + fn)  else 0
        f1   = round(2*prec*rec/(prec+rec), 4) if (prec+rec) else 0
        aggregate[method] = {"accuracy": acc, "precision": prec, "recall": rec,
                              "f1_score": f1, "correct": tp, "total": n}
    return per_sc, aggregate

def get_session_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)
# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/login")
def login_page():
    return send_from_directory(".", "login.html")


@app.route("/api/recommend", methods=["POST"])
def recommend():
    data   = request.json or {}
    errors = validate_request(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400
    results = run_recommendation(data)
    # Save to history if logged in
    user = get_session_user()
    if user:
        hist = RecommendationHistory(
            user_id     = user.id,
            top_pick    = results[0]["vendor"],
            top_score   = results[0]["score"],
            monthly_cost= results[0]["monthly_cost"],
            workload    = json.dumps(data.get("workload", {})),
            full_result = json.dumps({"recommendations": results}),
        )
        db.session.add(hist)
        db.session.commit()
    return jsonify({
        "success":           True,
        "recommendations":   results,
        "top_pick":          results[0]["vendor"],
        "analysis":          generate_analysis(results, data),
        "pricing_source":    "live" if _pricing_cache else "baseline",
        "pricing_updated_at": (datetime.utcfromtimestamp(_pricing_ts).isoformat() + "Z"
                               if _pricing_ts else None),
    })


@app.route("/api/export/csv", methods=["POST"])
def export_csv():
    data   = request.json or {}
    errors = validate_request(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400
    results  = run_recommendation(data)
    analysis = generate_analysis(results, data)

    out = io.StringIO()
    w   = csv.writer(out)
    w.writerow(["CloudMatch — Vendor Recommendation Report"])
    w.writerow(["Generated",   datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")])
    w.writerow(["Top Pick",    results[0]["name"]])
    w.writerow(["Summary",     analysis["summary"]])
    w.writerow([])

    wl = data.get("workload", {})
    w.writerow(["=== WORKLOAD PARAMETERS ==="])
    for label, val in [
        ("Compute Size",        wl.get("compute_size", "medium")),
        ("Compute Hours/mo",    wl.get("compute_hours", 730)),
        ("Storage (GB)",        wl.get("storage_gb", 100)),
        ("Network Egress (GB)", wl.get("network_gb", 50)),
        ("DB Instances",        wl.get("db_instances", 1)),
        ("DB Size",             wl.get("db_size", "small")),
        ("Budget Cap ($)",      data.get("max_budget", 1000)),
        ("Required Compliance", ", ".join(data.get("required_compliance", [])) or "None"),
    ]:
        w.writerow([label, val])
    w.writerow([])

    w.writerow(["=== VENDOR SCORES ==="])
    w.writerow(["Rank","Vendor","Overall Score","Monthly Cost ($)",
                "Reliability","Performance","Security","Cost Score",
                "Support","Innovation","Compliance","Recommended"])
    for i, r in enumerate(results):
        bd = r["breakdown"]
        w.writerow([i+1, r["name"], r["score"], r["monthly_cost"],
                    bd.get("reliability",""), bd.get("performance",""), bd.get("security",""),
                    bd.get("cost",""), bd.get("support",""), bd.get("innovation",""),
                    bd.get("compliance",""), "YES" if r.get("recommended") else ""])
    w.writerow([])

    w.writerow(["=== STRENGTHS & WEAKNESSES ==="])
    w.writerow(["Vendor","Strengths","Weaknesses"])
    for r in results:
        w.writerow([r["name"], " | ".join(r["strengths"]), " | ".join(r["weaknesses"])])
    w.writerow([])

    w.writerow(["=== ANALYSIS ==="])
    for line in analysis["reasoning"] + analysis["trade_offs"]:
        w.writerow([line])

    resp = make_response(out.getvalue().encode("utf-8"))
    resp.headers["Content-Type"]        = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="cloudmatch_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.csv"')
    return resp


@app.route("/api/export/json", methods=["POST"])
def export_json_file():
    data   = request.json or {}
    errors = validate_request(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400
    results  = run_recommendation(data)
    analysis = generate_analysis(results, data)
    payload  = {
        "generated_at":       datetime.utcnow().isoformat() + "Z",
        "workload":           data.get("workload", {}),
        "max_budget":         data.get("max_budget", 1000),
        "required_compliance":data.get("required_compliance", []),
        "top_pick":           results[0]["vendor"],
        "analysis":           analysis,
        "recommendations":    results,
    }
    resp = make_response(json.dumps(payload, indent=2))
    resp.headers["Content-Type"]        = "application/json"
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="cloudmatch_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.json"')
    return resp


@app.route("/api/pricing", methods=["GET"])
def pricing_info():
    pricing = get_pricing()
    return jsonify({
        "source":     "live" if _pricing_ts else "baseline",
        "updated_at": (datetime.utcfromtimestamp(_pricing_ts).isoformat() + "Z"
                       if _pricing_ts else None),
        "pricing":    pricing,
    })


@app.route("/api/evaluate", methods=["GET", "POST"])
def evaluate():
    per_sc, aggregate = evaluate_scenarios(TEST_SCENARIOS)
    return jsonify({"per_scenario": per_sc, "aggregate": aggregate})


@app.route("/api/scenarios", methods=["GET"])
def scenarios():
    safe = [{k: v for k, v in sc.items() if k != "requirements"}
            for sc in TEST_SCENARIOS]
    return jsonify({"scenarios": safe, "count": len(safe)})


@app.route("/api/vendors", methods=["GET"])
def vendors_list():
    return jsonify({"vendors": list(VENDORS.keys()), "count": len(VENDORS)})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":         "ok",
        "version":        "3.0.0",
        "vendors":        len(VENDORS),
        "scenarios":      len(TEST_SCENARIOS),
        "pricing_source": "live" if _pricing_ts else "baseline",
    })
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data     = request.json or {}
    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role     = data.get("role") or "Developer"
    if not name or not email or not password:
        return jsonify({"success": False, "error": "Name, email, and password are required."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "An account with this email already exists."}), 409
    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"success": True, "message": "Account created. Please log in."}), 201


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data     = request.json or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401
    session["user_id"] = user.id
    log = LoginHistory(user_id=user.id, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    return jsonify({"success": True, "user": user.to_dict()})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.pop("user_id", None)
    return jsonify({"success": True})


@app.route("/api/auth/user", methods=["GET"])
def api_current_user():
    user = get_session_user()
    if user:
        return jsonify({"logged_in": True, "user": user.to_dict()})
    return jsonify({"logged_in": False})


@app.route("/api/history", methods=["GET"])
def get_history():
    user = get_session_user()
    if not user:
        return jsonify({"success": False, "error": "Not authenticated."}), 401
    items = (RecommendationHistory.query
             .filter_by(user_id=user.id)
             .order_by(RecommendationHistory.created_at.desc())
             .limit(50).all())
    return jsonify({"success": True, "history": [h.to_dict() for h in items]})


# ── Auth — OAuth callback URL built from APP_BASE_URL env var ────────────────
@app.route("/auth/login")
def auth_login():
    return google.authorize_redirect(f"{APP_BASE_URL}/auth/callback")

@app.route("/auth/callback")
def auth_callback():
    token = google.authorize_access_token()
    user  = token.get("userinfo")
    if user:
        session["user"] = {
            "name":    user["name"],
            "email":   user["email"],
            "picture": user["picture"],
        }
    return redirect("/")

@app.route("/auth/logout")
def auth_logout():
    session.pop("user", None)
    return redirect("/")

@app.route("/auth/user")
def get_user():
    user = session.get("user")
    return jsonify({"logged_in": True, "user": user} if user else {"logged_in": False})
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
