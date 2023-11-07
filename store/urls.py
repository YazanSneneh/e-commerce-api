
from django.urls import path, include
from rest_framework_nested import routers
from . import views

router = routers.DefaultRouter()
router.register('products', views.ProductModelView, basename='products')
router.register('collections', views.CollectionModelView, basename='collections')
router.register('carts', views.CartViewSet, basename='carts')
router.register('customers', views.CustomerViewSet, basename='customers')
router.register("orders", views.OrderViewSet, basename="orders")


product_router = routers.NestedSimpleRouter(router, 'products', lookup='product')
product_router.register('reviews', views.ReviewSet, basename='product-reviews')

cart_items_router = routers.NestedSimpleRouter(router, 'carts', lookup='cart')
cart_items_router.register('items', views.CartItemsViewSet, basename='cart-items')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(product_router.urls)),
    path('', include(cart_items_router.urls)),
]