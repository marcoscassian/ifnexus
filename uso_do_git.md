
# Fluxo Básico de GitHub

## 1️⃣ Configuração Inicial
Clonar repositório remoto para sua máquina:

```bash
git clone git@github.com:usuario/repositorio.git
cd repositorio
````

Configurar nome e e-mail do Git (opcional):

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@users.noreply.github.com"
```

---

## 2️⃣ Receber alterações do GitHub (Pull)

Antes de começar a editar:

```bash
git pull origin main --rebase
```

* `main` = branch principal
* `--rebase` evita merges desnecessários

---

## 3️⃣ Fazer alterações

Edite, crie ou exclua arquivos normalmente.
Verifique o status das alterações:

```bash
git status
```

---

## 4️⃣ Adicionar alterações para o commit

Adicionar todos os arquivos modificados:

```bash
git add .
```

Adicionar arquivos específicos:

```bash
git add caminho/do/arquivo
```

---

## 5️⃣ Criar um commit

```bash
git commit -m "Mensagem curta descrevendo a alteração"
```

> Exemplo: `"Corrige bug no login"` ou `"Atualiza README"`

---

## 6️⃣ Enviar alterações para o GitHub (Push)

```bash
git push origin main
```

> Se aparecer erro de rejeição, faça:

```bash
git pull --rebase
git push origin main
```

---

## 7️⃣ Ignorar arquivos/pastas

Crie um arquivo `.gitignore` na raiz do projeto:

```
venv/
__pycache__/
.env
*.log
```

Se já enviou algo que quer ignorar:

```bash
git rm -r --cached pasta_ou_arquivo
git commit -m "Remove arquivos ignorados"
git push origin main
```

---

## 💡 Dicas

* Sempre faça **pull antes de editar**
* Commitar frequentemente mantém o histórico limpo
* Use **SSH** ou **Git Credential Manager** para não precisar digitar senha/token sempre
