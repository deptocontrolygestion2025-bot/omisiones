import streamlit as st
import pandas as pd
from io import BytesIO
import plotly.express as px

st.set_page_config(
    page_title="Analizador de Horas Médicas",
    layout="wide"
)

st.title("Analizador de Horas Asignadas")

archivo = st.file_uploader("Sube archivo Excel", type=["xlsx"])

if archivo:

    # =========================
    # HOJAS
    # =========================
    hoja1 = pd.read_excel(archivo, sheet_name=0)
    hoja2 = pd.read_excel(archivo, sheet_name=1)
    hoja3 = pd.read_excel(archivo, sheet_name=2)

    hoja1.columns = hoja1.columns.str.strip().str.upper()
    hoja2.columns = hoja2.columns.str.strip().str.upper()
    hoja3.columns = hoja3.columns.str.strip().str.upper()

    # =========================
    # COLUMNAS
    # =========================
    col_h1_prof = "NOMBRE PROFESIONAL"
    col_h1_agr = "AGRUPACION"
    col_h1_estado = "ESTADO HORA"

    col_h2_prof = "PROFESIONAL"
    col_h2_esp = "ESPECIALIDAD"

    col_h3_prof = "PROFESIONAL LEY 18"

    # =========================
    # VALIDACION
    # =========================
    for col in [col_h1_prof, col_h1_agr, col_h1_estado]:
        if col not in hoja1.columns:
            st.error(f"Falta columna en Hoja 1: {col}")
            st.stop()

    if col_h2_prof not in hoja2.columns or col_h2_esp not in hoja2.columns:
        st.error("Hoja 2 inválida")
        st.stop()

    if col_h3_prof not in hoja3.columns:
        st.error("Hoja 3 inválida")
        st.stop()

    # =========================
    # BASE
    # =========================
    df_asignadas = hoja1[
        hoja1[col_h1_estado].astype(str).str.upper().eq("ASIGNADA")
    ].copy()

    # =========================
    # PADRONES
    # =========================
    medicos_hoja2 = set(
        hoja2[col_h2_prof].astype(str).str.strip().str.upper()
    )

    no_medicos_hoja3 = set(
        hoja3[col_h3_prof].astype(str).str.strip().str.upper()
    )

    especialidades = dict(
        zip(
            hoja2[col_h2_prof].astype(str).str.strip().str.upper(),
            hoja2[col_h2_esp].astype(str).str.strip()
        )
    )

    # =========================
    # AGRUPACIONES
    # =========================
    agrup_medicos = {
        "MEDICO APS",
        "MEDICO ESPECIALISTA",
        "ODONTOLOGIA APS",
        "ODONTOLOGIA ESPECIALIDADES",
        "QUIMICO FARMACEUTICO"
    }

    agrup_no_medicos = {
        "TERAPEUTA OCUPACIONAL",
        "PSICOLOGIA",
        "ENFERMERA(O)",
        "ASISTENTE SOCIAL",
        "NUTRICIONISTA",
        "TECNOLOGO MEDICO",
        "FONOAUDIOLOGO",
        "MATRON(A)",
        "KINESIOLOGO"
    }

    # =========================
    # CLASIFICACION
    # =========================
    tipos = []
    especialidad_final = []
    desconocidos_proc = []

    for _, fila in df_asignadas.iterrows():

        prof = str(fila[col_h1_prof]).strip().upper()
        agr = str(fila[col_h1_agr]).strip().upper()

        # ==========================================
        # PRIORIDAD 1: NO MÉDICOS DE HOJA 3
        # ==========================================
        # Si el profesional aparece en Hoja 3,
        # SIEMPRE será considerado NO MÉDICO,
        # aunque su agrupación sea médica.
        if prof in no_medicos_hoja3:
            tipos.append("NO_MEDICO")
            especialidad_final.append(None)

        # ==========================================
        # PRIORIDAD 2: AGRUPACIONES MÉDICAS
        # ==========================================
        elif agr in agrup_medicos:
            tipos.append("MEDICO")
            especialidad_final.append(
                especialidades.get(prof, "SIN ESPECIALIDAD")
            )

        # ==========================================
        # PRIORIDAD 3: AGRUPACIONES NO MÉDICAS
        # ==========================================
        elif agr in agrup_no_medicos:
            tipos.append("NO_MEDICO")
            especialidad_final.append(None)

        # ==========================================
        # PROCEDIMIENTO
        # ==========================================
        elif agr == "PROCEDIMIENTO":

            if prof in medicos_hoja2:
                tipos.append("MEDICO")
                especialidad_final.append(
                    especialidades.get(prof, "SIN ESPECIALIDAD")
                )

            elif prof in no_medicos_hoja3:
                tipos.append("NO_MEDICO")
                especialidad_final.append(None)

            else:
                tipos.append("PROC_DUDOSO")
                especialidad_final.append(None)
                desconocidos_proc.append(prof)

        else:
            tipos.append("PROC_DUDOSO")
            especialidad_final.append(None)
            desconocidos_proc.append(prof)

    df_asignadas["TIPO_PROFESIONAL"] = tipos
    df_asignadas["ESPECIALIDAD_FINAL"] = especialidad_final

    # =========================
    # PREGUNTA PROCEDIMIENTO
    # =========================
    st.subheader("🔎 Revisión PROCEDIMIENTO")

    nuevos_medicos = []
    nuevos_no_medicos = []

    for prof in sorted(set(desconocidos_proc)):

        st.warning(f"{prof} no está en Hoja 2 ni Hoja 3")

        tipo = st.radio(
            f"{prof} es:",
            ["No Médico", "Médico"],
            key=prof
        )

        if tipo == "Médico":

            esp = st.text_input(
                f"Especialidad {prof}",
                key=f"esp_{prof}"
            )

            if esp:
                nuevos_medicos.append({
                    "PROFESIONAL": prof,
                    "ESPECIALIDAD": esp
                })

                medicos_hoja2.add(prof)
                especialidades[prof] = esp

        else:
            nuevos_no_medicos.append(prof)
            no_medicos_hoja3.add(prof)

    # =========================
    # RECLASIFICACION FINAL
    # =========================
    def clasificar(prof, agr):

        prof = str(prof).strip().upper()
        agr = str(agr).strip().upper()

        # ==========================================
        # PRIORIDAD 1: LISTA DE NO MÉDICOS - HOJA 3
        # ==========================================
        # Si el profesional aparece en Hoja 3,
        # SIEMPRE será considerado NO MÉDICO,
        # aunque su agrupación diga MEDICO.
        if prof in no_medicos_hoja3:
            return "NO_MEDICO"

        # ==========================================
        # PRIORIDAD 2: AGRUPACIONES MÉDICAS
        # ==========================================
        if agr in agrup_medicos:
            return "MEDICO"

        # ==========================================
        # PRIORIDAD 3: AGRUPACIONES NO MÉDICAS
        # ==========================================
        if agr in agrup_no_medicos:
            return "NO_MEDICO"

        # ==========================================
        # PRIORIDAD 4: PROCEDIMIENTO
        # ==========================================
        if agr == "PROCEDIMIENTO":

            if prof in medicos_hoja2:
                return "MEDICO"

            if prof in no_medicos_hoja3:
                return "NO_MEDICO"

            return "PROC_DUDOSO"

        return "PROC_DUDOSO"

    df_asignadas["TIPO_PROFESIONAL"] = df_asignadas.apply(
        lambda r: clasificar(r[col_h1_prof], r[col_h1_agr]),
        axis=1
    )

    df_asignadas["ESPECIALIDAD_FINAL"] = df_asignadas.apply(
        lambda r: (
            especialidades.get(
                str(r[col_h1_prof]).strip().upper(),
                "SIN ESPECIALIDAD"
            )
            if r["TIPO_PROFESIONAL"] == "MEDICO"
            else None
        ),
        axis=1
    )
