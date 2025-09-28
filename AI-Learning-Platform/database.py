import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('ai_learning_platform.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect('ai_learning_platform.db')
    cursor = conn.cursor()

    # Table: Admins
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        admin_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if any admins exist
    cursor.execute("SELECT 1 FROM admins LIMIT 1")
    if not cursor.fetchone():
        admin_id = "admin001"
        name = "System Administrator"
        email = "admin@school.edu"
        password = "securepassword123"  # Change this in production!
        password_hash = generate_password_hash(password)
        
        cursor.execute(
            "INSERT INTO admins (admin_id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (admin_id, name, email, password_hash)
        )
        print(f"✅ Admin account created with ID: {admin_id}, Email: {email}")

    # Table: Teachers
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teachers (
        teacher_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        created_by TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES admins(admin_id)
    );
    ''')

    # Table: Students
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Table: Progress
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            quiz_score INTEGER NOT NULL,
            max_score INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            topic TEXT NOT NULL,
            num_questions INTEGER NOT NULL,
            answers TEXT NOT NULL,
            question_details TEXT NOT NULL,
            time_taken INTEGER,
            time_per_question INTEGER,
            completion_status TEXT CHECK(completion_status IN ('completed', 'timeout', 'abandoned')),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    ''')

    # Table: Session Activity
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_type TEXT CHECK(user_type IN ('student', 'teacher', 'admin')),
            login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            logout_time DATETIME,
            duration_seconds REAL,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    ''')

    # Table: Quiz Files
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_size INTEGER,
            file_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            quiz_id INTEGER,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (quiz_id) REFERENCES progress(id) ON DELETE SET NULL
        )
    ''')

    # Table: Quiz Questions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            question_text TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
            difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_used DATETIME,
            use_count INTEGER DEFAULT 0
        )
    ''')

    # Table: User Settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            user_type TEXT CHECK(user_type IN ('student', 'teacher', 'admin')),
            quiz_time_per_question INTEGER DEFAULT 30,
            quiz_question_limit INTEGER DEFAULT 10,
            theme_preference TEXT DEFAULT 'light',
            FOREIGN KEY (user_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    ''')

    # Table: Chats (New - to manage chat sessions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id TEXT PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'archived'))
        )
    ''')

    # Table: Chat Participants (New)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_participants (
            chat_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_role TEXT CHECK(user_role IN ('teacher', 'student')),
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')

    # Table: Chat Messages (Updated with soft delete)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            sender_role TEXT NOT NULL CHECK(sender_role IN ('teacher', 'student')),
            sender_id TEXT NOT NULL,
            sender_name TEXT,
            text TEXT,
            file_url TEXT,
            filename TEXT,
            file_size INTEGER,
            duration TEXT DEFAULT '0:00',
            caption TEXT,
            is_typing INTEGER DEFAULT 0,
            is_read INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            deleted_by TEXT,
            deleted_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')

    # Insert sample data
    cursor.execute("INSERT OR IGNORE INTO students (student_id, name, email) VALUES ('STU1001', 'Rishil', 'rishil@example.com')")
    cursor.execute("INSERT OR IGNORE INTO students (student_id, name, email) VALUES ('STU1002', 'Amal', 'amal@example.com')")
    cursor.execute("INSERT OR IGNORE INTO teachers (teacher_id, name, email, created_by) VALUES ('TEA1001', 'Fayiz', 'fayiz@example.com', 'admin001')")
    cursor.execute("INSERT OR IGNORE INTO teachers (teacher_id, name, email, created_by) VALUES ('TEA1002', 'Sneha', 'sneha@example.com', 'admin001')")

    conn.commit()
    conn.close()
    print("✅ Database initialized with all required tables (including enhanced chat features).")

# Chat-specific functions
def clear_chat_messages(chat_id, deleted_by_role, deleted_by_id):
    """
    Soft deletes all messages in a chat
    Returns number of messages marked as deleted
    """
    conn = get_db_connection()
    try:
        result = conn.execute('''
            UPDATE chat_messages 
            SET is_deleted = 1,
                deleted_by = ?,
                deleted_at = CURRENT_TIMESTAMP
            WHERE chat_id = ? AND is_deleted = 0
        ''', (f"{deleted_by_role}:{deleted_by_id}", chat_id))
        
        conn.commit()
        return result.rowcount
    finally:
        conn.close()

def get_chat_messages(chat_id, since=0):
    """
    Get messages for a chat, excluding deleted ones
    """
    conn = get_db_connection()
    try:
        messages = conn.execute('''
            SELECT * FROM chat_messages 
            WHERE chat_id = ? AND id > ? AND is_deleted = 0
            ORDER BY created_at ASC
        ''', (chat_id, since)).fetchall()
        
        return [dict(msg) for msg in messages]
    finally:
        conn.close()

def verify_chat_participant(chat_id, user_id, user_role):
    """
    Verify if user is a participant in the chat
    """
    conn = get_db_connection()
    try:
        participant = conn.execute('''
            SELECT 1 FROM chat_participants 
            WHERE chat_id = ? AND user_id = ? AND user_role = ?
        ''', (chat_id, user_id, user_role)).fetchone()
        
        return participant is not None
    finally:
        conn.close()

def create_chat(participants):
    """
    Create a new chat with participants
    participants = list of tuples (user_id, user_role)
    Returns chat_id
    """
    conn = get_db_connection()
    try:
        chat_id = f"CHAT_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Create chat
        conn.execute('INSERT INTO chats (chat_id) VALUES (?)', (chat_id,))
        
        # Add participants
        for user_id, user_role in participants:
            conn.execute('''
                INSERT INTO chat_participants (chat_id, user_id, user_role)
                VALUES (?, ?, ?)
            ''', (chat_id, user_id, user_role))
        
        conn.commit()
        return chat_id
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()