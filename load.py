import json
from app import app
from models import db, Institution

with app.app_context():
    try:
        db.create_all()
        with open("institutions.json") as f:
            data = json.load(f)
        for i in data:
            try:
                if not Institution.query.get(i["aisheCode"]):
                    db.session.add(Institution(
                        aishe_code=i["aisheCode"],
                        name=i["name"],
                        state=i.get("stateName", ""),
                        district=i.get("districtName", ""),
                        institution_type=i.get("institutionType", ""),
                        website=i.get("webSite", "")
                    ))
            except Exception as e:
                print(f"❌ Error inserting {i.get('aisheCode')}: {e}")
        db.session.commit()
        print("✅ Institutions loaded successfully.")
    except Exception as e:
        print(f"❌ Failed to load institutions: {e}")
