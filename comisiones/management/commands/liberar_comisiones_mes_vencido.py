from datetime import date
from django.core.management.base import BaseCommand
from comisiones.services import recalcular_periodo


def _periodo_anterior(hoy: date) -> tuple[int, int]:
    if hoy.month == 1:
        return 12, hoy.year - 1
    return hoy.month - 1, hoy.year


class Command(BaseCommand):
    help = "Recalcula la liberacion de comisiones a mes vencido."

    def add_arguments(self, parser):
        parser.add_argument("--mes", type=int, help="Mes a recalcular (1-12)")
        parser.add_argument("--anio", type=int, help="Ano a recalcular (por defecto, ano del mes anterior)")
        parser.add_argument("--solo-pendientes", action="store_true", help="Solo periodos con comisiones no liberadas")

    def handle(self, *args, **options):
        hoy = date.today()
        mes = options.get("mes")
        anio = options.get("anio")

        if mes and (mes < 1 or mes > 12):
            self.stderr.write("Mes fuera de rango, usando mes anterior.")
            mes, anio = None, None

        if not mes:
            mes, anio = _periodo_anterior(hoy)
        if not anio:
            anio = hoy.year

    count = recalcular_periodo(mes, anio, today=hoy, solo_pendientes=options.get("solo_pendientes"))
    if count == 0:
        self.stdout.write("No hay comisiones que procesar.")
    else:
        self.stdout.write(f"Periodos procesados: {count} (mes {mes}, anio {anio}).")
