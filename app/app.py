import os
import zipfile
import tempfile
import boto3
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
)
from werkzeug.utils import secure_filename

# ── App bootstrap ──────────────────────────────────────────────────────────────
app = Flask(__name__)

# Secret key for session encryption — injected via env var, never hardcoded
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")

# ── Config from environment variables ─────────────────────────────────────────
PORTAL_USERNAME = os.environ.get("PORTAL_USERNAME", "admin")
PORTAL_PASSWORD = os.environ.get("PORTAL_PASSWORD", "changeme")

BUCKETS = {
    "main": {
        "bucket": os.environ.get("S3_BUCKET_MAIN", ""),
        "cloudfront_id": os.environ.get("CF_DIST_MAIN", ""),
        "label": "Main Website (gadiyadekhe.com)",
    },
    "admin": {
        "bucket": os.environ.get("S3_BUCKET_ADMIN", ""),
        "cloudfront_id": os.environ.get("CF_DIST_ADMIN", ""),
        "label": "Admin Panel (admin.gadiyadekhe.com)",
    },
}

ALLOWED_EXTENSIONS = {"zip"}

# ── AWS clients ────────────────────────────────────────────────────────────────
# boto3 automatically uses EC2 instance role — no credentials in code
s3 = boto3.client("s3", region_name="ap-south-1")
cf = boto3.client("cloudfront", region_name="ap-south-1")


# ── Helpers ────────────────────────────────────────────────────────────────────
def allowed_file(filename):
    """Only allow .zip files"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_logged_in():
    """Check if user has an active session"""
    return session.get("logged_in") is True


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("index.html", buckets=BUCKETS)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == PORTAL_USERNAME and password == PORTAL_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("index"))
        error = "Invalid credentials. Please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/upload", methods=["POST"])
def upload():
    if not is_logged_in():
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    # Validate target site selection
    target = request.form.get("target")
    if target not in BUCKETS:
        return jsonify({"success": False, "message": "Invalid target selected"}), 400

    # Validate file presence
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Only .zip files are allowed"}), 400

    bucket_name = BUCKETS[target]["bucket"]
    cloudfront_id = BUCKETS[target]["cloudfront_id"]

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, secure_filename(file.filename))
            file.save(zip_path)

            # Extract zip
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)

            # Build list of all local files to upload
            local_files = {}
            for root, dirs, files in os.walk(tmpdir):
                for fname in files:
                    if fname.endswith(".zip"):
                        continue
                    local_path = os.path.join(root, fname)
                    s3_key = os.path.relpath(local_path, tmpdir)
                    local_files[s3_key] = local_path

            # Delete files in S3 not in new zip — sync behavior
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name):
                for obj in page.get("Contents", []):
                    if obj["Key"] not in local_files:
                        s3.delete_object(Bucket=bucket_name, Key=obj["Key"])

            # Upload all new files
            uploaded_count = 0
            for s3_key, local_path in local_files.items():
                content_type = get_content_type(s3_key)
                s3.upload_file(
                    local_path,
                    bucket_name,
                    s3_key,
                    ExtraArgs={"ContentType": content_type},
                )
                uploaded_count += 1

        # CloudFront invalidation
        cf.create_invalidation(
            DistributionId=cloudfront_id,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": ["/*"]},
                "CallerReference": str(os.urandom(8).hex()),
            },
        )

        return jsonify({
            "success": True,
            "message": f"Deployed successfully. {uploaded_count} files uploaded. CloudFront cache cleared.",
        })

    except zipfile.BadZipFile:
        return jsonify({"success": False, "message": "Invalid zip file"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Deployment failed: {str(e)}"}), 500


def get_content_type(filename):
    """Return correct Content-Type for common static file types"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    types = {
        "html": "text/html",
        "css":  "text/css",
        "js":   "application/javascript",
        "json": "application/json",
        "png":  "image/png",
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "svg":  "image/svg+xml",
        "ico":  "image/x-icon",
        "woff": "font/woff",
        "woff2":"font/woff2",
        "ttf":  "font/ttf",
        "webp": "image/webp",
        "txt":  "text/plain",
        "xml":  "application/xml",
    }
    return types.get(ext, "application/octet-stream")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)