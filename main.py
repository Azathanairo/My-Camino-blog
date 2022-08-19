from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, CreateRegisterForm, CreateLoginForm, CreateCommentForm
from flask_gravatar import Gravatar
from functools import wraps
from dotenv import load_dotenv
from random import choice
import requests
import os

load_dotenv()

CONTENTFUL_ENDPOINT = "https://cdn.contentful.com"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None
                    )


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    surname = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    # author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    post = relationship("BlogPost", back_populates="comments")


class Image(db.Model):
    __tablename__ = "gallery"
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False)
    created = db.Column(db.String, nullable=False)
    filepath = db.Column(db.Text, nullable=True)


db.create_all()


# CREATE ADMIN DECORATOR
def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return function(*args, **kwargs)

    return wrapper_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, is_logged=current_user.is_authenticated)


@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = CreateRegisterForm()
    if register_form.validate_on_submit():
        if User.query.filter_by(email=request.form["email"]).first():
            flash(message="You've already signed up with this email. Please login instead.")
            return redirect(url_for('login', email=request.form["email"]))
        password_salted_hashed = generate_password_hash(
            password=request.form["password"],
            method="pbkdf2:sha256",
            salt_length=8
        )
        new_user = User(
            name=request.form["name"],
            surname=request.form["surname"],
            email=request.form["email"],
            password=password_salted_hashed,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=register_form, is_logged=current_user.is_authenticated)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = CreateLoginForm()
    if request.method == "GET":
        login_email = request.args.get("email")
        login_form.email.data = login_email
    if login_form.validate_on_submit():
        user = User.query.filter_by(email=request.form["email"]).first()
        if not user:
            flash(message="This user does not exist. Register or login with different email.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, request.form["password"]):
            flash(message="Incorrect password.")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=login_form, is_logged=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash(message="You need to login or register to comment.")
            return redirect(url_for('login'))
        new_comment = Comment(
            text=request.form["comment"],
            comment_author=current_user,
            post=requested_post,
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    return render_template("post.html", post=requested_post, form=comment_form, is_logged=current_user.is_authenticated)


@app.route("/gallery")
def get_all_images():
    with requests.get(f"{CONTENTFUL_ENDPOINT}/spaces/{os.environ.get('SPACE_ID')}/environments/master/assets",
                      headers={"Authorization": f"Bearer {os.environ.get('DELIVERY_API_KEY')}"}) as response:
        content = response.json()
    images = [url["fields"]["file"]["url"] for url in content["items"]]
    rnd_image = choice(images)
    return render_template('gallery.html', files=images, is_logged=current_user.is_authenticated, bg_image=rnd_image)


@app.route("/update_gallery")
def update_gallery():
    # TODO 1 dodělat tlačítko  na update databáze s obrázky (omezí se tím počet requestů na API při každém otevření
    #  galerie)
    pass


@app.route("/archive")
def archive_images():
    # TODO 1 dodělat tlačítko  na archivování obrázků do nové složky
    pass


@app.route("/location")
def show_location():
    pass


@app.route("/about")
def about():
    return render_template("about.html", is_logged=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", is_logged=current_user.is_authenticated)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, is_logged=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/delete/<int:post_id>/<int:comment_id>")
@admin_only
def delete_comment(comment_id, post_id):
    comment_to_delete = Comment.query.get(comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post_id))


if __name__ == "__main__":
    app.run(debug=True)
