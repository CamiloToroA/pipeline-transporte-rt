"""Genera el proyecto Power BI (PBIP: modelo TMDL + reporte PBIR) del tablero de transporte."""
import json, os, shutil, sys, uuid, hashlib, textwrap

OUT = sys.argv[1]
THEME_SRC = sys.argv[2]          # carpeta Report/StaticResources del pbix original
NAME = "Tablero Transporte A Coruña"
SM = f"{NAME}.SemanticModel"
RP = f"{NAME}.Report"


def gid(*parts):
    """GUID determinista: regenerar no cambia los lineageTag."""
    return str(uuid.UUID(hashlib.md5("|".join(parts).encode()).hexdigest()))


def hid(*parts):
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:20]


def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2))


def q(name):
    """Identificador TMDL: comillas si no es alfanumérico simple."""
    return name if name.replace("_", "").isalnum() and name.isascii() else "'" + name.replace("'", "''") + "'"


# ---------------------------------------------------------------- MODELO
# (nombre, dataType, sourceColumn, opciones)
TABLES = {
    "Observaciones": {
        "view": "bi_observaciones",
        "desc": "Un bus reportado por la API en una parada en una captura (hora local de A Coruña).",
        "columns": [
            ("id", "int64", "id", {"hidden": True}),
            ("ciclo_id", "int64", "ciclo_id", {"hidden": True}),
            ("linea_id", "string", "linea_id", {"hidden": True}),
            ("sentido_codigo", "string", "sentido", {"hidden": True}),
            ("Sentido", "string", "sentido_etiqueta", {}),
            ("parada_id", "string", "parada_id", {"hidden": True}),
            ("Bus", "string", "bus_id", {}),
            ("estado_codigo", "string", "estado", {"hidden": True}),
            ("Estado", "string", "estado_etiqueta", {}),
            ("Avance en tramo", "double", "distancia", {"format": "0.00",
                "desc": "Valor 'distancia' de la API; en los datos observados va de 0 a 1."}),
            ("Fecha y hora", "dateTime", "fecha_hora", {"format": "dd/mm/yyyy hh:nn:ss"}),
            ("Minuto", "dateTime", "minuto", {"hidden": True, "format": "dd/mm/yyyy hh:nn"}),
            ("fecha", "dateTime", "fecha", {"hidden": True, "format": "dd/mm/yyyy"}),
            ("hora", "int64", "hora", {"hidden": True}),
        ],
    },
    "Ciclos": {
        "view": "bi_ciclos",
        "desc": "Cada consulta a la API por línea; base para medir completitud y disponibilidad.",
        "columns": [
            ("ciclo_id", "int64", "ciclo_id", {"hidden": True}),
            ("linea_id", "string", "linea_id", {"hidden": True}),
            ("Estado ciclo", "string", "estado", {}),
            ("Resultado", "string", "estado_grupo", {}),
            ("HTTP", "int64", "http_status", {}),
            ("Fecha y hora", "dateTime", "fecha_hora", {"format": "dd/mm/yyyy hh:nn:ss"}),
            ("fecha", "dateTime", "fecha", {"hidden": True, "format": "dd/mm/yyyy"}),
            ("hora", "int64", "hora", {"hidden": True}),
            ("Duración (s)", "double", "duracion_seg", {"format": "0.00"}),
            ("Desfase (s)", "double", "desfase_seg", {"format": "0.0"}),
            ("registros_validos", "int64", "registros_validos", {"hidden": True}),
            ("registros_insertados", "int64", "registros_insertados", {"hidden": True}),
            ("registros_duplicados", "int64", "registros_duplicados", {"hidden": True}),
            ("registros_rechazados", "int64", "registros_rechazados", {"hidden": True}),
            ("Detalle", "string", "detalle", {}),
        ],
    },
    "Rechazos": {
        "view": "bi_rechazos",
        "desc": "Registros descartados por la validación del pipeline.",
        "columns": [
            ("id", "int64", "id", {"hidden": True}),
            ("ciclo_id", "int64", "ciclo_id", {"hidden": True}),
            ("linea_id", "string", "linea_id", {"hidden": True}),
            ("Motivo", "string", "motivo", {}),
            ("Motivo detalle", "string", "motivo_detalle", {}),
            ("fecha", "dateTime", "fecha", {"hidden": True, "format": "dd/mm/yyyy"}),
        ],
    },
    "Calendario": {
        "view": "bi_calendario",
        "desc": "Fechas en hora local de España, desde el primer dato hasta hoy.",
        "date_table": True,
        "columns": [
            ("Fecha", "dateTime", "fecha", {"format": "dd/mm/yyyy", "key": True}),
            ("Año", "int64", "anio", {"format": "0"}),
            ("mes_num", "int64", "mes_num", {"hidden": True}),
            ("Mes", "string", "mes", {"sort": "mes_num"}),
            ("Día", "int64", "dia", {}),
            ("dia_semana_num", "int64", "dia_semana_num", {"hidden": True}),
            ("Día semana", "string", "dia_semana", {"sort": "dia_semana_num"}),
            ("Tipo de día", "string", "tipo_dia", {}),
        ],
    },
    "Horas": {
        "view": "bi_horas",
        "desc": "Horas del día (hora local de A Coruña) y franjas de demanda.",
        "columns": [
            ("hora", "int64", "hora", {"hidden": True}),
            ("Hora del día", "string", "hora_etiqueta", {"sort": "hora"}),
            ("Franja", "string", "franja", {}),
            ("en_ventana_captura", "boolean", "en_ventana_captura", {"hidden": True}),
        ],
    },
    "Lineas": {
        "view": "dim_linea",
        "desc": "Líneas del GTFS estático; 'Monitoreada' indica las que captura el pipeline.",
        "columns": [
            ("linea_id", "string", "linea_id", {"hidden": True}),
            ("Línea", "string", "nombre_corto", {}),
            ("Recorrido", "string", "nombre", {}),
            ("Tipología", "string", "tipologia", {}),
            ("Monitoreada", "boolean", "monitoreada", {}),
        ],
    },
    "Paradas": {
        "view": "dim_parada",
        "desc": "Paradas del GTFS estático (stop_id coincide con el parada_id de la API).",
        "columns": [
            ("parada_id", "string", "parada_id", {}),
            ("Parada", "string", "nombre", {}),
            ("Latitud", "double", "latitud", {"category": "Latitude", "format": "0.000000"}),
            ("Longitud", "double", "longitud", {"category": "Longitude", "format": "0.000000"}),
        ],
    },
}

