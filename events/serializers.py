"""
Django REST Framework Serializers for the Events API.

Serializers handle the conversion between Event model instances
and JSON representation for the API.
"""

from rest_framework import serializers
from .models import Event


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for the Event model.
    
    Provides full event details including all stored fields.
    The raw_payload is excluded by default to reduce response size,
    but can be included using EventDetailSerializer.
    """
    
    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'start_date',
            'venue_name',
            'city',
            'category',
            'event_url',
            'source',
            'description',
            'address',
            'latitude',
            'longitude',
            'image_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class EventDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer that includes raw_payload.
    
    Use this for single event detail views where the complete
    data lineage information is needed.
    """
    
    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'start_date',
            'venue_name',
            'city',
            'category',
            'event_url',
            'source',
            'source_id',
            'description',
            'address',
            'latitude',
            'longitude',
            'image_url',
            'raw_payload',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class EventListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.
    
    Excludes detailed fields for better performance when
    listing many events.
    """
    
    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'start_date',
            'venue_name',
            'city',
            'category',
            'event_url',
            'image_url',
            'latitude',
            'longitude',
        ]
        read_only_fields = fields

