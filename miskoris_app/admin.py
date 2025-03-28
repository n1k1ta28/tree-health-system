from django.contrib import admin

# Register your models here.

from .models import *

admin.site.register(Forest)
admin.site.register(Order)
admin.site.register(Forest_image)
admin.site.register(Forest_document)
admin.site.register(AnalyzedPhoto)
# admin.site.register(TestClass)