# ============================================================
# 📊 GRÁFICOS DE ASIGNADAS
# ============================================================

st.markdown("## 📊 Análisis de Horas ASIGNADAS")

# ============================================================
# VALIDAR FECHA
# ============================================================

if "FECHA" not in df_asignadas.columns:

    st.error(
        "La Hoja 1 no contiene la columna FECHA."
    )

else:

    # --------------------------------------------------------
    # COPIA EXCLUSIVA DE LAS ASIGNADAS
    # --------------------------------------------------------

    df_grafico = df_asignadas.copy()

    # --------------------------------------------------------
    # FECHA
    # --------------------------------------------------------

    df_grafico["FECHA"] = pd.to_datetime(
        df_grafico["FECHA"],
        errors="coerce"
    )

    # Eliminar solamente fechas inválidas
    df_grafico = df_grafico[
        df_grafico["FECHA"].notna()
    ].copy()

    # --------------------------------------------------------
    # AÑO
    # --------------------------------------------------------

    df_grafico["AÑO"] = (
        df_grafico["FECHA"].dt.year
    )

    # --------------------------------------------------------
    # MES
    # --------------------------------------------------------

    df_grafico["MES_NUM"] = (
        df_grafico["FECHA"].dt.month
    )

    meses = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre"
    }

    df_grafico["MES"] = (
        df_grafico["MES_NUM"].map(meses)
    )

    # ========================================================
    # ESPECIALIDAD
    # ========================================================

    # Aquí usamos ESPECIALIDAD_FINAL SOLO SI EXISTE.
    # Si no existe, todos los registros se mantienen.

    if "ESPECIALIDAD_FINAL" in df_grafico.columns:

        df_grafico["ESPECIALIDAD_GRAFICO"] = (
            df_grafico["ESPECIALIDAD_FINAL"]
            .fillna("NO INFORMADA")
            .astype(str)
            .str.strip()
        )

    else:

        df_grafico["ESPECIALIDAD_GRAFICO"] = (
            "NO INFORMADA"
        )

    # ========================================================
    # POLICLÍNICO
    # ========================================================

    if "POLICLINICO" in df_grafico.columns:

        df_grafico["POLICLINICO_GRAFICO"] = (
            df_grafico["POLICLINICO"]
            .fillna("SIN POLICLINICO")
            .astype(str)
            .str.strip()
        )

    else:

        st.error(
            "La Hoja 1 no contiene la columna POLICLINICO."
        )

        st.stop()

    # ========================================================
    # FILTRO DE AÑO
    # ========================================================

    años_disponibles = sorted(
        df_grafico["AÑO"]
        .dropna()
        .unique()
        .tolist()
    )

    if not años_disponibles:

        st.warning(
            "No existen fechas válidas para generar los gráficos."
        )

    else:

        año_seleccionado = st.selectbox(
            "Seleccionar año",
            años_disponibles
        )

        df_grafico = df_grafico[
            df_grafico["AÑO"] == año_seleccionado
        ].copy()

        # ====================================================
        # GRÁFICO 1
        # ESPECIALIDADES
        # ====================================================

        st.markdown(
            "### 👨‍⚕️ Horas ASIGNADAS por Especialidad"
        )

        tabla_especialidad = (
            df_grafico
            .groupby(
                [
                    "ESPECIALIDAD_GRAFICO",
                    "MES_NUM",
                    "MES"
                ],
                dropna=False
            )
            .size()
            .reset_index(
                name="TOTAL_ASIGNADAS"
            )
            .sort_values(
                [
                    "ESPECIALIDAD_GRAFICO",
                    "MES_NUM"
                ]
            )
        )

        fig_especialidad = px.bar(
            tabla_especialidad,
            x="TOTAL_ASIGNADAS",
            y="ESPECIALIDAD_GRAFICO",
            color="MES",
            orientation="h",
            barmode="group",
            category_orders={
                "MES": list(meses.values())
            },
            labels={
                "TOTAL_ASIGNADAS": "Total ASIGNADAS",
                "ESPECIALIDAD_GRAFICO": "Especialidad",
                "MES": "Mes"
            },
            title=(
                f"Total de Horas ASIGNADAS por "
                f"Especialidad - {año_seleccionado}"
            )
        )

        fig_especialidad.update_layout(
            xaxis_title="Total de horas ASIGNADAS",
            yaxis_title="Especialidad",
            legend_title="Mes",
            height=700
        )

        st.plotly_chart(
            fig_especialidad,
            use_container_width=True
        )

        # ====================================================
        # GRÁFICO 2
        # POLICLÍNICO
        # ====================================================

        st.markdown(
            "### 🏥 Horas ASIGNADAS por Policlínico"
        )

        tabla_policlinico = (
            df_grafico
            .groupby(
                [
                    "POLICLINICO_GRAFICO",
                    "MES_NUM",
                    "MES"
                ],
                dropna=False
            )
            .size()
            .reset_index(
                name="TOTAL_ASIGNADAS"
            )
            .sort_values(
                [
                    "POLICLINICO_GRAFICO",
                    "MES_NUM"
                ]
            )
        )

        fig_policlinico = px.bar(
            tabla_policlinico,
            x="TOTAL_ASIGNADAS",
            y="POLICLINICO_GRAFICO",
            color="MES",
            orientation="h",
            barmode="group",
            category_orders={
                "MES": list(meses.values())
            },
            labels={
                "TOTAL_ASIGNADAS": "Total ASIGNADAS",
                "POLICLINICO_GRAFICO": "Policlínico",
                "MES": "Mes"
            },
            title=(
                f"Total de Horas ASIGNADAS por "
                f"Policlínico - {año_seleccionado}"
            )
        )

        fig_policlinico.update_layout(
            xaxis_title="Total de horas ASIGNADAS",
            yaxis_title="Policlínico",
            legend_title="Mes",
            height=700
        )

        st.plotly_chart(
            fig_policlinico,
            use_container_width=True
        )

    # =========================
    # BASES
    # =========================
    df_medicos = df_asignadas[df_asignadas["TIPO_PROFESIONAL"] == "MEDICO"].copy()
    df_no_medicos = df_asignadas[df_asignadas["TIPO_PROFESIONAL"] == "NO_MEDICO"].copy()
    df_proc = df_asignadas[df_asignadas["TIPO_PROFESIONAL"] == "PROC_DUDOSO"].copy()

    df_medicos["OMISIONES"] = 1
    df_no_medicos["OMISIONES"] = 1

   
    st.markdown("## 📊 Resumen General de Omisiones")
   
    total_asignadas = len(df_asignadas)
    total_medicos = len(df_medicos)
    total_no_medicos = len(df_no_medicos)
   
    col1, col2, col3 = st.columns(3)
   
    col1.metric(
        "Total Omisiones (Asignadas)",
        total_asignadas
    )
   
    col2.metric(
        "Omisiones Médicos",
        total_medicos
    )
   
    col3.metric(
        "Omisiones No Médicos",
        total_no_medicos
    )
   
    # =========================
    # TABLA 1 RESUMEN MEDICOS
    # =========================
    tabla_resumen_medicos = (
        df_medicos.groupby("ESPECIALIDAD_FINAL")
        .size()
        .reset_index(name="TOTAL ASIGNADAS")
    )

    # =========================
    # TABLA 2 DETALLE MEDICOS
    # =========================
    tabla_medicos_detalle = (
        df_medicos.groupby(["ESPECIALIDAD_FINAL", col_h1_prof])
        .size()
        .reset_index(name="TOTAL ASIGNADAS")
    )

    tabla_medicos_detalle = tabla_medicos_detalle.rename(columns={
        "ESPECIALIDAD_FINAL": "ESPECIALIDAD",
        col_h1_prof: "NOMBRE PROFESIONAL"
    })

    # =========================
    # TABLA 3 PACIENTES MEDICOS
    # =========================
    tabla_medicos_pacientes = df_medicos.groupby(
        ["ESPECIALIDAD_FINAL","RUT PROFESIONAL", col_h1_prof, "RUT PACIENTE", "NOMBRE PACIENTE", "FECHA"],
        dropna=False
    ).size().reset_index(name="OMISIONES")

    tabla_medicos_pacientes = tabla_medicos_pacientes.rename(columns={
        "ESPECIALIDAD_FINAL": "ESPECIALIDAD",
        col_h1_prof: "NOMBRE PROFESIONAL"
    })

    # =========================
    # TABLA 4 RESUMEN NO MEDICOS
    # =========================
    tabla_resumen_no_medicos = (
        df_no_medicos.groupby("POLICLINICO")
        .size()
        .reset_index(name="TOTAL ASIGNADAS")
    )

    # =========================
    # TABLA 5 DETALLE NO MEDICOS
    # =========================
    tabla_no_medicos_detalle = (
        df_no_medicos.groupby([col_h1_prof, "POLICLINICO"])
        .size()
        .reset_index(name="TOTAL ASIGNADAS")
    )

    tabla_no_medicos_detalle = tabla_no_medicos_detalle.rename(columns={
        col_h1_prof: "NOMBRE PROFESIONAL"
    })

    # =========================
    # TABLA 6 PACIENTES NO MEDICOS
    # =========================
    tabla_no_medicos_pacientes = df_no_medicos.groupby(
        ["POLICLINICO","RUT PROFESIONAL", col_h1_prof, "RUT PACIENTE", "NOMBRE PACIENTE", "FECHA"]
    ).size().reset_index(name="TOTAL ASIGNADAS")

    tabla_no_medicos_pacientes = tabla_no_medicos_pacientes.rename(columns={
        col_h1_prof: "NOMBRE PROFESIONAL"
    })

    # =========================
    # EXPORT
    # =========================
    salida = BytesIO()

    with pd.ExcelWriter(salida, engine="xlsxwriter") as writer:

        tabla_resumen_medicos.to_excel(writer, sheet_name="Resumen Medicos", index=False)
        tabla_medicos_detalle.to_excel(writer, sheet_name="Detalle Medicos", index=False)
        tabla_medicos_pacientes.to_excel(writer, sheet_name="Pacientes Medicos", index=False)

        tabla_resumen_no_medicos.to_excel(writer, sheet_name="Resumen No Medicos", index=False)
        tabla_no_medicos_detalle.to_excel(writer, sheet_name="Detalle No Medicos", index=False)
        tabla_no_medicos_pacientes.to_excel(writer, sheet_name="Pacientes No Medicos", index=False)

        if nuevos_medicos:
            pd.DataFrame(nuevos_medicos).to_excel(writer, sheet_name="Nuevos Medicos", index=False)

    st.download_button(
        "Descargar Excel",
        data=salida.getvalue(),
        file_name="resultado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
# =========================
# BASE ASIGNADAS
# =========================

df_asignadas = hoja1.copy()

# Normalizar ESTADO HORA
df_asignadas[col_h1_estado] = (
    df_asignadas[col_h1_estado]
    .astype(str)
    .str.strip()
    .str.upper()
)

# SOLO ASIGNADAS DE HOJA 1
df_asignadas = df_asignadas[
    df_asignadas[col_h1_estado] == "ASIGNADA"
].copy()

st.info(
    f"Registros ASIGNADA encontrados en Hoja 1: "
    f"{len(df_asignadas):,}"
)