# (tabla, nombre, formato, carpeta, descripción, DAX)
MEASURES = [
    ("Observaciones", "Total Observaciones", "#,0", "Actividad",
     "Número de registros bus-parada capturados.",
     "COUNTROWS(Observaciones)"),
    ("Observaciones", "Buses Únicos", "#,0", "Actividad",
     "Vehículos distintos observados en el periodo.",
     "DISTINCTCOUNT(Observaciones[Bus])"),
    ("Observaciones", "Paradas con Actividad", "#,0", "Actividad",
     "Paradas distintas en las que se observó al menos un bus.",
     "DISTINCTCOUNT(Observaciones[parada_id])"),
    ("Observaciones", "Capturas con Datos", "#,0", "Actividad",
     "Consultas a la API que devolvieron al menos un bus.",
     "DISTINCTCOUNT(Observaciones[ciclo_id])"),
    ("Observaciones", "Flota Promedio en Servicio", "#,0.0", "Flota",
     "Promedio de buses distintos por minuto, en los minutos con actividad.",
     """
     AVERAGEX(
         VALUES(Observaciones[Minuto]),
         CALCULATE(DISTINCTCOUNT(Observaciones[Bus]))
     )"""),
    ("Observaciones", "Flota Máxima", "#,0", "Flota",
     "Máximo de buses distintos observados en un mismo minuto.",
     """
     MAXX(
         VALUES(Observaciones[Minuto]),
         CALCULATE(DISTINCTCOUNT(Observaciones[Bus]))
     )"""),
    ("Observaciones", "Última Captura", "dd/mm/yyyy hh:nn:ss", "Última captura",
     "Fecha y hora (A Coruña) de la captura con datos más reciente del periodo.",
     """
     CALCULATE(
         MAX(Observaciones[Fecha y hora]),
         REMOVEFILTERS(Observaciones),
         REMOVEFILTERS(Paradas)
     )"""),
    ("Observaciones", "Buses Última Captura", "#,0", "Última captura",
     "Buses en servicio según la última captura con datos de cada línea.",
     """
     SUMX(
         VALUES(Lineas[linea_id]),
         VAR UltimoCiclo =
             CALCULATE(
                 MAX(Observaciones[ciclo_id]),
                 REMOVEFILTERS(Observaciones),
                 REMOVEFILTERS(Paradas)
             )
         RETURN
             IF(
                 NOT ISBLANK(UltimoCiclo),
                 CALCULATE(DISTINCTCOUNT(Observaciones[Bus]), Observaciones[ciclo_id] = UltimoCiclo)
             )
     )"""),
    ("Observaciones", "Observaciones Última Captura", "#,0", "Última captura",
     "Registros bus-parada de la última captura con datos de cada línea.",
     """
     SUMX(
         VALUES(Lineas[linea_id]),
         VAR UltimoCiclo =
             CALCULATE(
                 MAX(Observaciones[ciclo_id]),
                 REMOVEFILTERS(Observaciones),
                 REMOVEFILTERS(Paradas)
             )
         RETURN
             IF(
                 NOT ISBLANK(UltimoCiclo),
                 CALCULATE(COUNTROWS(Observaciones), Observaciones[ciclo_id] = UltimoCiclo)
             )
     )"""),
    ("Ciclos", "Ciclos Registrados", "#,0", "Continuidad",
     "Consultas a la API registradas en la bitácora.",
     "COUNTROWS(Ciclos)"),
    ("Ciclos", "Ciclos con Datos", "#,0", "Continuidad",
     "Consultas que devolvieron buses.",
     "CALCULATE(COUNTROWS(Ciclos), Ciclos[Resultado] = \"Con datos\")"),
    ("Ciclos", "Ciclos sin Buses", "#,0", "Continuidad",
     "Consultas correctas pero sin buses en la línea.",
     "CALCULATE(COUNTROWS(Ciclos), Ciclos[Resultado] = \"Sin buses\")"),
    ("Ciclos", "Ciclos con Error", "#,0", "Continuidad",
     "Consultas fallidas (red, HTTP, formato o respuesta de la API).",
     "CALCULATE(COUNTROWS(Ciclos), Ciclos[Resultado] = \"Error\")"),
    ("Ciclos", "Ciclos Esperados", "#,0", "Continuidad",
     "Una consulta por minuto y línea monitoreada dentro de la ventana de captura (06:00-24:00), "
     "entre el primer y el último día con registros.",
     """
     VAR Inicio = CALCULATE(MIN(Ciclos[fecha]), REMOVEFILTERS())
     VAR Fin = CALCULATE(MAX(Ciclos[fecha]), REMOVEFILTERS())
     VAR Dias =
         COUNTROWS(
             FILTER(VALUES(Calendario[Fecha]), Calendario[Fecha] >= Inicio && Calendario[Fecha] <= Fin)
         )
     VAR HorasVentana = CALCULATE(COUNTROWS(Horas), Horas[en_ventana_captura] = TRUE())
     VAR LineasMonitoreadas = CALCULATE(COUNTROWS(Lineas), Lineas[Monitoreada] = TRUE())
     RETURN
         Dias * HorasVentana * 60 * LineasMonitoreadas"""),
    ("Ciclos", "Cobertura de Captura", "0.0%", "Calidad",
     "Ciclos registrados frente a los esperados. Los días de inicio y el día en curso salen incompletos.",
     "DIVIDE([Ciclos Registrados], [Ciclos Esperados])"),
    ("Ciclos", "Disponibilidad API", "0.0%", "Calidad",
     "Porcentaje de consultas que no terminaron en error.",
     "DIVIDE([Ciclos Registrados] - [Ciclos con Error], [Ciclos Registrados])"),
    ("Ciclos", "Registros Duplicados", "#,0", "Calidad",
     "Registros válidos que ya existían (la API repitió la misma instantánea).",
     "SUM(Ciclos[registros_duplicados])"),
    ("Ciclos", "Desfase Promedio (s)", "#,0.0", "Calidad",
     "Diferencia media entre la fecha de la API y el reloj del pipeline.",
     "AVERAGE(Ciclos[Desfase (s)])"),
    ("Ciclos", "Duración Promedio Consulta (s)", "#,0.00", "Calidad",
     "Tiempo medio de respuesta de la API.",
     "AVERAGE(Ciclos[Duración (s)])"),
    ("Rechazos", "Registros Rechazados", "#,0", "Calidad",
     "Registros descartados por la validación.",
     "COUNTROWS(Rechazos)"),
    ("Rechazos", "Tasa de Rechazo", "0.00%", "Calidad",
     "Rechazados sobre el total de registros recibidos (válidos + rechazados).",
     "DIVIDE([Registros Rechazados], [Registros Rechazados] + [Total Observaciones])"),
]

