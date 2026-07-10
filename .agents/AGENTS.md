# Règles de développement pour les agents IA

## 1. Qualité du Code, Linting et Formatage
- **Formatage & Linting obligatoires** : Avant de terminer une tâche ou de créer un commit, vous devez obligatoirement formater et vérifier le code à l'aide des outils du projet.
- **Utilisation de pre-commit** : Exécutez la commande suivante pour tout valider (formatage, imports, types) avant de commiter :
  ```bash
  .venv-desktop/bin/pre-commit run --all-files
  ```
- **Validation des tests** : Assurez-vous que tous les tests unitaires passent en exécutant `pytest` avant de déclarer la tâche terminée :
  ```bash
  .venv-desktop/bin/pytest
  ```
