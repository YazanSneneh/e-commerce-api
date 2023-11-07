from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from store.pagination import DefaultPagination
from store.permissions import IsAdminOrReadOnly

from .models import  Cart, CartItem, Collection, Customer, Order, OrderItem, Product, Review
from .serializers import (  AddCartItemSerializer, CartSerializer,
                            CartitemSertializer, CollectionSerializer, CreateOrderSerializer,
                            CustomerSerializer, ProductSerializer,
                            ReviewSerializer, UpateCartItemSerializer,
                            OrderSerializer, UpdateOrderSerializer)
from .filters import CollectionFilter, ProductFilter


# ================================================ PRODUCTS =======================================
class ProductModelView(ModelViewSet):
    queryset = Product.objects.prefetch_related('collection').all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['title','description']
    permission_classes = [IsAdminOrReadOnly]
    ordering_fields = ['unit_price','last_update', 'collection__title']
    pagination_class = DefaultPagination

    def get_serializer_context(self):
        return {'request': self.request}

    def destroy(self, request, *args, **kwargs):
        if OrderItem.objects.filter(product_id= kwargs['pk']).count() >0:
            return Response({"error": "cannot delete product because it have orderitems"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().destroy(request, *args, **kwargs)


# ================================================= COLLECTION =======================================
class CollectionModelView(ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    filter_backends = [DjangoFilterBackend]
    # filter_fields = ['title', 'id']
    filter_class = CollectionFilter
    permission_classes=[IsAdminOrReadOnly]


    def get_serializer_context(self):
        return {'request': self.request}

    def destroy(self, request, pk):
        collection = get_object_or_404(Collection, pk=pk)
        if collection.product_set.count() >0:
            return Response({"error": "Collection can't be deleted because it have products"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        collection.delete()
        return Response(status = status.HTTP_204_NO_CONTENT)


class ReviewSet(ModelViewSet):
    serializer_class = ReviewSerializer

# I override the queryset because I wanted to implement some extra logic.
# that logic is view reviews related to only one object.
    '''
    the reason i was forced to implement it because i don't have access to self object the one that 
    contains the kwargs - that contains the model parameters
    def get_queryset(self):
        return Review.objects.filter(product_id = self.kwargs['product_pk'])
    '''
    def get_queryset(self):
        return Review.objects.filter(product_id = self.kwargs['product_pk'])
        
    def get_serializer_context(self):
        return {'product_id': self.kwargs['product_pk']}

# ================================================= Cart =======================================
class CartViewSet(
                    CreateModelMixin,
                    RetrieveModelMixin,
                    DestroyModelMixin,
                    GenericViewSet
                ):
    queryset = Cart.objects.prefetch_related('items__product').all()
    serializer_class = CartSerializer


class CartItemsViewSet(ModelViewSet):
    http_method_names = ['get','post','patch','delete']
    serializer_class = CartitemSertializer

    def get_queryset(self):
        cart = self.kwargs.get('cart_pk')
        return CartItem.objects\
                        .select_related('product')\
                        .filter(cart_id = cart)

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method == 'POST':
            return AddCartItemSerializer
        elif self.request.method =='PATCH':
            return UpateCartItemSerializer
        return CartitemSertializer

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["GET", "PUT"], permission_classes=[IsAuthenticated])
    def me(self, request):
        (customer, created) = Customer.objects.get_or_create(user_id=request.user.id)

        if request.method=="GET":
            serializer = CustomerSerializer(customer)

        elif request.method=="PUT":
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderViewSet(ModelViewSet):
    http_method_names = ["get", "patch", "post", "delete", "head", "options"]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ['DELETE', "PATCH"]:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(data=request.data, context= {"user_id": request.user.id})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def get_serializer_context(self, **kwargs):
        return {"user_id": self.request.user.id}

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method == "POST":
            return CreateOrderSerializer
        if self.request.method == "PATCH":
            return UpdateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Order.objects.all()

        (customer_id, created) = Customer.objects.only("id").get_or_create(user_id = user.id)
        return Order.objects.filter(customer_id=customer_id)


# ---------------- using generic concrete methods example
# class CollectionList(ListCreateAPIView):

#     def get_queryset(self):
#         return Collection.objects.all()

#     def get_serializer_class(self):
#         return CollectionSerializer

#     def get_serializer_context(self):
#         return {'request': self.request} 

# ------------------================= Concrete generic based api =====================----------------------
# ------------------================= ListAPIView mixen & generic based api =====================----------------------
# class ProductList(ListCreateAPIView):
#     queryset = Product.objects.select_related('collection').all().order_by('id','title')
#     serializer_class = ProductSerializer


#     def get_serializer_context(self):
#         return {'request': self.request}

# ------------------------------------ ProductDetails pi
# class ProductDetails(RetrieveUpdateDestroyAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializer

#     def delete(self, request, pk):
#         product = get_object_or_404(Product, pk=pk)
#         if product.orderitem_set.count() > 0:
#             return HttpResponse({"error": "cannot delete product because it have orderitems"},
#             status=status.HTTP_405_METHOD_NOT_ALLOWED)
#         product.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------================= APIView class based api =====================----------------------
    # def get(self):
    #     return
    # def get(self, request):
    #     proucts = Product.objects.select_related('collection').all().order_by('id','title')
    #     serializer = ProductSerializer(proucts, many =True)
    #     return Response(serializer.data)

    # def post(self, request):
    #     serializer = ProductSerializer(data= request.data)
    #     serializer.is_valid(raise_exception=True)
    #     serializer.save()
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)

# ----------------=============== Method based API view ===================--------------------

# api_view(['GET', 'POST'])
# def collections(request):
#     if request.method == 'GET':
#         collections = Collection.objects.all()
#         serializer = serializers.CollectionSerializer(collections, many=True)
#         return Response(serializer.data)
#     elif request.method == 'POST':
#         serializer = serializers.CollectionSerializer( data= request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data, status = status.HTTP_201_CREATED)

# @api_view(['GET', 'DELETE','PUT'])
# def collection(request, id):
#     collection = get_object_or_404(Collection, pk=id)
#     if request.method == 'GET':
#         serializer = serializers.CollectionSerializer(collection)
#         return Response(serializer.data)
#     elif request.method == "PUT":
#         serializer = CollectionSerializer(collection, data = request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)