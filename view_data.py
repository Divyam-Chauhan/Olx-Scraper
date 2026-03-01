import sqlite3

conn = sqlite3.connect('olx_rentals.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM listings")
total = cursor.fetchone()[0]

if total == 0:
    print("Database is currently empty.")
else:
    print(f"\n--- Found {total} Listings in Database ---\n")
    print(f"{'BHK':<6} | {'Price':<10} | {'Seller':<10} | {'Furnishing':<15} | {'Title':<45} | {'URL'}")
    print("-" * 150)
    
    cursor.execute("SELECT bhk, price, seller_type, furnishing, title, url FROM listings")
    rows = cursor.fetchall()
    
    for row in rows:
        bhk, price, seller, furnishing, title, url = row
        safe_price = str(price).replace("₹", "Rs")
        safe_title = (str(title)[:42] + '...') if len(str(title)) > 45 else str(title)
        safe_seller = str(seller).split('\n')[0][:10]
        
        print(f"{str(bhk):<6} | {safe_price:<10} | {safe_seller:<10} | {str(furnishing):<15} | {safe_title:<45} | {str(url)}")

conn.close()
