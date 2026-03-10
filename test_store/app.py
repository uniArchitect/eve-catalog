import csv

# Load the "Database" from the CSV file
inventory = {}
with open('products.csv', mode='r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        inventory[row['product']] = float(row['price'])

cart = []

print("--- Welcome to the Vibe Store ---")

while True:
    print("\nAvailable:", ", ".join(inventory.keys()))
    choice = input("Add to cart (or 'done'): ").lower()
    
    if choice == 'done':
        break
    elif choice in inventory:
        cart.append(choice)
        print(f"Added {choice}!")
    else:
        print("Not in stock.")

subtotal = sum(inventory[item] for item in cart)
print(f"\nYour Total: ${subtotal:.2f}")