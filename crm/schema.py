import graphene
from graphene_django import DjangoObjectType, DjangoListField
from graphene_django.filter import DjangoFilterConnectionField
from django.db import transaction
from django.core.exceptions import ValidationError
import re
from .models import Customer, Product, Order, OrderItem
from .filters import CustomerFilter, ProductFilter, OrderFilter

# Types
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (graphene.relay.Node,)
        filterset_class = CustomerFilter

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (graphene.relay.Node,)
        filterset_class = ProductFilter

class OrderItemType(DjangoObjectType):
    class Meta:
        model = OrderItem

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filterset_class = OrderFilter

# Input Types
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int()

class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()

# Queries
class Query(graphene.ObjectType):
    hello = graphene.String()
    
    # Customer queries
    all_customers = DjangoFilterConnectionField(CustomerType)
    customer = graphene.Field(CustomerType, id=graphene.ID(required=True))
    
    # Product queries
    all_products = DjangoFilterConnectionField(ProductType)
    product = graphene.Field(ProductType, id=graphene.ID(required=True))
    
    # Order queries
    all_orders = DjangoFilterConnectionField(OrderType)
    order = graphene.Field(OrderType, id=graphene.ID(required=True))

    def resolve_hello(self, info):
        return "Hello, GraphQL!"

    def resolve_customer(self, info, id):
        return Customer.objects.get(id=id)

    def resolve_product(self, info, id):
        return Product.objects.get(id=id)

    def resolve_order(self, info, id):
        return Order.objects.get(id=id)

# Mutations
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    success = graphene.Boolean()

    @staticmethod
    def validate_phone(phone):
        if phone:
            # Basic phone validation for +1234567890 or 123-456-7890 formats
            pattern = r'^(\+\d{1,3}[- ]?)?\d{3}[- ]?\d{3}[- ]?\d{4}$'
            if not re.match(pattern, phone):
                raise ValidationError("Invalid phone number format. Use +1234567890 or 123-456-7890")
        return True

    def mutate(self, info, input):
        try:
            # Validate email uniqueness
            if Customer.objects.filter(email=input.email).exists():
                raise ValidationError("Email already exists")

            # Validate phone format
            CreateCustomer.validate_phone(input.phone)

            customer = Customer(
                name=input.name,
                email=input.email,
                phone=input.phone
            )
            customer.full_clean()
            customer.save()

            return CreateCustomer(
                customer=customer,
                message="Customer created successfully",
                success=True
            )
        except ValidationError as e:
            return CreateCustomer(
                customer=None,
                message=str(e),
                success=False
            )
        except Exception as e:
            return CreateCustomer(
                customer=None,
                message=f"Error creating customer: {str(e)}",
                success=False
            )

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        inputs = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)
    success = graphene.Boolean()

    def mutate(self, info, inputs):
        customers = []
        errors = []
        
        with transaction.atomic():
            for input_data in inputs:
                try:
                    # Validate email uniqueness
                    if Customer.objects.filter(email=input_data.email).exists():
                        errors.append(f"Email {input_data.email} already exists")
                        continue

                    # Validate phone format
                    CreateCustomer.validate_phone(input_data.phone)

                    customer = Customer(
                        name=input_data.name,
                        email=input_data.email,
                        phone=input_data.phone
                    )
                    customer.full_clean()
                    customer.save()
                    customers.append(customer)
                    
                except ValidationError as e:
                    errors.append(f"Validation error for {input_data.email}: {str(e)}")
                except Exception as e:
                    errors.append(f"Error creating customer {input_data.email}: {str(e)}")

        return BulkCreateCustomers(
            customers=customers,
            errors=errors,
            success=len(customers) > 0
        )

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()
    success = graphene.Boolean()

    def mutate(self, info, input):
        try:
            # Validate price is positive
            if input.price <= 0:
                raise ValidationError("Price must be positive")

            # Validate stock is non-negative
            stock = input.stock if input.stock is not None else 0
            if stock < 0:
                raise ValidationError("Stock cannot be negative")

            product = Product(
                name=input.name,
                price=input.price,
                stock=stock
            )
            product.full_clean()
            product.save()

            return CreateProduct(
                product=product,
                message="Product created successfully",
                success=True
            )
        except ValidationError as e:
            return CreateProduct(
                product=None,
                message=str(e),
                success=False
            )
        except Exception as e:
            return CreateProduct(
                product=None,
                message=f"Error creating product: {str(e)}",
                success=False
            )

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()
    success = graphene.Boolean()

    def mutate(self, info, input):
        try:
            # Validate customer exists
            try:
                customer = Customer.objects.get(id=input.customer_id)
            except Customer.DoesNotExist:
                raise ValidationError("Customer does not exist")

            # Validate products exist and get them
            products = []
            total_amount = 0
            
            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(id=product_id)
                    products.append(product)
                    total_amount += product.price
                except Product.DoesNotExist:
                    raise ValidationError(f"Product with ID {product_id} does not exist")

            # Validate at least one product
            if not products:
                raise ValidationError("At least one product is required")

            # Create order
            with transaction.atomic():
                order = Order(
                    customer=customer,
                    total_amount=total_amount
                )
                order.save()

                # Create order items
                for product in products:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=1,
                        unit_price=product.price
                    )

            return CreateOrder(
                order=order,
                message="Order created successfully",
                success=True
            )
        except ValidationError as e:
            return CreateOrder(
                order=None,
                message=str(e),
                success=False
            )
        except Exception as e:
            return CreateOrder(
                order=None,
                message=f"Error creating order: {str(e)}",
                success=False
            )

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()