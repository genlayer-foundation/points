from django.contrib import admin

from .models import MetricSnapshot


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'metric_key',
        'source',
        'status',
        'value',
        'unit',
        'observed_at',
        'created_at',
    )
    list_filter = ('metric_key', 'source', 'status', 'unit')
    search_fields = ('metric_key', 'source', 'label', 'error')
    readonly_fields = (
        'metric_key',
        'source',
        'label',
        'value',
        'unit',
        'observed_at',
        'dimensions',
        'raw_payload',
        'status',
        'error',
        'created_at',
        'updated_at',
    )
    ordering = ('-observed_at', '-created_at')
    date_hierarchy = 'observed_at'
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