RELATIONSHIPS = [
    ("Observaciones", "fecha", "Calendario", "Fecha"),
    ("Observaciones", "hora", "Horas", "hora"),
    ("Observaciones", "linea_id", "Lineas", "linea_id"),
    ("Observaciones", "parada_id", "Paradas", "parada_id"),
    ("Ciclos", "fecha", "Calendario", "Fecha"),
    ("Ciclos", "hora", "Horas", "hora"),
    ("Ciclos", "linea_id", "Lineas", "linea_id"),
    ("Rechazos", "fecha", "Calendario", "Fecha"),
    ("Rechazos", "linea_id", "Lineas", "linea_id"),
]


def dax_block(expr):
    expr = textwrap.dedent(expr).strip("\n")
    if "\n" not in expr:
        return " " + expr
    return "\n" + "\n".join("\t\t\t" + l if l.strip() else "" for l in expr.split("\n"))


def table_tmdl(name, t):
    out = []
    if t.get("desc"):
        out.append(f"/// {t['desc']}")
    out.append(f"table {q(name)}")
    if t.get("date_table"):
        out.append("\tdataCategory: Time")
    out.append(f"\tlineageTag: {gid('table', name)}\n")
    for tbl, mname, fmt, folder, desc, dax in MEASURES:
        if tbl != name:
            continue
        out.append(f"\t/// {desc}")
        out.append(f"\tmeasure {q(mname)} ={dax_block(dax)}")
        out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append(f"\t\tlineageTag: {gid('measure', name, mname)}\n")
    for cname, dtype, src, o in t["columns"]:
        if o.get("desc"):
            out.append(f"\t/// {o['desc']}")
        out.append(f"\tcolumn {q(cname)}")
        out.append(f"\t\tdataType: {dtype}")
        if o.get("hidden"):
            out.append("\t\tisHidden")
        if o.get("key"):
            out.append("\t\tisKey")
        fmt = o.get("format") or ("0" if dtype == "int64" else None)
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        if o.get("category"):
            out.append(f"\t\tdataCategory: {o['category']}")
        out.append(f"\t\tlineageTag: {gid('column', name, cname)}")
        out.append("\t\tsummarizeBy: none")
        out.append(f"\t\tsourceColumn: {src}")
        if o.get("sort"):
            out.append(f"\t\tsortByColumn: {q(o['sort'])}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User\n")
    out.append(f"\tpartition {q(name)} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    m = [
        "let",
        "    Origen = PostgreSQL.Database(Servidor, BaseDatos),",
        f"    Datos = Origen{{[Schema = \"public\", Item = \"{t['view']}\"]}}[Data]",
        "in",
        "    Datos",
    ]
    out += ["\t\t\t\t" + l for l in m]
    out.append("")
    out.append("\tannotation PBI_ResultType = Table\n")
    return "\n".join(out)


