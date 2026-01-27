# src/memory_manager.py
"""
Memory management for conversation history using SQLite.
Optimized with connection caching and efficient queries.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
from rich.console import Console

from config import MEMORY_DB_PATH, MEMORY_LIMIT_GB

console = Console()


def _ensure_db_directory():
    """Creates the database directory if it doesn't exist."""
    db_dir = os.path.dirname(MEMORY_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


@contextmanager
def _get_connection():
    """
    Context manager for database connections.
    Ensures proper connection handling and cleanup.
    """
    conn = sqlite3.connect(MEMORY_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _get_table_info() -> Dict[str, Any]:
    """
    Get existing column info from the memory table.
    Returns dict with column names as keys and their info.
    """
    try:
        with _get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(memory)")
            columns = {}
            for row in cursor.fetchall():
                # row: (cid, name, type, notnull, dflt_value, pk)
                columns[row[1]] = {
                    "type": row[2],
                    "notnull": bool(row[3]),
                    "default": row[4],
                    "pk": bool(row[5])
                }
            return columns
    except sqlite3.Error:
        return {}


def initialize_database():
    """Initializes the SQLite database and creates/updates the memory table."""
    _ensure_db_directory()
    
    with _get_connection() as conn:
        # Check if table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory'"
        )
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Create new table with all common columns
            conn.execute("""
                CREATE TABLE memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_query TEXT NOT NULL,
                    vlm_response TEXT NOT NULL,
                    image_path TEXT DEFAULT '',
                    image_size INTEGER DEFAULT 0
                )
            """)
            # Create index for faster timestamp queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_timestamp 
                ON memory(timestamp DESC)
            """)
        
        conn.commit()


def save_interaction(
    user_query: str, 
    vlm_response: str, 
    image_path: Optional[str] = None,
    image_size: Optional[int] = None
) -> bool:
    """
    Saves a user interaction to the database.
    Dynamically handles existing table schema.
    
    Args:
        user_query: The user's query text
        vlm_response: The VLM's response text
        image_path: Optional path to saved screenshot
        image_size: Optional size of screenshot in bytes
        
    Returns:
        bool: True if saved successfully
    """
    if not user_query or not vlm_response:
        return False
    
    try:
        # Get existing columns
        columns_info = _get_table_info()
        
        # Build column list and values based on what exists
        columns = ["timestamp", "user_query", "vlm_response"]
        values = [datetime.now().isoformat(), user_query.strip(), vlm_response.strip()]
        
        # Add optional columns if they exist in the table
        if "image_path" in columns_info:
            columns.append("image_path")
            values.append(image_path or "")
        
        if "image_size" in columns_info:
            columns.append("image_size")
            values.append(image_size or 0)
        
        # Handle any other NOT NULL columns with defaults
        for col_name, col_info in columns_info.items():
            if col_name not in columns and col_info["notnull"] and not col_info["pk"]:
                columns.append(col_name)
                # Provide reasonable defaults based on type
                col_type = col_info["type"].upper()
                if "INT" in col_type:
                    values.append(0)
                elif "REAL" in col_type or "FLOAT" in col_type:
                    values.append(0.0)
                else:
                    values.append("")
        
        # Build and execute INSERT
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join(columns)
        sql = f"INSERT INTO memory ({column_names}) VALUES ({placeholders})"
        
        with _get_connection() as conn:
            conn.execute(sql, values)
            conn.commit()
        
        return True
        
    except sqlite3.Error as e:
        console.print(f"[red]Database error saving interaction: {e}[/red]")
        return False


def get_recent_interactions_data(n: int = 5) -> list[dict]:
    """
    Retrieves the last n interactions as a list of dictionaries.
    Useful for constructing custom context strings or accessing image paths.
    """
    try:
        with _get_connection() as conn:
            # Check if image_path column exists
            columns = [row[1] for row in conn.execute("PRAGMA table_info(memory)").fetchall()]
            has_image = "image_path" in columns
            
            query = "SELECT timestamp, user_query, vlm_response"
            if has_image:
                query += ", image_path"
            else:
                query += ", '' as image_path"
                
            query += " FROM memory ORDER BY timestamp DESC LIMIT ?"
            
            cursor = conn.execute(query, (n,))
            rows = cursor.fetchall()
            
            results = []
            for row in reversed(rows): # Return oldest to newest
                results.append({
                    "timestamp": row["timestamp"],
                    "user_query": row["user_query"],
                    "vlm_response": row["vlm_response"],
                    "image_path": row["image_path"] if has_image and row["image_path"] else None
                })
            return results
            
    except sqlite3.Error as e:
        console.print(f"[red]Database error retrieving data: {e}[/red]")
        return []


def retrieve_recent_context(user_query: str, n: int = 5) -> str:
    """
    Retrieves the last n interactions to provide context for the VLM.
    Wraps get_recent_interactions_data for backward compatibility.
    """
    interactions = get_recent_interactions_data(n)
    if not interactions:
        return ""

    lines = ["Here is the recent conversation history:"]
    for item in interactions:
        ts = item["timestamp"]
        try:
            ts_formatted = datetime.fromisoformat(ts).strftime("%H:%M:%S")
        except (ValueError, TypeError):
            ts_formatted = str(ts)[:19] if ts else "Unknown"
        
        img_mark = " [Image]" if item.get("image_path") else ""
        lines.append(f"[{ts_formatted}] User: {item['user_query']}{img_mark}")
        lines.append(f"[{ts_formatted}] Agent: {item['vlm_response']}")

    return "\n".join(lines)


def get_memory_usage() -> int:
    """Returns the total size of the memory database in bytes."""
    if os.path.exists(MEMORY_DB_PATH):
        return os.path.getsize(MEMORY_DB_PATH)
    return 0


def get_interaction_count() -> int:
    """Returns the total number of stored interactions."""
    try:
        with _get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM memory")
            return cursor.fetchone()[0]
    except sqlite3.Error:
        return 0


def prune_memory_if_needed(verbose: bool = True) -> int:
    """
    Deletes oldest memories if database size exceeds the configured limit.
    
    Args:
        verbose: Whether to print status messages
        
    Returns:
        int: Number of entries deleted
    """
    memory_limit_bytes = MEMORY_LIMIT_GB * (1024 ** 3)
    current_usage = get_memory_usage()

    if current_usage <= memory_limit_bytes:
        if verbose:
            usage_mb = current_usage / (1024 ** 2)
            limit_mb = memory_limit_bytes / (1024 ** 2)
            console.print(f"[dim]Memory: {usage_mb:.1f}MB / {limit_mb:.1f}MB[/dim]")
        return 0

    if verbose:
        console.print("[yellow]Memory limit exceeded. Pruning oldest entries...[/yellow]")

    deleted_count = 0
    
    try:
        with _get_connection() as conn:
            while get_memory_usage() > memory_limit_bytes:
                cursor = conn.execute(
                    "SELECT id FROM memory ORDER BY timestamp ASC LIMIT 1"
                )
                oldest = cursor.fetchone()

                if not oldest:
                    break

                conn.execute("DELETE FROM memory WHERE id = ?", (oldest["id"],))
                conn.commit()
                deleted_count += 1

            if deleted_count > 0:
                conn.execute("VACUUM")

    except sqlite3.Error as e:
        console.print(f"[red]Error during pruning: {e}[/red]")

    if verbose and deleted_count > 0:
        console.print(f"[dim]Pruned {deleted_count} entries[/dim]")

    return deleted_count


def clear_all_memory() -> bool:
    """Clears all conversation history. Use with caution."""
    try:
        with _get_connection() as conn:
            conn.execute("DELETE FROM memory")
            conn.execute("VACUUM")
            conn.commit()
        console.print("[yellow]All memory cleared[/yellow]")
        return True
    except sqlite3.Error as e:
        console.print(f"[red]Error clearing memory: {e}[/red]")
        return False


# Initialize database on module load
initialize_database()


if __name__ == "__main__":
    console.print("[bold]Memory Manager Test[/bold]\n")
    
    # Show schema info
    info = _get_table_info()
    console.print(f"[bold]Table columns:[/bold]")
    for col, details in info.items():
        console.print(f"  {col}: {details}")
    
    # Show current stats
    count = get_interaction_count()
    usage = get_memory_usage()
    console.print(f"\nStored interactions: {count}")
    console.print(f"Database size: {usage / 1024:.1f} KB")
    
    # Test save
    console.print("\n[yellow]Testing save...[/yellow]")
    result = save_interaction("Test query", "Test response")
    if result:
        console.print("[green]✓ Save successful[/green]")
    else:
        console.print("[red]✗ Save failed[/red]")
