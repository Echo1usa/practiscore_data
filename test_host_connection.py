import pymysql

DB_HOST = "gator4033.hostgator.com"   # or "localhost" if running inside HostGator
DB_USER = "wycoprl3_dbbot"        # replace with your actual cPanel-prefixed user
DB_PASS = "Ab7!tX9%Qz_4Kc3&"
DB_NAME = "wycoprl3_all_shooters"           # replace with your actual cPanel-prefixed db name

try:
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cursor = conn.cursor()
    cursor.execute("SELECT NOW()")
    print("✅ Connected! Server time is:", cursor.fetchone()[0])
    conn.close()
except Exception as e:
    print("❌ Failed:", e)