def build_model():
    base = f"{SM}/definition"
    write(f"{base}/database.tmdl", "database\n\tcompatibilityLevel: 1600\n\n")
    order = ["Servidor", "BaseDatos"] + list(TABLES)
    model = [
        "model Model",
        "\tculture: es-ES",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: es-CO",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        f"annotation PBI_QueryOrder = {json.dumps(order, ensure_ascii=False)}",
        "",
    ]
    model += [f"ref table {q(t)}" for t in TABLES]
    write(f"{base}/model.tmdl", "\n".join(model) + "\n\n")
    expr = []
    for pname, val, desc in [("Servidor", "localhost", "Servidor PostgreSQL (el contenedor Docker publica el puerto 5432)."),
                             ("BaseDatos", "transporte_db", "Base de datos del pipeline.")]:
        expr += [
            f"/// {desc}",
            f"expression {pname} = \"{val}\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]",
            f"\tlineageTag: {gid('expr', pname)}",
            "",
            "\tannotation PBI_ResultType = Text",
            "",
        ]
    write(f"{base}/expressions.tmdl", "\n".join(expr) + "\n")
    rel = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        rel += [f"relationship {gid('rel', ft, fc, tt)}",
                f"\tfromColumn: {q(ft)}.{q(fc)}",
                f"\ttoColumn: {q(tt)}.{q(tc)}", ""]
    write(f"{base}/relationships.tmdl", "\n".join(rel) + "\n")
    for name, t in TABLES.items():
        write(f"{base}/tables/{name}.tmdl", table_tmdl(name, t))
    write(f"{SM}/definition.pbism", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}})
    write(f"{SM}/.platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": gid("sm")}})


