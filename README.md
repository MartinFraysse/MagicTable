# <PROJECT_NAME>

## 🧭 Overview

Short description of the project.
Explain `what problem it solves` and `why it exists`.

Example:
This project provides a lightweight tool to manage X in an Arch Linux environment.

---

## 🎯 Goals

- Primary goal of the project
- Secondary goals
- Non-goals (what this project intentionally does NOT do)

---

## 🧱 Project Structure

Project layout:

```
./
├── src/        # Source code
├── docs/       # Project documentation
├── .claude/    # Claude Code rules (AI behavior)
├── .vscode/    # VS Code configuration
├── README.md   # Project entry point
└── INIT.md     # Project initialization guide
```

---

## 🛠️ Stack & Environment

- OS: `Arch Linux`
- Shell: `bash`
- Editor: `Visual Studio Code`
- Version control: `git`
- AI assistant: `Claude Code (CLI)`

---

## 🚀 Getting Started

### Prerequisites

- `git`
- `node.js` (installed via `nvm`)
- `claude-code` installed

### Initialization

Initialize the repository:

```
git init
git add .
git commit -m "chore: initial project structure"
```

Open the project in VS Code:

```
code .
```

---

## 🤖 Claude Code Usage

This project uses `Claude Code` as a development assistant.

Rules defining Claude behavior are located in:

`.claude/rules.md`

Key principles:

- Claude is an `assistant`, not an autonomous agent
- Default mode is `read-only`
- All code changes require explicit confirmation

Start Claude manually:

```
claude
```

Or via VS Code task:

`Run Task → Claude Code`

---

## 📚 Documentation

Detailed documentation lives in:

`docs/`

Start with:

`docs/README.md`

---

## 🔐 Git & Workflow

- Clean commit history is expected
- Conventional commit messages are recommended
- Documentation updates should accompany behavior changes

If present, see:

`docs/COMMITS.md`

---

## 📝 Notes

- Design decisions
- Constraints
- Known limitations
- Future improvements

---

## 📄 License

Specify the license here if applicable.
