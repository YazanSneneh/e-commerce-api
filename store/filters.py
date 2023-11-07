from django.db import models
from django.db.models import fields
from django_filters.rest_framework import FilterSet
from .models import Collection, Product

class ProductFilter(FilterSet):
    class Meta:
        model = Product
        fields = {
            'collection_id': ['exact'],
            'unit_price': ['gt', 'lt']
        }

class CollectionFilter(FilterSet):
    class Meta:
        model = Collection
        fields = {
            'title': ['icontains'],
            'id': ['gt', 'lt']
        }