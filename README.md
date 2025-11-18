# Meu Projeto Django

Uma aplicação Django moderna com estrutura completa de templates HTML, Bootstrap 5 e design responsivo.

## 🚀 Estrutura do Projeto

```
teset2/
├── app/                          # Aplicação principal
│   ├── templates/               # Templates HTML
│   │   ├── base.html           # Template base com navegação
│   │   ├── home.html           # Página inicial
│   │   ├── about.html          # Página sobre
│   │   ├── contact.html        # Página de contato
│   │   └── services.html       # Página de serviços
│   ├── views.py                # Views das páginas
│   ├── urls.py                 # URLs da aplicação
│   └── ...
├── static/                      # Arquivos estáticos
│   ├── css/
│   │   └── style.css           # Estilos customizados
│   ├── js/
│   │   └── main.js             # JavaScript customizado
│   └── images/                 # Imagens do projeto
├── projeto/                     # Configurações do projeto
│   ├── settings.py             # Configurações Django
│   └── urls.py                 # URLs principais
└── manage.py                   # Script de gerenciamento Django
```

## 📋 Páginas Disponíveis

- **Home** (`/`) - Página inicial com hero section e estatísticas
- **Sobre** (`/about/`) - Informações sobre o projeto e equipe
- **Contato** (`/contact/`) - Formulário de contato funcional
- **Serviços** (`/services/`) - Lista de serviços oferecidos
- **Admin** (`/admin/`) - Painel administrativo do Django

## 🎨 Recursos de Design

- **Bootstrap 5** - Framework CSS moderno e responsivo
- **Font Awesome** - Ícones vetoriais
- **Design Responsivo** - Funciona em todos os dispositivos
- **Animações CSS** - Transições suaves e efeitos visuais
- **Tema Customizado** - Cores e estilos personalizados

## 🛠️ Tecnologias Utilizadas

- **Django 5.2.7** - Framework web Python
- **Bootstrap 5.3.0** - Framework CSS
- **Font Awesome 6.0.0** - Ícones
- **JavaScript ES6** - Funcionalidades interativas
- **SQLite** - Banco de dados (desenvolvimento)

## 🚀 Como Executar

1. **Instalar dependências:**
   ```bash
   pip install django
   ```

2. **Executar migrações:**
   ```bash
   python manage.py migrate
   ```

3. **Criar superusuário (opcional):**
   ```bash
   python manage.py createsuperuser
   ```

4. **Executar servidor:**
   ```bash
   python manage.py runserver
   ```

5. **Acessar no navegador:**
   - Site: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## 📱 Funcionalidades

### Página Inicial
- Hero section com call-to-action
- Cards de recursos principais
- Seção de estatísticas
- Design moderno e atrativo

### Página Sobre
- História da empresa/projeto
- Missão, visão e valores
- Informações da equipe
- Layout profissional

### Página de Contato
- Formulário de contato funcional
- Validação client-side e server-side
- Informações de contato
- Links para redes sociais
- Integração com sistema de e-mail

### Página de Serviços
- Lista detalhada de serviços
- Processo de trabalho
- Call-to-action para contato
- Design organizado e profissional

## 🎯 Próximos Passos

Para expandir o projeto, você pode:

1. **Adicionar mais páginas** - Criar novos templates e views
2. **Implementar banco de dados** - Criar models para dados dinâmicos
3. **Sistema de usuários** - Autenticação e perfis
4. **API REST** - Django REST Framework
5. **Deploy** - Configurar para produção

## 📝 Personalização

### Cores e Tema
Edite o arquivo `static/css/style.css` para personalizar:
- Cores principais
- Tipografia
- Espaçamentos
- Animações

### Conteúdo
Modifique os templates em `app/templates/` para:
- Alterar textos
- Adicionar seções
- Modificar layout
- Incluir novas funcionalidades

### Funcionalidades
Adicione novas views em `app/views.py` e URLs em `app/urls.py` para:
- Novas páginas
- APIs
- Funcionalidades específicas

## 🔧 Configurações Importantes

- **Static Files**: Configurados para desenvolvimento
- **Email**: Configurado para console (desenvolvimento)
- **Database**: SQLite (pode ser alterado para PostgreSQL/MySQL)
- **Language**: Português brasileiro
- **Timezone**: America/Sao_Paulo

## 📞 Suporte

Para dúvidas ou sugestões, entre em contato através da página de contato do site ou abra uma issue no repositório.
