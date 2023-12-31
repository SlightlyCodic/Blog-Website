import os
from datetime import date
from functools import wraps
from dotenv import load_dotenv, find_dotenv
from flask import Flask, render_template, redirect, url_for, abort, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import LoginManager, UserMixin, current_user, logout_user, login_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from Form import LoginForm, RegisterForm, ContactForm, CreatePostForm


def create_app():
    app = Flask(__name__)
    load_dotenv(find_dotenv())
    database = os.getenv("DATABASE")


    app.config['SECRET_KEY'] = 'boobs'
    app.config['SQLALCHEMY_DATABASE_URI'] = database
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    bootstrap = Bootstrap(app)
    ckeditor = CKEditor(app)
    gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)


    db =SQLAlchemy(app)
    login_manager = LoginManager(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    class User(UserMixin, db.Model):
        __tablename__ = "users"
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(100), unique=True, nullable=False)
        email = db.Column(db.String(100), nullable=False)
        password = db.Column(db.String(100), nullable=False)
        posts = relationship("BlogPost", back_populates="author")

    class BlogPost(db.Model):
        __tablename__ = "blog_posts"
        id = db.Column(db.Integer, primary_key=True)
        author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
        author = relationship("User", back_populates="posts")
        title = db.Column(db.String(250), unique=True, nullable=False)
        subtitle = db.Column(db.String(250), nullable=False)
        date = db.Column(db.String(250), nullable=False)
        body = db.Column(db.Text, nullable=False)
        img_url = db.Column(db.String(250), nullable=False)

    # Run only once
    # with app.app_context():
    #     db.create_all()

    def admin_only(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.id != 1:
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function


    @app.route('/')
    def home_page():
        return render_template('index.html',current_user=current_user)

    @app.route("/allposts")
    def get_all_post():
        posts = BlogPost.query.all()
        return render_template('all_posts.html',all_posts=posts,current_user=current_user)


    @app.route('/Login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data
            user_exist = User.query.filter_by(email=email).first()

            if not user_exist:
                flash("That email does not exist, please try again.")
                return redirect(url_for('login'))
            elif not check_password_hash(user_exist.password, password):
                flash('Password incorrect, please try again.')
                return redirect(url_for('login'))
            else:
                login_user(user_exist)
                return redirect(url_for('get_all_post',current_user=current_user))
        return render_template('login.html', form=form,current_user=current_user)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():

            if User.query.filter_by(email=form.email.data).first():
                flash("Account already exist with the Email")
                return redirect(url_for('login'))

            elif not User.query.filter_by(email=form.email.data).first() and User.query.filter_by(username=form.username.data).first():
                flash("Username already exists choose another")
                return redirect(url_for("register"))


            hash_and_salted_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256',
                salt_length=8
            )

            new_user = User(
                username=form.username.data,
                email= form.email.data,
                password=hash_and_salted_password,
            )

            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)

            return redirect(url_for('get_all_post',current_user=current_user))

        return render_template('register.html', form=form,current_user=current_user)

    @app.route("/contact",methods=["GET","POST"])
    def contact():
        form = ContactForm()
        messagesent=False
        if form.validate_on_submit():
            Name = form.name.data,
            Email = form.email.data,
            Message = form.message.data,
            messagesent = True;

            redirect(url_for("contact", messagesent=messagesent, form=form))
        return render_template("contact.html", form=form, current_user=current_user, messagesent=messagesent)



    @app.route("/post/<int:post_id>", methods=["GET", "POST"])
    def show_post(post_id):
        requested_post = BlogPost.query.get(post_id)

        return render_template("post.html", post=requested_post, current_user=current_user)



    @app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
    @admin_only
    def edit_post(post_id):
        post = BlogPost.query.get(post_id)
        edit_form = CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            img_url=post.img_url,
            author=current_user,
            body=post.body
        )
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))
        return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)

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
                author=current_user,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_post"))

        return render_template("make-post.html", form=form, current_user=current_user)

    @app.route("/delete/<int:post_id>")
    @admin_only
    def delete_post(post_id):
        post_to_delete = db.get_or_404(BlogPost, post_id)
        db.session.delete(post_to_delete)
        db.session.commit()
        return redirect(url_for('get_all_post'))

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('home_page'))

    return app
