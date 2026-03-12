from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField, DateField
from wtforms.validators import DataRequired, Email, Length, Regexp, Optional


class RegisterForm(FlaskForm):
    """Formulário de cadastro de novo usuário."""

    nome = StringField('Nome', validators=[DataRequired(), Length(max=150)])
    sobrenome = StringField('Sobrenome', validators=[DataRequired(), Length(max=150)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    cpf = StringField('CPF (somente números)', validators=[
        DataRequired(),
        Length(min=11, max=11, message='CPF deve ter 11 dígitos.'),
        Regexp(r'^\d{11}$', message='Apenas dígitos.')
    ])
    celular = StringField('Celular (com DDD)', validators=[DataRequired()])
    data_nascimento = StringField('Data de Nascimento (dd/mm/aaaa)', validators=[DataRequired()])
    genero = SelectField('Gênero', choices=[
        ('Masculino', 'Masculino'),
        ('Feminino', 'Feminino'),
        ('Personalizado', 'Personalizado')
    ], validators=[DataRequired()])
    submit = SubmitField('Avançar para Captura Facial')


class TaskForm(FlaskForm):
    """Formulário de criação e edição de tarefas."""

    title = StringField('Título', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrição (opcional)', validators=[Length(max=500)])
    priority = SelectField('Prioridade', choices=[
        ('1', '🟢 Baixa'), ('2', '🟡 Média'), ('3', '🔴 Alta'),
    ], default='2', coerce=int)
    # Data limite opcional — o campo aceita string vazia
    due_date = DateField('Data Limite (opcional)', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Salvar Tarefa')
