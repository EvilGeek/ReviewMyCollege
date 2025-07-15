from flask import Flask, render_template, redirect, url_for, session, request, abort
from models import db, User, Institution, Review, UserInstitution
from auth import linkedin_blueprint, fetch_linkedin_data
from utils import encode_id, decode_id
from sqlalchemy.sql.expression import func
import os
import uuid
import requests

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///institutions.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
app.register_blueprint(linkedin_blueprint, url_prefix="/auth")

@app.route("/")
def home():
    return redirect("/search")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    user = db.session.get(User, session["user_id"]) if "user_id" in session else None
    if q:
        institutions = Institution.query.filter(Institution.name.ilike(f"%{q}%")).all()
    else:
        institutions = Institution.query.order_by(func.random()).limit(9).all()
    return render_template("search.html", institutions=institutions, query=q, user=user)

@app.route("/institute/<id>")
def institute(id):
    code = decode_id(id)
    inst = Institution.query.get_or_404(code)
    page = int(request.args.get("page", 1))
    reviews = Review.query.filter_by(aishe_code=code)\
        .order_by(Review.created_at.desc())\
        .limit(6 * page)\
        .options(db.joinedload(Review.user)).all()
    user = db.session.get(User, session["user_id"]) if "user_id" in session else None
    can_post = existing_review = False
    if user:
        can_post = UserInstitution.query.filter_by(user_id=user.id, aishe_code=code).first() is not None
        existing_review = Review.query.filter_by(user_id=user.id, aishe_code=code).first()
    all_reviews = Review.query.filter_by(aishe_code=code).all()
    avg_rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 1) if all_reviews else None
    return render_template("institute.html", inst=inst, reviews=reviews, avg_rating=avg_rating, page=page,
                           can_post=can_post, existing_review=existing_review, user=user, encode_id=encode_id)

@app.route("/institute/<id>/review", methods=["POST"])
def submit_review(id):
    if "user_id" not in session:
        return redirect("/login")
    code = decode_id(id)
    user_id = session["user_id"]
    if not UserInstitution.query.filter_by(user_id=user_id, aishe_code=code).first():
        abort(403)
    try:
        rating = int(request.form["rating"])
        title = request.form["title"][:100]
        body = request.form["body"][:500]
    except KeyError:
        abort(400, description="Missing required fields.")
    db.session.add(Review(user_id=user_id, aishe_code=code, rating=rating, title=title, body=body))
    db.session.commit()
    return redirect(f"/institute/{id}")

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")
    user = db.session.get(User, session["user_id"])
    reviews = Review.query.filter_by(user_id=user.id).all()
    institutions = [db.session.get(Institution, i.aishe_code) for i in user.institutions]
    return render_template("profile.html", user=user, reviews=reviews, institutions=institutions, encode_id=encode_id)

@app.route("/user/<uid>")
def public_user(uid):
    linkedin_id = decode_id(uid)
    user = User.query.filter_by(linkedin_id=linkedin_id).first_or_404()
    reviews = Review.query.filter_by(user_id=user.id).all()
    institutions = [db.session.get(Institution, i.aishe_code) for i in user.institutions]
    current_user = db.session.get(User, session["user_id"]) if "user_id" in session else None
    return render_template("user.html", user=user, reviews=reviews, institutions=institutions,
                           encode_id=encode_id, current_user=current_user)

@app.route("/auth/linkedin/callback")
def linkedin_callback():
    profile, email, edu_aishe_codes = fetch_linkedin_data(request.args.get("code"))
    linkedin_id = profile.get("id")
    name = profile.get("name", "")
    photo = profile.get("photo", "")
    user = User.query.filter_by(linkedin_id=linkedin_id).first()
    saved_path = None
    if photo:
        try:
            response = requests.get(photo, timeout=5)
            if response.status_code == 200:
                ext = "jpeg"
                filename = f"{uuid.uuid4().hex}.{ext}"
                folder = os.path.join("static", "profile_pics")
                os.makedirs(folder, exist_ok=True)
                local_path = os.path.join(folder, filename)
                with open(local_path, "wb") as f:
                    f.write(response.content)
                saved_path = f"profile_pics/{filename}"
        except Exception as e:
            print("⚠️ Failed to download image:", e)
    if not user:
        user = User(linkedin_id=linkedin_id, name=name, email=email, photo_url=saved_path or "")
        db.session.add(user)
    else:
        user.name = name or user.name
        user.email = email or user.email
        if saved_path and (not user.photo_url or not user.photo_url.startswith("profile_pics/")):
            user.photo_url = saved_path
    db.session.commit()
    session["user_id"] = user.id
    for code in edu_aishe_codes:
        if not UserInstitution.query.filter_by(user_id=user.id, aishe_code=code).first():
            db.session.add(UserInstitution(user_id=user.id, aishe_code=code))
    db.session.commit()
    return redirect("/profile")

@app.route("/select-college")
def select_college():
    if "user_id" not in session:
        return redirect("/login")
    user = db.session.get(User, session["user_id"])
    institutions = Institution.query.order_by(Institution.name).all()
    return render_template("select_college.html", user=user, institutions=institutions)

@app.route("/select-colleges", methods=["POST"])
def save_colleges():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    UserInstitution.query.filter_by(user_id=user_id).delete()
    ug_code = request.form.get("ug_college", "").strip()
    pg_code = request.form.get("pg_college", "").strip()
    if ug_code:
        db.session.add(UserInstitution(user_id=user_id, aishe_code=ug_code))
    if pg_code:
        db.session.add(UserInstitution(user_id=user_id, aishe_code=pg_code))
    db.session.commit()
    return redirect("/profile")

@app.route("/edit-colleges")
def edit_colleges():
    if "user_id" not in session:
        return redirect("/login")
    user = db.session.get(User, session["user_id"])
    institutions = Institution.query.order_by(Institution.name).all()
    codes = [link.aishe_code for link in UserInstitution.query.filter_by(user_id=user.id)]
    ug = db.session.get(Institution, codes[0]) if len(codes) > 0 else None
    pg = db.session.get(Institution, codes[1]) if len(codes) > 1 else None
    return render_template("select_college.html", user=user, institutions=institutions,
                           ug_name=ug.name if ug else "", ug_code=ug.aishe_code if ug else "",
                           pg_name=pg.name if pg else "", pg_code=pg.aishe_code if pg else "")

@app.route("/api/suggest")
def suggest():
    q = request.args.get("q", "").strip()
    random_mode = request.args.get("random", "").lower() == "true"
    if random_mode:
        institutions = Institution.query.order_by(func.random()).limit(9).all()
    else:
        institutions = Institution.query.filter(Institution.name.ilike(f"%{q}%")).limit(10).all()
    data = []
    for inst in institutions:
        reviews = Review.query.filter_by(aishe_code=inst.aishe_code).all()
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else None
        data.append({
            "aishe_code": inst.aishe_code,
            "name": inst.name or "",
            "district": inst.district or "",
            "state": inst.state or "",
            "institution_type": inst.institution_type or "",
            "avg_rating": avg_rating
        })
    return data

if __name__ == "__main__":
    app.run(debug=True)
