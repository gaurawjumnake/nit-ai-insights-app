import psycopg2
import pandas as pd
import json
from psycopg2.extras import execute_values

# PostgreSQL connection details
host = 'localhost'
port = 5434
database = 'organizationmanagement'
user = 'postgres'
password = 'Nitor@2025'

conn_params = {
    'host': host,
    'port': port,
    'dbname': database,
    'user': user,
    'password': password
}

TABLE_DATE_COLUMNS = {
    'accounts': ['created_at'],
    'profiles': ['created_at', 'updated_at'],
    'delivery_units': ['created_at'],
    'projects': [
        'ai_recommendations_generated_at',
        'created_at',
        'from_date',
        'to_date',
        'proposal_end_date',
        'expected_win_date'
    ]
}

PROJECTS_SQL_COLUMNS = [
    'id', 'account_id', 'name', 'overview', 'tech_stack',
    'ai_recommendations', 'ai_recommendations_generated_at', 'created_at',
    'ai_direct_hours', 'ai_assist_hours', 'code_coverage_pct', 'expected_revenue',
    'ytd_revenue', 'ai_revenue', 'expected_outcome', 'ai_direct_people',
    'ai_assisted_people', 'ai_assisted_revenue', 'from_date', 'to_date',
    'status', 'proposal_end_date', 'expected_win_date', 'project_type',
    'total_ai_revenue'
]


def clean_tech_stack(value):
    """Convert tech_stack to JSON or None."""
    if pd.isna(value) or value in ["NaN", "None", ""]:
        return None
    try:
        # If already JSON-like, keep it
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        # Try to parse string as JSON
        return json.dumps(json.loads(str(value)))
    except Exception:
        # Treat non-JSON values as plain strings
        return json.dumps({"value": str(value)})


def upload_csv_to_db(csv_file_path, table_name):
    print(f"\n📤 Uploading {csv_file_path} → {table_name} ...")

    try:
        df = pd.read_csv(csv_file_path)

        if table_name == 'projects':
            df = df[[col for col in PROJECTS_SQL_COLUMNS if col in df.columns]]
            print(f"🧩 Projects columns filtered: {df.columns.tolist()}")

            # ✅ Fix tech_stack before upload
            if 'tech_stack' in df.columns:
                df['tech_stack'] = df['tech_stack'].apply(clean_tech_stack)

        # Convert date columns
        for col in TABLE_DATE_COLUMNS.get(table_name, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)

        # Replace NaN and NaT with None
        df = df.replace({pd.NaT: None}).where(pd.notnull(df), None)

        columns = list(df.columns)
        values = [tuple(x) for x in df.to_numpy()]

        insert_query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET
            {', '.join([f"{col}=EXCLUDED.{col}" for col in columns if col != 'id'])};
        """

        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cursor:
                execute_values(cursor, insert_query, values)
                conn.commit()
                print(f"✅ {len(df)} records inserted/updated into {table_name}")

    except Exception as e:
        print(f"❌ Error uploading {csv_file_path}: {e}")


if __name__ == '__main__':
    upload_csv_to_db('backend/data_processor/migration/delivery_units.csv', 'delivery_units')
    upload_csv_to_db('backend/data_processor/migration/accounts.csv', 'accounts')
    upload_csv_to_db('backend/data_processor/migration/profiles.csv', 'profiles')
    upload_csv_to_db('backend/data_processor/migration/projects.csv', 'projects')