# ---------------------------------------------------------------- REPORTE
VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def theme_color(cid, pct=0):
    return {"solid": {"color": {"expr": {"ThemeDataColor": {"ColorId": cid, "Percent": pct}}}}}


def col(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def meas(entity, prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


MEASURE_TABLE = {m[1]: m[0] for m in MEASURES}


def F(ref):
    """'Tabla.Columna' o nombre de medida -> (field, queryRef, nativeQueryRef)."""
    if ref in MEASURE_TABLE:
        return meas(MEASURE_TABLE[ref], ref), f"{MEASURE_TABLE[ref]}.{ref}", ref
    entity, prop = ref.split(".", 1)
    return col(entity, prop), ref, prop


def projections(refs, active=False):
    out = []
    for r in refs:
        field, qref, native = F(r)
        p = {"field": field, "queryRef": qref, "nativeQueryRef": native}
        if active:
            p["active"] = True
        out.append(p)
    return {"projections": out}


def container_objects(title):
    """Mismo estilo de tarjeta que el tablero original (título centrado, sombra, fondo)."""
    return {
        "title": [{"properties": {
            "show": lit("true" if title else "false"), "titleWrap": lit("true"),
            "background": theme_color(0), "alignment": lit("'center'"),
            "fontSize": lit("18D"), "bold": lit("true"),
            **({"text": lit("'" + title.replace("'", "''") + "'")} if title else {})}}],
        "subTitle": [{"properties": {"show": lit("false")}}],
        "background": [{"properties": {"show": lit("true"), "transparency": lit("0D")}}],
        "padding": [{"properties": {"top": lit("12D"), "bottom": lit("8D"), "left": lit("8D"), "right": lit("8D")}}],
        "border": [{"properties": {"show": lit("false"), "radius": lit("8D")}}],
        "dropShadow": [{"properties": {
            "show": lit("true"), "preset": lit("'BottomRight'"), "transparency": lit("86D"),
            "shadowSpread": lit("0D"), "shadowBlur": lit("3D"), "angle": lit("90D"), "shadowDistance": lit("1D")}}],
        "visualHeader": [{"properties": {"show": lit("false")}}],
    }


class Page:
    def __init__(self, display, title):
        self.name = hid("page", display)
        self.display = display
        self.visuals = []
        self.z = 0
        self.add("shape", 0, 0, 1920, 102, None, objects={
            "shape": [{"properties": {"tileShape": lit("'rectangle'")}}],
            "fill": [{"properties": {"fillColor": theme_color(3, -0.25)}, "selector": {"id": "default"}}]},
            container=False, key="header")
        self.add("textbox", 28, 20, 1856, 62, None, objects={"general": [{"properties": {"paragraphs": [{
            "textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": "30pt", "color": "#ffffff"}}],
            "horizontalTextAlignment": "center"}]}}]}, container=False, key="title")

    def add(self, vtype, x, y, w, h, title, query=None, objects=None, container=True, filters=None, key=None):
        self.z += 1000
        name = hid(self.display, key or title or vtype, str(self.z))
        visual = {"visualType": vtype}
        if query:
            visual["query"] = query
        if objects:
            visual["objects"] = objects
        if container:
            visual["visualContainerObjects"] = container_objects(title)
        visual["drillFilterOtherVisuals"] = True
        v = {"$schema": VC_SCHEMA, "name": name,
             "position": {"x": x, "y": y, "z": self.z, "height": h, "width": w, "tabOrder": self.z},
             "visual": visual}
        if filters:
            v["filterConfig"] = {"filters": filters}
        self.visuals.append(v)

    # --- visuales de alto nivel
    def card(self, x, y, w, h, title, measure):
        field, _, _ = F(measure)
        self.add("cardVisual", x, y, w, h, title,
                 query={"queryState": {"Data": projections([measure])}},
                 objects={"label": [{"properties": {"show": lit("false")}, "selector": {"id": "default"}}],
                          "value": [{"properties": {"fontSize": lit("30D"), "horizontalAlignment": lit("'center'")},
                                     "selector": {"id": "default"}}]})

    def slicer(self, x, y, w, h, title, ref, mode="Basic", filters=None, horizontal=False):
        field, _, _ = F(ref)
        objects = {"data": [{"properties": {"mode": lit(f"'{mode}'")}}],
                   "header": [{"properties": {"show": lit("false")}}],
                   "items": [{"properties": {"textSize": lit("13D")}}]}
        if horizontal:
            objects["general"] = [{"properties": {"orientation": lit("1D")}}]
        self.add("slicer", x, y, w, h, title,
                 query={"queryState": {"Values": projections([ref], active=True)},
                        "sortDefinition": {"sort": [{"field": field, "direction": "Ascending"}], "isDefaultSort": True}},
                 objects=objects, filters=filters)

    def chart(self, vtype, x, y, w, h, title, category, values, series=None, sort=None, filters=None,
              categorical_axis=False, color=3):
        qs = {"Category": projections([category], active=True), "Y": projections(values)}
        if series:
            qs["Series"] = projections([series])
        sort_ref, direction = sort or (values[0], "Descending")
        query = {"queryState": qs, "sortDefinition": {"sort": [{"field": F(sort_ref)[0], "direction": direction}],
                                                      "isDefaultSort": True}}
        objects = {}
        if not series and vtype not in ("donutChart", "pieChart"):
            objects["dataPoint"] = [{"properties": {"fill": theme_color(color)}}]
        if categorical_axis:
            objects["categoryAxis"] = [{"properties": {"axisType": lit("'Categorical'")}}]
        if vtype in ("donutChart", "pieChart"):
            objects["legend"] = [{"properties": {"show": lit("true"), "position": lit("'Bottom'")}}]
            objects["labels"] = [{"properties": {"labelStyle": lit("'Percent of total'")}}]
        self.add(vtype, x, y, w, h, title, query=query, objects=objects or None, filters=filters)

    def table(self, x, y, w, h, title, refs, sort=None):
        sort_ref, direction = sort or (refs[0], "Ascending")
        self.add("tableEx", x, y, w, h, title,
                 query={"queryState": {"Values": projections(refs)},
                        "sortDefinition": {"sort": [{"field": F(sort_ref)[0], "direction": direction}]}},
                 objects={"columnHeaders": [{"properties": {"fontSize": lit("13D"), "alignment": lit("'Center'")}}],
                          "values": [{"properties": {"fontSize": lit("12D")}}],
                          "total": [{"properties": {"totals": lit("true"), "fontSize": lit("12D")}}]})


