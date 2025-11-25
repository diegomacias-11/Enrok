
from django.shortcuts import render


def reporte_looker(request):
    """Renderiza el dashboard de Looker Studio embebido."""
    return render(request, 'reportes/looker.html')
