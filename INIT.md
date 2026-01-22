# Project Initialization

Steps to create a new project from this template.

1. Copy the template directory and rename it to the project name.

2. Initialize Git:
   - git init
   - git add .
   - git commit -m "chore: initial project structure"

3. Create the remote repository using GitHub CLI:
   - gh repo create <project-name> --private --source=. --remote=origin --push

4. Open the project in VS Code:
   - code .

5. Update documentation:
   - Edit README.md (project name and description)
   - Edit docs/README.md (project purpose)

6. Start coding in src/.

7. Use Claude Code when needed:
   - Run `claude`
   - Or use VS Code task: Run Task → Claude Code

---

PS:
A helper command `project create <project_name>` may be available.
This command automates all the steps above (template copy, git init,
remote creation, first push, and VS Code launch).
