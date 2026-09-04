from django.contrib.admin.apps import AdminConfig


class SecurtekAdminConfig(AdminConfig):
    default_site = "config.admin.SecurtekAdminSite"
