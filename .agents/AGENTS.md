# Development Rules for AI Agents

## 1. Code Quality, Linting, and Formatting
- **Mandatory Formatting & Linting**: Before completing a task or creating a commit, you must format and verify the code using the project's tools.
- **Using pre-commit**: Run the following command to validate everything (formatting, imports, types) before committing:
  ```bash
  .venv-desktop/bin/pre-commit run --all-files
  ```
- **Test Validation**: Ensure all unit tests pass by running `pytest` before declaring the task complete:
  ```bash
  .venv-desktop/bin/pytest
  ```

## 2. Mandatory Consumption Report
For every user response in this workspace, you must append the consumption report (Consumption report) at the end of your response in the following Markdown format:

### Consumption report
- **Working mode**: direct tools only | single subagent | multiple subagents
- **Tool activity**: N tool calls (list high-cost tools like shell, subagents, web, large reads)
- **Token risk level**: low | medium | high
- **Main cost drivers**: 1-3 bullet points describing what consumed the most
- **Applied optimizations**: token optimizations applied this turn
- exact token count unavailable in this environment
