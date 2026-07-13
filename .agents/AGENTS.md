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

## 2. Rapport de consommation obligatoire
Pour chaque réponse utilisateur dans cet espace de travail, vous devez obligatoirement ajouter le rapport de consommation (Consumption report) à la fin de votre réponse au format Markdown suivant :

### Rapport de consommation
- **Mode de travail**: direct tools only | single subagent | multiple subagents
- **Activité outils**: N tool calls (list high-cost tools like shell, subagents, web, large reads)
- **Niveau de risque tokens**: low | medium | high
- **Principaux postes de coût**: 1-3 puces décrivant ce qui a consommé le plus
- **Optimisations appliquées**: optimisations de tokens appliquées ce tour
- exact token count unavailable in this environment
