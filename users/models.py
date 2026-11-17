# No models - Schema is managed directly on the production database.
# Pure SQL queries via django.db.connection are used across the application.
# This prevents accidental migrations, DDL executions, or schema modifications.
