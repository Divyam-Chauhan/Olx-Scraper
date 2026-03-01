import sqlite3
import sys

def wipe_database():
    """
    Connects to the SQLite database and deletes all rows from the listings table
    while preserving the table schema/structure itself.
    """
    db_name = 'olx_rentals.db'
    
    print("=" * 50)
    print("   DATABASE CLEANUP UTILITY")
    print("=" * 50)
    print(f"WARNING: This will permanently delete ALL scraped listings from '{db_name}'.")
    
    confirm = input("\nAre you sure you want to proceed? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("\nCleanup cancelled. Your data is safe.")
        sys.exit(0)
        
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Count rows before deletion
        cursor.execute("SELECT COUNT(*) FROM listings")
        count = cursor.fetchone()[0]
        
        # Delete all rows
        cursor.execute("DELETE FROM listings")
        conn.commit()
        
        print(f"\nSUCCESS: Successfully deleted {count} listings from the database.")
        print("The database is now completely empty and ready for a fresh scrape.")
        
    except sqlite3.OperationalError:
        print(f"\nERROR: Could not find '{db_name}'.")
        print("The database might not have been created yet, or it's currently completely empty.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    wipe_database()
