import psycopg2
from psycopg2 import sql

# Database connection details
host = 'localhost'
port = 5434  
database = 'organizationmanagement'
user = 'postgres'
password = 'Nitor@2025'

# Connection string
conn_params = {
    'host': host,
    'port': port,
    'dbname': database,
    'user': user,
    'password': password
}

# SQL statements
create_table_queries = [
    # Drop tables (in dependency order)
    """DROP TABLE IF EXISTS projects CASCADE;""",
    """DROP TABLE IF EXISTS accounts CASCADE;""",
    """DROP TABLE IF EXISTS profiles CASCADE;""",
    """DROP TABLE IF EXISTS delivery_units CASCADE;""",

    # Create delivery_units
    """
    CREATE TABLE delivery_units (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # Create accounts
    """
    CREATE TABLE accounts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        customer_overview TEXT NULL,
        delivery_unit_id UUID NOT NULL,
        ai_recommendations TEXT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        account_manager VARCHAR(255) NULL,
        FOREIGN KEY (delivery_unit_id) REFERENCES delivery_units(id) ON DELETE CASCADE
    );
    """,

    # Create profiles
    """
    CREATE TABLE profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        avatar_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # Create projects
    """
    CREATE TABLE projects (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        overview TEXT,
        tech_stack JSONB,
        ai_recommendations TEXT,
        ai_recommendations_generated_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        ai_direct_hours DOUBLE PRECISION,
        ai_assist_hours DOUBLE PRECISION,
        code_coverage_pct DOUBLE PRECISION,
        expected_revenue NUMERIC(18,2),
        ytd_revenue NUMERIC(18,2),
        ai_revenue NUMERIC(18,2),
        expected_outcome TEXT,
        ai_direct_people INT,
        ai_assisted_people INT,
        ai_assisted_revenue NUMERIC(18,2),
        from_date TIMESTAMP,
        to_date TIMESTAMP,
        status VARCHAR(50),
        proposal_end_date TIMESTAMP,
        expected_win_date TIMESTAMP,
        project_type VARCHAR(50),
        total_ai_revenue NUMERIC(18,2)
    );
    """
]


def create_tables():
    """Drops and recreates tables in PostgreSQL"""
    try:
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cursor:
                print("Creating tables in PostgreSQL...")
                for query in create_table_queries:
                    cursor.execute(query)
                conn.commit()
                print("✅ Tables created successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")


if __name__ == '__main__':
    create_tables()
