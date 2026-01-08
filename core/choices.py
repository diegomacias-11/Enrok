TIPO_CHOICES = [
    ("Producto", "Producto"),
    ("Servicio", "Servicio"),
]

MEDIO_CHOICES = [
    ("Remarketing", "Remarketing"),
    ("Alianzas", "Alianzas"),
    ("Lead", "Lead"),
    ("Procompite", "Procompite"),
    ("Ejecutivos", "Ejecutivos"),
    ("Personales", "Personales"),
    ("Expos / Eventos Deportivos", "Expos / Eventos Deportivos"),
]

SERVICIO_CHOICES = [
    ("Pendiente", "Pendiente"),
    ("Otros", "Otros"),
    ("Todos", "Todos"),    
    ("Fiscal", "Fiscal"),
    ("Auto-ahorro", "Auto-ahorro"),
    ("CheckUp", "CheckUp"),
    ("Contabilidad", "Contabilidad"),
    ("Hidrocarburos", "Hidrocarburos"),
    ("Marketing", "Marketing"),
    ("Monederos", "Monederos"),
    ("Mutualink", "Mutualink"),
    ("PRAIDS", "PRAIDS"),
    ("PROCOM", "PROCOM"),
    ("STEE", "STEE"),
    ("TPV", "TPV"),
    ("Valuación de activos intangibles", "Valuación de activos intangibles"),
    ("Venta de empresas", "Venta de empresas"),
    ("VP360", "VP360"),
    ("Préstamos", "Préstamos"),
    ("Reembolsos", "Reembolsos"),
    ("Reclutamiento", "Reclutamiento"),
]

VENDEDOR_CHOICES = [
    ("Bernardo", "Bernardo"),
    ("Alfredo", "Alfredo"),
    ("Gabriel", "Gabriel"),
]

ESTATUS_CITA_CHOICES = [
    ("Agendada", "Agendada"),
    ("Pospuesta", "Pospuesta"),
    ("Cancelada", "Cancelada"),
    ("Atendida", "Atendida"),
]

NUM_CITA_CHOICES = [
    ("Primera", "Primera"),
    ("Segunda", "Segunda"),
    ("Tercera", "Tercera"),
    ("Cuarta", "Cuarta"),
    ("Quinta", "Quinta"),
]

ESTATUS_SEGUIMIENTO_CHOICES = [
    ("Esperando respuesta del cliente", "Esperando respuesta del cliente"),
    ("Agendar nueva cita", "Agendar nueva cita"),
    ("Solicitud de propuesta", "Solicitud de propuesta"),
    ("Elaboración de propuesta", "Elaboración de propuesta"),
    ("Propuesta enviada", "Propuesta enviada"),
    ("Se envió auditoría Laboral", "Se envió auditoría Laboral"),
    ("Stand by", "Stand by"),
    ("Pendiente de cierre", "Pendiente de cierre"),
    ("En activación", "En activación"),
    ("Reclutando", "Reclutando"),
    ("Cerrado", "Cerrado"),
    ("No está interesado en este servicio", "No está interesado en este servicio"),
    ("Fuera de su presupuesto", "Fuera de su presupuesto"),
]

LUGAR_CHOICES = [
    ("Oficina de Enrok", "Oficina de Enrok"),
    ("Oficina del cliente", "Oficina del cliente"),
    ("Zoom", "Zoom"),
]


AC_CHOICES = [
    ("CONFEDIN", "CONFEDIN"),
    ("CAMARENCE", "CAMARENCE"),
    ("SERVIARUGA", "SERVIARUGA"),
    ("ZAMORA", "ZAMORA"),
    ("INACTIVO", "INACTIVO"),
]

ESTATUS_PROCESO_PENDIENTE = "Pendiente"
ESTATUS_PROCESO_ENVIADA = "Enviada"
ESTATUS_PROCESO_APLICADA = "Aplicada"

ESTATUS_PROCESO_CHOICES = [
    (ESTATUS_PROCESO_PENDIENTE, "Pendiente"),
    (ESTATUS_PROCESO_ENVIADA, "Enviada"),
    (ESTATUS_PROCESO_APLICADA, "Aplicada"),
]

ESTATUS_PERIODO_PENDIENTE = "Pendiente"
ESTATUS_PERIODO_CERRADO = "Cerrado"
ESTATUS_PERIODO_TIMBRADO = "Timbrado"
ESTATUS_PERIODO_ENVIADO = "Enviado"
ESTATUS_PERIODO_ENVIADO_IND = "Enviado ind."
ESTATUS_PERIODO_DRIVE = "Drive"

ESTATUS_PERIODO_CHOICES = [
    (ESTATUS_PERIODO_PENDIENTE, "Pendiente"),
    (ESTATUS_PERIODO_CERRADO, "Cerrado"),
    (ESTATUS_PERIODO_TIMBRADO, "Timbrado"),
    (ESTATUS_PERIODO_ENVIADO, "Enviado"),
    (ESTATUS_PERIODO_ENVIADO_IND, "Enviado ind."),
    (ESTATUS_PERIODO_DRIVE, "Drive"),
]

ESTATUS_PAGO_PENDIENTE = "Pendiente"
ESTATUS_PAGO_PAGADO = "Pagado"

ESTATUS_PAGO_CHOICES = [
    (ESTATUS_PAGO_PENDIENTE, "Pendiente"),
    (ESTATUS_PAGO_PAGADO, "Pagado"),
]
