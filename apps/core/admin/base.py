from django.contrib import admin


class BaseAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    list_filter = (
        "is_active",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        if not change and hasattr(obj, "created_by"):
            obj.created_by = request.user

        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user

        super().save_model(request, obj, form, change)