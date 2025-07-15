from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  linkedin_id = db.Column(db.String, unique=True, nullable=False)
  name = db.Column(db.String, nullable=False)
  email = db.Column(db.String, nullable=False)
  photo_url = db.Column(db.String(512))  # ✅ NEW

  reviews = db.relationship("Review", backref="user", lazy=True)
  institutions = db.relationship("UserInstitution", backref="user", lazy=True)

class Institution(db.Model):
  aishe_code = db.Column(db.String, primary_key=True)
  name = db.Column(db.String)
  state = db.Column(db.String)
  district = db.Column(db.String)
  institution_type = db.Column(db.String)
  website = db.Column(db.String)

class Review(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
  aishe_code = db.Column(db.String, db.ForeignKey("institution.aishe_code"), nullable=False)
  rating = db.Column(db.Integer, nullable=False)
  title = db.Column(db.String(100))
  body = db.Column(db.String(500))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

  institution = db.relationship("Institution")

class UserInstitution(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
  aishe_code = db.Column(db.String, db.ForeignKey("institution.aishe_code"), nullable=False)
