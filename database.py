"""
Database manager for SQLite
"""
import aiosqlite
import json
from datetime import datetime
from config import Config

class Database:
    def __init__(self):
        self.db_path = Config.DB_PATH

    async def init(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Guild members table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    discord_id INTEGER PRIMARY KEY,
                    username TEXT,
                    nickname TEXT,
                    role TEXT DEFAULT 'C',
                    joined_date TEXT,
                    checkin_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    last_checkin TEXT,
                    total_checkins INTEGER DEFAULT 0
                )
            """)

            # Damage submissions - Co-op
            await db.execute("""
                CREATE TABLE IF NOT EXISTS coop_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id INTEGER,
                    date TEXT,
                    damage REAL,
                    boss_name TEXT,
                    proof_url TEXT,
                    submitted_at TEXT,
                    edited BOOLEAN DEFAULT 0,
                    edited_by TEXT,
                    FOREIGN KEY (discord_id) REFERENCES members(discord_id)
                )
            """)

            # Damage submissions - Guild Challenge
            await db.execute("""
                CREATE TABLE IF NOT EXISTS gc_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id INTEGER,
                    date TEXT,
                    damage REAL,
                    boss_name TEXT,
                    proof_url TEXT,
                    submitted_at TEXT,
                    edited BOOLEAN DEFAULT 0,
                    edited_by TEXT,
                    FOREIGN KEY (discord_id) REFERENCES members(discord_id)
                )
            """)

            # Events table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    event_type TEXT,
                    scheduled_time TEXT,
                    created_by INTEGER,
                    status TEXT DEFAULT 'active'
                )
            """)

            # Event participants
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    discord_id INTEGER,
                    role TEXT,
                    character TEXT,
                    confirmed BOOLEAN DEFAULT 0,
                    FOREIGN KEY (event_id) REFERENCES events(event_id)
                )
            """)

            # Member rosters (owned characters)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS member_roster (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id INTEGER,
                    character_id TEXT,
                    boundary TEXT,
                    FOREIGN KEY (discord_id) REFERENCES members(discord_id)
                )
            """)

            # Tier list cache
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tierlist_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    tier TEXT,
                    character_id TEXT,
                    explanation TEXT,
                    updated_by TEXT,
                    updated_at TEXT
                )
            """)

            await db.commit()

    # Member management
    async def get_or_create_member(self, discord_id, username, nickname=None):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM members WHERE discord_id = ?", (discord_id,)
            )
            member = await cursor.fetchone()

            if not member:
                await db.execute(
                    "INSERT INTO members (discord_id, username, nickname, joined_date) VALUES (?, ?, ?, ?)",
                    (discord_id, username, nickname or username, datetime.now().isoformat())
                )
                await db.commit()
                return await self.get_member(discord_id)
            return member

    async def get_member(self, discord_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM members WHERE discord_id = ?", (discord_id,)
            )
            return await cursor.fetchone()

    async def update_member_role(self, discord_id, role):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE members SET role = ? WHERE discord_id = ?",
                (role, discord_id)
            )
            await db.commit()

    # Check-in system
    async def checkin(self, discord_id):
        from utils.helpers import get_today_date, has_reset_occurred

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT last_checkin, checkin_streak, longest_streak, total_checkins FROM members WHERE discord_id = ?",
                (discord_id,)
            )
            result = await cursor.fetchone()

            if not result:
                return None, "Member not found"

            last_checkin, streak, longest, total = result
            today = get_today_date()

            if last_checkin == today:
                return None, "Already checked in today!"

            # Calculate new streak
            if last_checkin and not has_reset_occurred(last_checkin):
                streak += 1
            else:
                streak = 1

            if streak > longest:
                longest = streak

            total += 1

            await db.execute(
                "UPDATE members SET last_checkin = ?, checkin_streak = ?, longest_streak = ?, total_checkins = ? WHERE discord_id = ?",
                (today, streak, longest, total, discord_id)
            )
            await db.commit()

            return {
                'streak': streak,
                'longest': longest,
                'total': total
            }, None

    async def get_checkin_leaderboard(self, limit=10):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT username, checkin_streak, longest_streak, total_checkins FROM members ORDER BY checkin_streak DESC LIMIT ?",
                (limit,)
            )
            return await cursor.fetchall()

    # Co-op submissions
    async def submit_coop(self, discord_id, damage, boss_name, proof_url):
        from utils.helpers import get_today_date

        async with aiosqlite.connect(self.db_path) as db:
            # Check if already submitted today
            today = get_today_date()
            cursor = await db.execute(
                "SELECT id FROM coop_submissions WHERE discord_id = ? AND date = ?",
                (discord_id, today)
            )
            if await cursor.fetchone():
                return None, "Already submitted co-op damage today!"

            await db.execute(
                "INSERT INTO coop_submissions (discord_id, date, damage, boss_name, proof_url, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
                (discord_id, today, damage, boss_name, proof_url, datetime.now().isoformat())
            )
            await db.commit()

            cursor = await db.execute("SELECT last_insert_rowid()")
            submission_id = (await cursor.fetchone())[0]
            return submission_id, None

    async def get_coop_submission(self, discord_id, date=None):
        from utils.helpers import get_today_date
        if date is None:
            date = get_today_date()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM coop_submissions WHERE discord_id = ? AND date = ?",
                (discord_id, date)
            )
            return await cursor.fetchone()

    async def get_coop_leaderboard(self, date=None):
        from utils.helpers import get_today_date
        if date is None:
            date = get_today_date()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT s.discord_id, m.username, s.damage, s.boss_name, s.proof_url, s.edited 
                   FROM coop_submissions s 
                   JOIN members m ON s.discord_id = m.discord_id 
                   WHERE s.date = ? 
                   ORDER BY s.damage DESC""",
                (date,)
            )
            return await cursor.fetchall()

    async def edit_coop(self, discord_id, new_damage, edited_by):
        from utils.helpers import get_today_date

        async with aiosqlite.connect(self.db_path) as db:
            today = get_today_date()
            await db.execute(
                "UPDATE coop_submissions SET damage = ?, edited = 1, edited_by = ? WHERE discord_id = ? AND date = ?",
                (new_damage, edited_by, discord_id, today)
            )
            await db.commit()
            return True

    async def delete_coop(self, discord_id, date=None):
        from utils.helpers import get_today_date
        if date is None:
            date = get_today_date()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM coop_submissions WHERE discord_id = ? AND date = ?",
                (discord_id, date)
            )
            await db.commit()
            return True

    # Guild Challenge submissions (same structure as co-op)
    async def submit_gc(self, discord_id, damage, boss_name, proof_url):
        from utils.helpers import get_today_date

        async with aiosqlite.connect(self.db_path) as db:
            today = get_today_date()
            cursor = await db.execute(
                "SELECT id FROM gc_submissions WHERE discord_id = ? AND date = ?",
                (discord_id, today)
            )
            if await cursor.fetchone():
                return None, "Already submitted guild challenge damage today!"

            await db.execute(
                "INSERT INTO gc_submissions (discord_id, date, damage, boss_name, proof_url, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
                (discord_id, today, damage, boss_name, proof_url, datetime.now().isoformat())
            )
            await db.commit()

            cursor = await db.execute("SELECT last_insert_rowid()")
            submission_id = (await cursor.fetchone())[0]
            return submission_id, None

    async def get_gc_submission(self, discord_id, date=None):
        from utils.helpers import get_today_date
        if date is None:
            date = get_today_date()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM gc_submissions WHERE discord_id = ? AND date = ?",
                (discord_id, date)
            )
            return await cursor.fetchone()

    async def get_gc_leaderboard(self, date=None):
        from utils.helpers import get_today_date
        if date is None:
            date = get_today_date()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT s.discord_id, m.username, s.damage, s.boss_name, s.proof_url, s.edited 
                   FROM gc_submissions s 
                   JOIN members m ON s.discord_id = m.discord_id 
                   WHERE s.date = ? 
                   ORDER BY s.damage DESC""",
                (date,)
            )
            return await cursor.fetchall()

    async def edit_gc(self, discord_id, new_damage, edited_by):
        from utils.helpers import get_today_date

        async with aiosqlite.connect(self.db_path) as db:
            today = get_today_date()
            await db.execute(
                "UPDATE gc_submissions SET damage = ?, edited = 1, edited_by = ? WHERE discord_id = ? AND date = ?",
                (new_damage, edited_by, discord_id, today)
            )
            await db.commit()
            return True

    async def delete_gc(self, discord_id, date=None):
        from utils.helpers import get_today_date
        if date is None:
            date = get_today_date()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM gc_submissions WHERE discord_id = ? AND date = ?",
                (discord_id, date)
            )
            await db.commit()
            return True

    # Events
    async def create_event(self, name, event_type, scheduled_time, created_by):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO events (name, event_type, scheduled_time, created_by) VALUES (?, ?, ?, ?)",
                (name, event_type, scheduled_time, created_by)
            )
            await db.commit()
            cursor = await db.execute("SELECT last_insert_rowid()")
            return (await cursor.fetchone())[0]

    async def get_event(self, event_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM events WHERE event_id = ?", (event_id,)
            )
            return await cursor.fetchone()

    async def join_event(self, event_id, discord_id, role, character):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO event_participants (event_id, discord_id, role, character) VALUES (?, ?, ?, ?)",
                (event_id, discord_id, role, character)
            )
            await db.commit()

    async def get_event_participants(self, event_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT m.username, ep.role, ep.character, ep.confirmed 
                   FROM event_participants ep 
                   JOIN members m ON ep.discord_id = m.discord_id 
                   WHERE ep.event_id = ?""",
                (event_id,)
            )
            return await cursor.fetchall()

    # Roster management
    async def add_to_roster(self, discord_id, character_id, boundary):
        async with aiosqlite.connect(self.db_path) as db:
            # Check if already exists
            cursor = await db.execute(
                "SELECT id FROM member_roster WHERE discord_id = ? AND character_id = ?",
                (discord_id, character_id)
            )
            if await cursor.fetchone():
                await db.execute(
                    "UPDATE member_roster SET boundary = ? WHERE discord_id = ? AND character_id = ?",
                    (boundary, discord_id, character_id)
                )
            else:
                await db.execute(
                    "INSERT INTO member_roster (discord_id, character_id, boundary) VALUES (?, ?, ?)",
                    (discord_id, character_id, boundary)
                )
            await db.commit()

    async def get_roster(self, discord_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT character_id, boundary FROM member_roster WHERE discord_id = ?",
                (discord_id,)
            )
            return await cursor.fetchall()

db = Database()