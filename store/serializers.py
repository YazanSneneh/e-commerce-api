from decimal import Decimal
from django.core import validators
from django.core.exceptions import ValidationError
from django.db.models import fields
from django.db.models.aggregates import Sum
from django.db import transaction
from rest_framework import serializers
from store.models import Cart, CartItem, Product, Collection, Customer, Review, Order, OrderItem

class CollectionSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField('add_products_count')

    class Meta:
        model = Collection
        fields =['id', 'title', 'products_count']

    def add_products_count(self, collection: Collection):
        return  collection.product_set.count()


class ProductSerializer(serializers.ModelSerializer):
    price_with_tax = serializers.SerializerMethodField('add_tax_to_price')

    class Meta:
        model = Product
        fields = ['id','title', 'description', 'slug', 'inventory','unit_price', 'price_with_tax', 'collection']
    # title = serializers.CharField(max_length=255)
    # price = serializers.DecimalField(max_digits=6, decimal_places=2, source='unit_price')
    # collection = serializers.StringRelatedField()
    # collection = CollectionSerializer()

    def add_tax_to_price(self, product: Product):
        return product.unit_price * Decimal(1.6)


class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model= Customer
        fields =['id', 'user_id', 'membership', 'phone', 'birth_date']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'name', 'description', 'date']

    def create(self, validated_data):
        product_id = self.context['product_id']
        return Review.objects.create(product_id = product_id, **validated_data)


class SimpleProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'unit_price', 'title']


class CartitemSertializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    total_price = serializers.SerializerMethodField('calc_item_price', )

    class Meta:
        model = CartItem
        fields = ['id','quantity','product', 'total_price']


    def calc_item_price(self, item: CartItem):
        return  item.product.unit_price * item.quantity


class CartSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    items = CartitemSertializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField('calc_total_price')

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price']

    def calc_total_price(self, cart : Cart):
        return  sum([item.quantity * item.product.unit_price for item in cart.items.all()])


class AddCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity']

    product_id = serializers.IntegerField()

    def validate_product_id(self,value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Product does not exist')
        return value

    def save(self, **kwargs):
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']
        cart_id = self.context['cart_id']

        try:
            cart_item = CartItem.objects.get(product_id = product_id, cart_id = cart_id)
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            cart_item = CartItem.objects.create(cart_id=cart_id, product_id=product_id, quantity=quantity)
            cart_item.save()
            self.instance = cart_item
        return self.instance


class UpateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['quantity']


class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    class Meta:
        model = OrderItem
        fields = ["id", "quantity", "unit_price", "product"]


class OrderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    customer = CustomerSerializer()
    placed_at = serializers.DateTimeField()
    payment_status = serializers.CharField()
    items = OrderItemSerializer(many=True, read_only=True)


class UpdateOrderSerializer(serializers.Serializer):
    payment_status = serializers.CharField()

class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()

    def validate_cart_id(self, cart_id):
        print(cart_id)
        if not Cart.objects.filter(id=cart_id).exists():
            raise ValidationError("Cart given id does not exist!")

        if not CartItem.objects.filter(cart_id=cart_id):
            raise ValidationError("Cart with given id is empty!")

    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data["cart_id"]

            (customer, created) = Customer.objects.get_or_create(user_id = self.context["user_id"])
            order = Order.objects.create(customer=customer)

            cart_items = CartItem.objects.select_related("product").filter(cart_id=cart_id)

            order_items = [
                OrderItem(
                    quantity = item.quantity,
                    product = item.product,
                    unit_price = item.product.unit_price,
                    order=order,
                )
                for item in cart_items
            ]

            OrderItem.objects.bulk_create(order_items)

            Cart.objects.filter(id=cart_id).delete()

            return order