# FaceVault

Gerenciador de tarefas com autenticação facial em 3 etapas.

> Projeto desenvolvido para o XIII JORNACITEC 2024 — UNESP/FCA Botucatu  
> Demonstração de visão computacional aplicada a sistemas web com Python + Flask

## Funcionalidades

- Autenticação em 3 fatores: CPF → Celular → Reconhecimento Facial (LBPH)
- Reconhecimento facial com OpenCV LBPH e detecção anti-spoofing (rejeita mãos, objetos e outros rostos)
- Gerenciamento de tarefas: criar, editar, concluir e excluir tarefas com prioridades
- Dashboard com estatísticas em tempo real via AJAX, sem recarregar a página
- Painel de administração para ativar ou bloquear contas, promover admins e excluir usuários
- Primeiro acesso redirecionado para `/setup` para criação do administrador inicial
- Quatro temas visuais por usuário: Vault, Obsidian, Cyber e Terminal
- Dark mode com toggle persistente e transições suaves
- Interface responsiva para desktop e mobile

## Como executar

```bash
# 1. Clone o repositório
git clone https://github.com/CarlosGabrielModesto/facevault.git
cd facevault

# 2. Crie e ative o ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie o servidor
python app.py
```

Acesse **http://127.0.0.1:5000**. Na primeira execução, o sistema redireciona automaticamente para `/setup` para criar o administrador.

> **Requisito**: Python 3.10+  
> **Câmera**: Necessária para registro e login facial

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.10+, Flask 3.0, SQLAlchemy 2.0 |
| Autenticação | Flask-Login, WTForms, bcrypt |
| Visão Computacional | OpenCV (LBPH Face Recognizer), NumPy |
| Frontend | HTML5, CSS3 (Design System próprio), JavaScript ES2022 |
| Banco de dados | SQLite (desenvolvimento) |

## Estrutura do projeto

```text
facevault/
├── app.py                  # Application factory + first-run redirect
├── config.py               # Configurações
├── models.py               # User, Task (SQLAlchemy ORM)
├── forms.py                # Validação com WTForms
├── requirements.txt
├── routes/
│   ├── auth.py             # Login, registro e captura facial
│   ├── tasks.py            # CRUD de tarefas + toggle AJAX
│   ├── admin.py            # Painel de administração
│   ├── profile.py          # Edição de perfil e re-captura facial
│   └── setup.py            # First-run wizard (desaparece após uso)
├── services/
│   └── face_service.py     # LBPH Face Recognizer isolado
├── templates/              # Jinja2
│   ├── base.html           # Navbar, dark mode, modais, orbs
│   ├── index.html          # Dashboard principal
│   ├── admin/
│   │   └── dashboard.html  # Painel admin
│   └── ...
└── static/
    ├── css/
    │   ├── style.css       # Design System base
    │   ├── theme-vault.css
    │   ├── theme-obsidian.css
    │   ├── theme-cyber.css
    │   └── theme-terminal.css
    └── js/
```

## Temas visuais

Cada usuário pode escolher o tema na página de perfil. O tema é salvo no banco de dados e aplicado automaticamente no próximo login.

| Tema | Cor principal | Estilo |
|---|---|---|
| **Vault** | Verde-esmeralda `#10b981` | Padrão — segurança e biometria |
| **Obsidian** | Azul corporativo `#2563eb` | Elegante e sofisticado |
| **Cyber** | Sky Blue `#0ea5e9` | Grid animado + scanner biométrico |
| **Terminal** | Zinc `#0284c7` | Visual de software, bordas retas |

## Segurança

- Senhas com hash bcrypt
- CSRF protection em todos os formulários (Flask-WTF)
- Reconhecimento facial com threshold calibrado (`LBPH_THRESHOLD = 75.0`)
- Detecção anti-spoofing: `minNeighbors=6`, `minSize=(100,100)`, validação de aspect ratio
- Banco de dados e imagens faciais **nunca versionados** (`.gitignore`)
- Verificação de propriedade em todas as rotas de tarefa (o usuário acessa apenas os próprios dados)

## Autor

**Carlos Gabriel dos Santos Modesto**  
Mestrando em Engenharia Agrícola — UNESP/FCA Botucatu  
Engenheiro de Computação — Faculdade Galileu (2024)  
Bolsista CNPq

[Lattes](http://lattes.cnpq.br/9699036690474846)  
[LinkedIn](https://linkedin.com/in/SEU-LINKEDIN)

## Licença

MIT — livre para estudar, modificar e usar como referência.