def filtro_monitoreadas(name):
    return [{"name": name, "field": col("Lineas", "Monitoreada"), "type": "Categorical",
             "filter": {"Version": 2, "From": [{"Name": "l", "Entity": "Lineas", "Type": 0}],
                        "Where": [{"Condition": {"In": {
                            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "l"}}, "Property": "Monitoreada"}}],
                            "Values": [[{"Literal": {"Value": "true"}}]]}}}]}}]


def filtro_topn(name, entity, prop, n, measure):
    mt = MEASURE_TABLE[measure]
    return [{"name": name, "field": col(entity, prop), "type": "TopN",
             "filter": {"Version": 2,
                        "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": {
                            "Version": 2,
                            "From": [{"Name": "p", "Entity": entity, "Type": 0},
                                     {"Name": "m", "Entity": mt, "Type": 0}],
                            "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "p"}}, "Property": prop}, "Name": "field"}],
                            "OrderBy": [{"Direction": 2, "Expression": {"Measure": {
                                "Expression": {"SourceRef": {"Source": "m"}}, "Property": measure}}}],
                            "Top": n}}}, "Type": 2},
                                 {"Name": "p", "Entity": entity, "Type": 0}],
                        "Where": [{"Condition": {"In": {
                            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "p"}}, "Property": prop}}],
                            "Table": {"SourceRef": {"Source": "subquery"}}}}}]}}]


