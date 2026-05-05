import psycopg2

conn = psycopg2.connect(
    host="db.dbsrjjdvbaxrcbdyiirv.supabase.co",
    database="postgres",
    user="postgres",
    password="SecureData2026Vault",
    port=5432,
    sslmode="require"
)

cursor = conn.cursor()

# Columns add karo
cursor.execute("ALTER TABLE user_user ADD COLUMN IF NOT EXISTS plan VARCHAR(100) NULL;")
cursor.execute("ALTER TABLE user_user ADD COLUMN IF NOT EXISTS nutritionist_type VARCHAR(20) NULL;")

conn.commit()
cursor.close()
conn.close()

print("✅ Columns successfully add ho gaye!")