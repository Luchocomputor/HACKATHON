from flask import Flask
from flask import render_template
from flask import request, jsonify, redirect, url_for
from src.utils.ask_question_to_pdf import ask_question_to_pdf, read_pdf, split_text, read_txt
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Configure le dossier d'upload
app.config["UPLOAD_FOLDER"] = "uploads/"
# Nom du dossier pour stocker les fichiers
app.config["MAX_CONTENT_LENGTH"] = (
    16 * 1024 * 1024
)  # Taille maximale de fichier acceptée (16 Mo)

# S'assurer que le répertoire existe
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])


class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dark_mode = db.Column(db.Boolean, default=False)


# Ensure tables are created
with app.app_context():
    db.create_all()

filename = os.path.join(os.path.dirname(__file__), "filename.pdf")
document = read_pdf(filename)
chunks = split_text(document)

course_content = chunks[0]







@app.route("/")
def home(name=None):
    return render_template("index.html")


@app.route("/prompt", methods=["POST"])
def prompt():
    # Call your function for processing the prompt
    response = jsonify({"answer": ask_question_to_pdf(request.form["prompt"])})
    return response


@app.route("/set-preference", methods=["POST"])
def set_preference():
    dark_mode = request.form.get("dark_mode") == "true"
    # Upsert the dark mode preference (insert or update)
    user_preference = UserPreference.query.first()
    if user_preference:
        user_preference.dark_mode = dark_mode
    else:
        user_preference = UserPreference(dark_mode=dark_mode)
        db.session.add(user_preference)
    db.session.commit()
    return jsonify({"message": "Preference saved"})


@app.route("/get-preference", methods=["GET"])
def get_preference():
    user_preference = UserPreference.query.first()
    if user_preference:
        return jsonify({"dark_mode": user_preference.dark_mode})
    else:
        return jsonify({"dark_mode": False})


@app.route("/question", methods=["POST"])
def generate_question():
    return {
        "answer": ask_question_to_pdf(
            "Pose moi une question sur le cours suivant puis APRES que l'utilisateur ait donné sa réponse dis lui si cette derniere est correcte :"  # noqa: E501
            + course_content
        )
    }


# Affichage du formulaire


@app.route("/upload-course", methods=["GET", "POST"])
def upload_course():
    global course_content  # Permet de modifier la variable globale
    if request.method == "POST":
        # Vérifie si un fichier est bien présent dans la requête
        if "file" not in request.files:
            return "No file part in the request", 400

        file = request.files["file"]

        # Vérifie si un fichier a été sélectionné
        if file.filename == "":
            return "No file selected", 400

        if file:
            # Sécurise le nom du fichier
            filename = secure_filename(file.filename)
            # Construit le chemin complet vers le dossier d'upload
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            # Sauvegarde le fichier dans le répertoire configuré
            file.save(filepath)

            if filename.lower().endswith('.pdf'):
                # Lire et traiter le fichier PDF uploadé
                document = read_pdf(filepath)
                chunks = split_text(document)

            if filename.lower().endswith('.txt'):
                # Lire et traiter le fichier PDF uploadé
                document = read_txt(filepath)
                chunks = split_text(document)

            # Mettre à jour la variable course_content avec le contenu du fichier uploadé
            course_content = chunks[0]

            # Redirige vers une page de confirmation ou affiche un message de succès
            return redirect(url_for("course_uploaded", filename=filename))

    return render_template("upload_course.html")


# Pour confirmer l'upload


@app.route("/course-uploaded/<filename>")
def course_uploaded(filename):
    return f"Course '{filename}' uploaded successfully!"


if __name__ == "__main__":
    app.run(debug=True)