def slicers_comunes(p, extra=None):
    p.slicer(48, 118, 440, 140, "Fecha", "Calendario.Fecha", mode="Between")
    p.slicer(512, 118, 900, 140, "Línea", "Lineas.Línea", horizontal=True,
             filters=filtro_monitoreadas(hid(p.display, "f-monitoreadas")))
    ref, title = extra or ("Calendario.Tipo de día", "Tipo de día")
    p.slicer(1436, 118, 436, 140, title, ref, mode="Dropdown")


def cards(p, y, items):
    n, gap, x0, total = len(items), 24, 48, 1824
    w = (total - gap * (n - 1)) / n
    for i, (title, m) in enumerate(items):
        p.card(x0 + i * (w + gap), y, w, 150, title, m)


def build_report():
    pages = []

    p = Page("Resumen Operativo", "RESUMEN OPERATIVO · BUSES DE A CORUÑA")
    slicers_comunes(p)
    cards(p, 282, [("Última captura con datos", "Última Captura"), ("Buses en la última captura", "Buses Última Captura"),
                   ("Flota promedio en servicio", "Flota Promedio en Servicio"), ("Flota máxima en un minuto", "Flota Máxima"),
                   ("Observaciones", "Total Observaciones")])
    p.chart("clusteredBarChart", 48, 456, 600, 584, "Buses en la última captura por línea",
            "Lineas.Línea", ["Buses Última Captura"])
    p.chart("lineChart", 672, 456, 1200, 290, "Flota promedio en servicio por hora (hora de A Coruña)",
            "Horas.Hora del día", ["Flota Promedio en Servicio"], series="Lineas.Línea",
            sort=("Horas.Hora del día", "Ascending"))
    p.table(672, 770, 1200, 270, "Resumen por línea",
            ["Lineas.Línea", "Lineas.Tipología", "Total Observaciones", "Buses Únicos",
             "Flota Promedio en Servicio", "Flota Máxima", "Cobertura de Captura"])
    pages.append(p)

    p = Page("Análisis Temporal y Paradas", "ANÁLISIS TEMPORAL Y POR PARADA")
    slicers_comunes(p, extra=("Observaciones.Sentido", "Sentido"))
    p.chart("lineChart", 48, 282, 1100, 360, "Observaciones por hora del día (hora de A Coruña)",
            "Horas.Hora del día", ["Total Observaciones"], series="Lineas.Línea",
            sort=("Horas.Hora del día", "Ascending"))
    p.chart("clusteredColumnChart", 1172, 282, 700, 360, "Flota promedio por día de la semana",
            "Calendario.Día semana", ["Flota Promedio en Servicio"], sort=("Calendario.Día semana", "Ascending"))
    p.chart("clusteredBarChart", 48, 666, 1100, 374, "Top 10 paradas con más observaciones",
            "Paradas.Parada", ["Total Observaciones"],
            filters=filtro_topn(hid(p.display, "f-top"), "Paradas", "Parada", 10, "Total Observaciones"))
    p.chart("donutChart", 1172, 666, 338, 374, "Estado de los buses", "Observaciones.Estado", ["Total Observaciones"])
    p.chart("donutChart", 1534, 666, 338, 374, "Observaciones por sentido", "Observaciones.Sentido", ["Total Observaciones"])
    pages.append(p)

    p = Page("Calidad y Continuidad", "CALIDAD Y CONTINUIDAD DE LOS DATOS")
    slicers_comunes(p)
    cards(p, 282, [("Cobertura de captura", "Cobertura de Captura"), ("Disponibilidad de la API", "Disponibilidad API"),
                   ("Tasa de rechazo", "Tasa de Rechazo"), ("Registros duplicados", "Registros Duplicados"),
                   ("Desfase promedio API (s)", "Desfase Promedio (s)")])
    p.chart("columnChart", 48, 456, 1100, 310, "Ciclos por día según resultado",
            "Calendario.Fecha", ["Ciclos Registrados"], series="Ciclos.Resultado",
            sort=("Calendario.Fecha", "Ascending"), categorical_axis=True)
    p.chart("clusteredBarChart", 1172, 456, 700, 310, "Registros rechazados por motivo",
            "Rechazos.Motivo", ["Registros Rechazados"], color=4)
    p.table(48, 790, 1824, 250, "Completitud diaria por línea",
            ["Calendario.Fecha", "Lineas.Línea", "Ciclos Registrados", "Ciclos Esperados", "Cobertura de Captura",
             "Ciclos con Datos", "Ciclos sin Buses", "Ciclos con Error", "Registros Rechazados"],
            sort=("Calendario.Fecha", "Descending"))
    pages.append(p)

    base = f"{RP}/definition"
    for pg in pages:
        write(f"{base}/pages/{pg.name}/page.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": pg.name, "displayName": pg.display, "displayOption": "FitToPage", "height": 1080, "width": 1920})
        for v in pg.visuals:
            write(f"{base}/pages/{pg.name}/visuals/{v['name']}/visual.json", v)
    write(f"{base}/pages/pages.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [pg.name for pg in pages], "activePageName": pages[0].name})
    write(f"{base}/version.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0"})
    write(f"{base}/report.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "Fluent2-CY26SU08",
                                          "reportVersionAtImport": {"visual": "2.12.0", "report": "3.4.0", "page": "2.3.1"},
                                          "type": "SharedResources"}},
        "objects": {"outspacePane": [{"properties": {"expanded": lit("false")}}]},
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": "Fluent2-CY26SU08", "path": "BaseThemes/Fluent2-CY26SU08.json", "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                     "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}})
    shutil.copytree(THEME_SRC, os.path.join(OUT, RP, "StaticResources"), dirs_exist_ok=True)
    write(f"{RP}/definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{SM}"}}})
    write(f"{RP}/.platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": gid("rp")}})
    write(f"{NAME}.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": RP}}], "settings": {"enableAutoRecovery": True}})
    write(".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    return pages


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    build_model()
    pages = build_report()
    print("Generado en", OUT)
    for pg in pages:
        print(f"  {pg.display}: {len(pg.visuals)} visuales")
