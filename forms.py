from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, IntegerField
from wtforms.validators import DataRequired, URL, Email, EqualTo
from flask_ckeditor import CKEditorField


##WTForm
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class CreateRegisterForm(FlaskForm):
    name = StringField("First Name", validators=[DataRequired()])
    surname = StringField("Last Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password",
                             validators=[DataRequired(), EqualTo("second_password", message="Passwords must match")])
    second_password = PasswordField("Repeat password",
                                    validators=[DataRequired(), EqualTo("password", message="Passwords must match")])
    submit = SubmitField("Sign Me Up!")


class CreateLoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class CreateCommentForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")


class EditImageWeek(FlaskForm):
    week = IntegerField("Week #", validators=[DataRequired()])
    submit = SubmitField("Update")
