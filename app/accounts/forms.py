"""Formulários de autenticação."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    # O allauth aceitava username **ou** e-mail no mesmo campo
    # (ACCOUNT_LOGIN_METHODS); o rótulo diz isso e a view resolve os dois.
    username = StringField("Usuário ou e-mail", validators=[DataRequired()])
    password = PasswordField("Senha", validators=[DataRequired()])


class SignupForm(FlaskForm):
    username = StringField("Usuário", validators=[DataRequired(), Length(max=150)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=254)])
    password1 = PasswordField(
        "Senha", validators=[DataRequired(), Length(min=8, message="Mínimo de 8 caracteres.")]
    )
    password2 = PasswordField(
        "Confirme a senha",
        validators=[DataRequired(), EqualTo("password1", message="As senhas não conferem.")],
    )
