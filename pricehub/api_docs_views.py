# pricehub/api_docs_views.py
from django.shortcuts import render

from .views import staff_required


@staff_required
def api_docs(request):
    return render(request, 'api/api_docs.html')