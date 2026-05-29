# ICT Help Desk

## 🛠️ Local Setup

1. **Clone the repository**
```bash
   git clone https://github.com/vincentkyalomusembi/ICT-Help-Desk-neon.git
   cd ICT-Help-Desk-neon
```

2. **Create and activate virtual environment**
```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Mac/Linux
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Set up environment variables**
   - Create `.env` and fill in with values from the team lead

---

## 🚀 Running the Dev Server

```bash
fastapi dev app/main.py
```

The API will be available at `http://127.0.0.1:8000`  
Interactive docs at `http://127.0.0.1:8000/docs`

---

## 🌿 Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production — stable, tested code only |
| `dev` | Development — all PRs merge here |
| `Anthony` | Anthony's working branch |
| `Vincent` | Vincent's working branch |

---

## 📅 Daily Workflow

1. **Switch to your branch**
```bash
   git checkout Anthony  # or your branch name
```

2. **Pull latest changes from dev**
```bash
   git pull origin dev
```

3. **Do your work and commit**
```bash
   git add .
   git commit -m "describe what you did"
```

4. **Push to your branch**
```bash
   git push origin Anthony  # or your branch name
```

5. **Open a Pull Request** on GitHub from your branch → `dev`

---

## ⚠️ Rules

- ❌ Never push directly to `dev` or `main`
- ❌ Never merge your own Pull Request without review
- ✅ Always be on your own branch before making changes
- ✅ Always pull from `dev` at the start of each day