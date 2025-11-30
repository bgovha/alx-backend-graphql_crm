
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'graphql_crm.settings')
django.setup()

from crm.models import Customer, Product, Order, OrderItem
from django.db import transaction

@transaction.atomic
def seed_database():
    # Clear existing data
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    Customer.objects.all().delete()
    Product.objects.all().delete()

    # Create customers
    customers = [
        Customer(name="Alice Johnson", email="alice@example.com", phone="+1234567890"),
        Customer(name="Bob Smith", email="bob@example.com", phone="123-456-7890"),
        Customer(name="Carol Davis", email="carol@example.com", phone="+44555123456"),
    ]
    for customer in customers:
        customer.save()

    # Create products
    products = [
        Product(name="Laptop", price=999.99, stock=10),
        Product(name="Mouse", price=29.99, stock=50),
        Product(name="Keyboard", price=79.99, stock=25),
        Product(name="Monitor", price=299.99, stock=5),
    ]
    for product in products:
        product.save()

    # Create orders
    customer1 = Customer.objects.get(email="alice@example.com")
    customer2 = Customer.objects.get(email="bob@example.com")

    # Order 1
    order1 = Order(customer=customer1, total_amount=999.99 + 29.99)
    order1.save()
    OrderItem.objects.create(order=order1, product=products[0], quantity=1, unit_price=999.99)
    OrderItem.objects.create(order=order1, product=products[1], quantity=1, unit_price=29.99)

    # Order 2
    order2 = Order(customer=customer2, total_amount=299.99 + 79.99)
    order2.save()
    OrderItem.objects.create(order=order2, product=products[3], quantity=1, unit_price=299.99)
    OrderItem.objects.create(order=order2, product=products[2], quantity=1, unit_price=79.99)

    print("Database seeded successfully!")
    print(f"Created {len(customers)} customers")
    print(f"Created {len(products)} products")
    print(f"Created 2 orders")

if __name__ == '__main__':
    seed_database()