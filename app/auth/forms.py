from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length

VALIDADORES_DE_EMAIL = [
    DataRequired("Informe o e-mail."),
    Email("E-mail inválido."),
    Length(max=100),
]


class EntrarForm(FlaskForm):
    email = StringField("E-mail", validators=VALIDADORES_DE_EMAIL)
    senha = PasswordField("Senha", validators=[DataRequired("Informe a senha.")])


class CadastrarForm(FlaskForm):
    nome_usuario = StringField(
        "Nome de usuário",
        validators=[DataRequired("Informe o nome de usuário."), Length(max=50)],
    )
    email = StringField("E-mail", validators=VALIDADORES_DE_EMAIL)
    senha = PasswordField(
        "Senha",
        validators=[
            DataRequired("Informe a senha."),
            Length(min=8, message="Use ao menos 8 caracteres."),
        ],
    )
    confirmacao = PasswordField(
        "Confirme a senha",
        validators=[
            DataRequired("Repita a senha."),
            EqualTo("senha", message="As senhas não conferem."),
        ],
    )
