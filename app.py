import streamlit as st
import duckdb
import pandas as pd
import os
import altair as alt
import time


# 1. Configuración de página e inicialización de Memoria
st.set_page_config(page_title="Gestor EPS", layout="wide", initial_sidebar_state="expanded")

if 'macro_activa' not in st.session_state:
    st.session_state.macro_activa = False

if 'modulo_activo' not in st.session_state:
    st.session_state.modulo_activo = "Bases de Datos"

def activar_macro():
    st.session_state.macro_activa = True

def desactivar_macro():
    st.session_state.macro_activa = False

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] { background: transparent !important; }
        .stDeployButton {display: none !important;}
        
        .block-container {padding-top: 1rem; padding-bottom: 1rem;}
        
        /* OCULTAR SCROLLBAR VISUALMENTE */
        [data-testid="stSidebar"] [data-overlayscrollbars-viewport] {
            scrollbar-width: none !important;
            -ms-overflow-style: none !important;
        }
        [data-testid="stSidebar"] [data-overlayscrollbars-viewport]::-webkit-scrollbar {
            display: none !important;
        }
        
        /* =========================================================
           1. BOTÓN DE SIDEBAR (Minimalista y poco intrusivo)
           ========================================================= */
        [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {
            top: 0.5rem !important; 
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #64748b !important; /* Gris oscuro sutil */
            transition: all 0.3s ease !important;
        }
        [data-testid="stSidebarCollapseButton"]:hover, [data-testid="collapsedControl"]:hover {
            color: #38bdf8 !important; /* Celeste al pasar el ratón */
            background: rgba(56, 189, 248, 0.1) !important;
            border-radius: 50% !important;
        }

        /* =========================================================
           2. NAVEGACIÓN Y BOTONES CON EFECTO HOVER (Tamaño Exacto)
           ========================================================= */
        [data-testid="stRadio"] { width: 100% !important; }
        div[role="radiogroup"] { width: 100% !important; gap: 4px !important; }
        
        /* 1. Forzar ALTURA EXACTA y alineación a la IZQUIERDA perfecta */
        div[role="radiogroup"] > label, 
        [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
            width: 100% !important;
            height: 42px !important;
            min-height: 42px !important;
            max-height: 42px !important;
            background: transparent !important;
            border: none !important;
            border-left: 3px solid transparent !important;
            border-radius: 0 8px 8px 0 !important;
            padding: 0 0 0 25px !important; 
            margin: 0 !important;
            color: #94a3b8 !important;
            box-shadow: none !important;
            transition: all 0.2s ease-in-out !important;
            display: flex !important;
            justify-content: flex-start !important; 
            align-items: center !important;
            box-sizing: border-box !important;
        }
        
        /* 2. Forzar que el texto no baile y se pegue a la izquierda */
        div[role="radiogroup"] > label p,
        [data-testid="stSidebar"] .stButton > button[kind="secondary"] div,
        [data-testid="stSidebar"] .stButton > button[kind="secondary"] p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
            text-align: left !important; 
            width: 100% !important;
        }
            
        /* 3. Efecto Sombreado al pasar el ratón */
        div[role="radiogroup"] > label:hover, 
        [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
            background: rgba(255, 255, 255, 0.05) !important;
            color: #e2e8f0 !important;
            border-left: 3px solid rgba(255, 255, 255, 0.2) !important;
        }
        
        /* 4. Efecto Activo SOLO para el módulo actualmente seleccionado */
        div[role="radiogroup"] > label:has(input:checked) {
            background: rgba(56, 189, 248, 0.1) !important;
            border-left: 3px solid #38bdf8 !important;
        }
        div[role="radiogroup"] > label:has(input:checked) p {
            color: #38bdf8 !important;
            font-weight: 700 !important;
        }
        
        /* 5. Ocultar el círculo nativo de selección */
        div[role="radiogroup"] > label > div:first-child { display: none !important; }
            
        /* 6. Truco para eliminar el espacio invisible que separa los botones de los módulos */
        [data-testid="stSidebar"] .element-container:has(button[kind="secondary"]) {
            margin-top: -12px !important; 
        }    
            
        /* =========================================================
           3. TARJETAS DE GRÁFICOS CON BORDES CURVOS
           ========================================================= */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 15px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            background: rgba(30, 41, 59, 0.2) !important;
            padding: 1rem !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Conexión al Motor DuckDB (Blindada con Caché)
@st.cache_resource
def iniciar_conexion():
    return duckdb.connect('base_datos_eps.db')

conn = iniciar_conexion()

def procesar_dataframe(df):
    # 1. Limpieza extrema
    df.columns = df.columns.astype(str).str.replace('ï»¿', '').str.replace('\ufeff', '').str.strip().str.lower().str.replace(' ', '_')
    
    # 2. Borrar las columnas si la EPS llega a mandarlas
    columnas_basura = ['v_f', 'pendiente_conciliar', 'llave_maestra', '#']
    for col in columnas_basura:
        if col in df.columns:
            df = df.drop(columns=[col])

    # 3. BLINDAJE: Aseguramos que las llaves existan
    for col in ['numero_recepcion', 'numero_radicacion', 'factura']:
        if col not in df.columns:
            df[col] = 'SIN_DATO'

    df['numero_recepcion'] = df['numero_recepcion'].fillna('SIN_REC').astype(str).str.replace(r'\.0$', '', regex=True)
    df['numero_radicacion'] = df['numero_radicacion'].fillna('SIN_RAD').astype(str).str.replace(r'\.0$', '', regex=True)
    df['factura'] = df['factura'].fillna('SIN_FAC').astype(str).str.replace(r'\.0$', '', regex=True)
    
    df['llave_maestra'] = df['numero_recepcion'] + '_' + df['numero_radicacion'] + '_' + df['factura']
    
    columnas_financieras = [
        'total_cuota_moderadora', 'total_copago', 'valor_neto', 'valor_factura', 
        'valor_contrato', 'total_servicios', 'total_glosas', 'valor_aceptado_ips_1', 
        'saldo_ips_1', 'valor_aceptado_eps_1', 'saldo_eps_1', 'valor_aceptado_ips_2', 
        'saldo_ips_2', 'valor_aceptado_eps_2', 'saldo_eps_2', 'valor_aceptado_ips_gerencial', 
        'valor_aceptado_eps_gerencial', 'valor_total_acepta_eps', 'valor_total_acepta_ips'
    ]
    
    for col in columnas_financieras:
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].astype(str).replace(r'[^\d.-]', '', regex=True)
        # 🛡️ LA SOLUCIÓN: Convertimos a int64 ANTES de que toque la base de datos
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')

    df['V_F'] = (df['total_glosas'] == (df['valor_total_acepta_ips'] + df['valor_total_acepta_eps']))
    df['V_F'] = df['V_F'].map({True: 'VERDADERO', False: 'FALSO'})
    
    df['PENDIENTE_CONCILIAR'] = df['total_glosas'] - (df['valor_total_acepta_ips'] + df['valor_total_acepta_eps'])
    
    cols_base = [c for c in df.columns if c not in ['llave_maestra', 'V_F', 'PENDIENTE_CONCILIAR']]
    if 'valor_total_acepta_ips' in cols_base:
        idx = cols_base.index('valor_total_acepta_ips') + 1
        cols_base.insert(idx, 'V_F')
        cols_base.insert(idx + 1, 'PENDIENTE_CONCILIAR')
    else:
        cols_base.extend(['V_F', 'PENDIENTE_CONCILIAR'])
        
    columnas_finales = ['llave_maestra'] + cols_base
    # 4. BLINDAJE ABSOLUTO DE FECHAS MÚLTIPLES (Extracción manual sin motores de Python)
    def extraer_fecha_exacta(val):
        if pd.isna(val) or str(val).strip().lower() in ['nan', 'nat', 'none', '']:
            return None
        val = str(val).strip().split(' ')[0].replace('-', '/')
        if '/' in val:
            partes = val.split('/')
            if len(partes) == 3:
                # Si el archivo crudo viene como DD/MM/YYYY (El año está al final)
                if len(partes[2]) == 4:
                    return f"{partes[0].zfill(2)}/{partes[1].zfill(2)}/{partes[2]}"
                # Si el archivo crudo viene como YYYY/MM/DD (El año está al inicio)
                elif len(partes[0]) == 4:
                    return f"{partes[2].zfill(2)}/{partes[1].zfill(2)}/{partes[0]}"
        return None

    # Lista con todas tus columnas de fechas a blindar
    columnas_fechas = [
        'fecha_radicado', 'fecha_servicio_inicio_rips', 'fecha_servicio_fin_rips', 
        'fecha_inicio', 'fecha_fin', 'fecha_expedicion', 'fecha_cierre_auditoria_tecnica', 
        'fecha_notificado', 'fecha_maxima_glosa_1_ips', 'fecha_respuesta_ips_glosa_1', 
        'fecha_maxima_glosa_1_eps', 'fecha_respuesta_eps_glosa_1', 'fecha_maxima_glosa_2_ips', 
        'fecha_respuesta_ips_glosa_2', 'fecha_maxima_glosa_2_eps', 'fecha_respuesta_eps_glosa_2', 
        'fecha_conciliacion_gerencial'
    ]

    # Le pasamos la barredora a cada columna de la lista si existe en el archivo
    for col_fecha in columnas_fechas:
        if col_fecha in df.columns:
            df[col_fecha] = df[col_fecha].apply(extraer_fecha_exacta)
    
    columnas_finales = ['llave_maestra'] + cols_base
    return df[columnas_finales]

# 3. Panel Lateral
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 15px 10px; background-color: #0f172a; border-radius: 10px; border: 1px solid #1e293b; margin-bottom: 25px;'>
            <h3 style='margin: 0; color: #38bdf8; font-weight: 800; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 1px;'>Auditoría de Cuentas Medicas</h3>
            <p style='margin: 5px 0 0 0; font-size: 0.8rem; color: #94a3b8;'>Creada por <b style='color: #e2e8f0;'>Elthon Herrera</b></p>
        </div>
    """, unsafe_allow_html=True)

    # --- 1. BLOQUE DE MÓDULOS ---
    st.session_state.modulo_activo = st.radio(
        "Navegación:", 
        ["Bases de Datos", "KPIs", "Dinámica", "Gerencial", "Seguimiento Operativo", "Detalle de Glosas"], 
        label_visibility="collapsed"
    )
    
    # --- 3. LÍNEA DIVISORIA Y ESPACIO ---
    st.write("---")
    st.markdown("<div style='height: 2vh;'></div>", unsafe_allow_html=True)
    
    # --- 4. BLOQUE DE CARGA MULTI-ARCHIVOS (Aislado abajo) ---
    st.markdown("<div style='text-align: center;'><p style='font-size: 0.95rem; font-weight: bold; color: #e2e8f0; margin-bottom: 10px;'>Cargar Documento(s)</p></div>", unsafe_allow_html=True)
    
    # 🎯 MAGIA UI: Activamos la subida de múltiples archivos
    archivos_nuevos = st.file_uploader("", type=['csv'], accept_multiple_files=True, label_visibility="collapsed")
    
    if archivos_nuevos:
        if st.button(f"Procesar {len(archivos_nuevos)} Archivo(s)", use_container_width=True, type="primary"):
            try:
                tiempo_inicio = time.time()
                with st.spinner("Procesando y fusionando datos..."):
                    lista_tablas = []
                    
                    # 1. Leemos cada archivo bloqueando conversiones automáticas (dtype=str)
                    for archivo in archivos_nuevos:
                        df_temp = None
                        for codificacion in ['utf-8-sig', 'latin-1', 'cp1252']:
                            try:
                                archivo.seek(0)
                                df_temp = pd.read_csv(archivo, sep=';', encoding=codificacion, low_memory=False, dtype=str)
                                if len(df_temp.columns) >= 10: break
                            except:
                                pass
                                
                        if df_temp is None or len(df_temp.columns) < 10:
                            for codificacion in ['utf-8-sig', 'latin-1', 'cp1252']:
                                try:
                                    archivo.seek(0)
                                    df_temp = pd.read_csv(archivo, sep=',', encoding=codificacion, low_memory=False, dtype=str)
                                    if len(df_temp.columns) >= 10: break
                                except:
                                    pass
                                    
                        if df_temp is not None:
                            lista_tablas.append(df_temp)
                    
                    df_nuevo_consolidado = pd.concat(lista_tablas, ignore_index=True)
                    df_nuevo = procesar_dataframe(df_nuevo_consolidado)
                    tablas = conn.execute("SHOW TABLES").df()
                    
                    if tablas.empty or 'facturas' not in tablas['name'].values:
                        conn.execute("CREATE TABLE facturas AS SELECT * FROM df_nuevo")
                        tiempo_fin = time.time()
                        ms = int((tiempo_fin - tiempo_inicio) * 1000)
                        st.toast(f"Base inicializada con {len(archivos_nuevos)} archivos en {ms} ms", icon="🚀")
                        st.rerun()
                    else:
                        cols_db = conn.execute("DESCRIBE facturas").df()['column_name'].tolist()
                        
                        # 1. Si el archivo no trae columnas viejas, las rellenamos con nulo para no romper nada
                        for c in cols_db:
                            if c not in df_nuevo.columns:
                                df_nuevo[c] = None
                                
                        # 2. 🎯 EL ARREGLO: Si el archivo trae columnas NUEVAS, alteramos la base de datos para agregarlas dinámicamente
                        columnas_nuevas = [c for c in df_nuevo.columns if c not in cols_db]
                        for c_nueva in columnas_nuevas:
                            # Agregamos la columna a la estructura de la base de datos
                            conn.execute(f"ALTER TABLE facturas ADD COLUMN \"{c_nueva}\" VARCHAR")
                            
                        # Recargamos la lista de columnas para asegurarnos de que todo empate perfectamente
                        cols_db_actualizadas = conn.execute("DESCRIBE facturas").df()['column_name'].tolist()
                        df_nuevo = df_nuevo[cols_db_actualizadas] 
                        
                        conteo_antes = conn.execute("SELECT COUNT(*) FROM facturas").fetchone()[0]
                        conn.execute("""
                            INSERT INTO facturas
                            SELECT * FROM df_nuevo
                            WHERE llave_maestra NOT IN (SELECT llave_maestra FROM facturas)
                        """)
                        conteo_despues = conn.execute("SELECT COUNT(*) FROM facturas").fetchone()[0]
                        tiempo_fin = time.time()
                        ms = int((tiempo_fin - tiempo_inicio) * 1000)
                        st.toast(f"Sincronizados {conteo_despues - conteo_antes} registros en {ms} ms.", icon="⚡")
            except Exception as e:
                st.error(f"Fallo crítico: {e}")

# 4. Enrutador de Pantallas
try:
    total_registros = conn.execute("SELECT COUNT(*) FROM facturas").fetchone()[0]
    esquema_db = conn.execute("DESCRIBE facturas").df()
    columnas_db = esquema_db['column_name'].tolist()

    # =========================================================================
    # PANTALLA 1: BASES DE DATOS
    # =========================================================================
    if st.session_state.modulo_activo == "Bases de Datos":
        columnas_texto = esquema_db[esquema_db['column_type'].str.contains('VARCHAR')]['column_name'].tolist()
        columnas_busqueda_rapida = list(set(columnas_texto + ['llave_maestra']))
        
        header_container = st.container()
        st.write("") 
        
        # NUEVA DISTRIBUCIÓN DE COLUMNAS (Fila 1)
        col_busqueda, col_vf, col_macro, col_copiar, col_export = st.columns([3.5, 2, 2, 2.5, 2])
        
        # --- 1. ESTADO V_F (Fila 1) ---
        with col_vf:
            filtro_vf = st.selectbox("Estado V_F", ["Todos los Estados", "VERDADERO", "FALSO"], label_visibility="collapsed", key="memoria_vf")

        # --- 2. LECTURA DE MEMORIA PARA CASCADA ---
        cond_memoria = "1=1"
        if filtro_vf == "VERDADERO": cond_memoria += " AND \"V_F\" = 'VERDADERO'"
        elif filtro_vf == "FALSO": cond_memoria += " AND \"V_F\" = 'FALSO'"
        
        m_tipo = st.session_state.get("memoria_tipo_busq", "🔍 Global")
        m_cols = {"🏢 Razón Social": "razon_social", "🆔 NIT": "nit", "🧾 Factura": "factura", "📦 Radicado": "numero_radicacion"}
        m_term = ""
        
        if m_tipo == "🔍 Global":
            m_term = st.session_state.get("memoria_global", "")
        else:
            c_db_mem = m_cols.get(m_tipo)
            if m_tipo in ["🏢 Razón Social", "🆔 NIT"]:
                m_term = st.session_state.get(f"memoria_select_{c_db_mem}", "")
            else:
                m_term = st.session_state.get(f"memoria_text_{c_db_mem}", "")
                
        if m_term and str(m_term).strip() != "" and str(m_term).strip().lower() != "none":
            term_l = str(m_term).replace("'", "''")
            if m_tipo == "🔍 Global":
                c_glob = [f"\"{c}\" ILIKE '%{term_l}%'" for c in columnas_busqueda_rapida]
                cond_memoria += " AND (" + " OR ".join(c_glob) + ")"
            else:
                c_db_mem = m_cols.get(m_tipo)
                cond_memoria += f" AND CAST(\"{c_db_mem}\" AS VARCHAR) ILIKE '%{term_l}%'"

        # --- 3. BOTONES DE FILTROS INDEPENDIENTES (Fila 2) ---
        cf1, cf2, cf3, cf4, cf5, cf6 = st.columns(6)
        
        filtros_sql = []
        
        def crear_btn_filtro(col, titulo, col_db):
            with col:
                clave = f"frap_{col_db}"
                activos = st.session_state.get(clave, [])
                label_btn = f"🟢 {titulo}" if activos else titulo
                
                with st.popover(label_btn, use_container_width=True):
                    if col_db in columnas_db:
                        # 🎯 NUEVO: Lógica de CASCADA para leer otros filtros activos en la sesión
                        cond_cascada = ""
                        for key, val in st.session_state.items():
                            if key.startswith("frap_") and key != clave and val and isinstance(val, list):
                                c_otra = key.replace("frap_", "")
                                if c_otra in columnas_db:
                                    v_norm_otra = [v for v in val if v != "Sin Estado"]
                                    cond_col_otra = []
                                    if v_norm_otra:
                                        v_limpios = [v.replace("'", "''") for v in v_norm_otra]
                                        in_clause = ", ".join([f"'{v}'" for v in v_limpios])
                                        cond_col_otra.append(f"CAST(\"{c_otra}\" AS VARCHAR) IN ({in_clause})")
                                    if "Sin Estado" in val:
                                        cond_col_otra.append(f"(\"{c_otra}\" IS NULL OR TRIM(CAST(\"{c_otra}\" AS VARCHAR)) = '' OR LOWER(CAST(\"{c_otra}\" AS VARCHAR)) IN ('nan', 'none'))")
                                    if cond_col_otra:
                                        cond_cascada += f" AND ({' OR '.join(cond_col_otra)})"

                        # Inyectamos la condición en cascada a las opciones del desplegable
                        query_opciones = f"SELECT DISTINCT \"{col_db}\" FROM facturas WHERE \"{col_db}\" IS NOT NULL AND TRIM(CAST(\"{col_db}\" AS VARCHAR)) != '' AND LOWER(CAST(\"{col_db}\" AS VARCHAR)) NOT IN ('nan', 'none') AND {cond_memoria} {cond_cascada}"
                        
                        try:
                            opciones_db = conn.execute(query_opciones).df()[col_db].astype(str).tolist()
                        except:
                            opciones_db = []
                            
                        if col_db == "estado_tecnica":
                            opciones_db.append("Sin Estado")
                            
                        for vg in activos:
                            if vg not in opciones_db: opciones_db.append(vg)
                            
                        valores_sel = st.multiselect(f"Seleccionar {titulo}:", sorted(opciones_db), key=clave, label_visibility="collapsed")
                        
                        if valores_sel:
                            condiciones_col = []
                            v_norm = [v for v in valores_sel if v != "Sin Estado"]
                            if v_norm:
                                v_limpios = [v.replace("'", "''") for v in v_norm]
                                in_clause = ", ".join([f"'{v}'" for v in v_limpios])
                                condiciones_col.append(f"CAST(\"{col_db}\" AS VARCHAR) IN ({in_clause})")
                            if "Sin Estado" in valores_sel:
                                condiciones_col.append(f"(\"{col_db}\" IS NULL OR TRIM(CAST(\"{col_db}\" AS VARCHAR)) = '' OR LOWER(CAST(\"{col_db}\" AS VARCHAR)) IN ('nan', 'none'))")
                            
                            if condiciones_col:
                                filtros_sql.append(f"({' OR '.join(condiciones_col)})")

        crear_btn_filtro(cf1, "Rango de Valores", "rango_factura")
        crear_btn_filtro(cf2, "Numero de Contrato", "numero_contrato")
        crear_btn_filtro(cf3, "Tipo de Contrato", "tipo_contrato")
        
        with cf4:
            hay_fechas = any(k.startswith('frap_meses_') and st.session_state.get(k) for k in st.session_state.keys())
            label_fechas = "🟢 Fecha de Radicado" if hay_fechas else "Fecha de Radicado"
            
            with st.popover(label_fechas, use_container_width=True):
                try:
                    # 1. Buscamos años reales cruzados con la memoria de búsqueda actual
                    anios_ext = conn.execute(f"SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL AND {cond_memoria}").df()
                    anios_validos = sorted([str(a) for a in anios_ext['anio'].dropna().tolist() if a != ''], reverse=True)
                    if not anios_validos: # Salvavidas
                        anios_ext = conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()
                        anios_validos = sorted([str(a) for a in anios_ext['anio'].dropna().tolist() if a != ''], reverse=True)
                except:
                    anios_validos = []

                if not anios_validos:
                    st.caption("No hay periodos en la base de datos.")

                nombres_meses = {'1':'Ene', '2':'Feb', '3':'Mar', '4':'Abr', '5':'May', '6':'Jun', '7':'Jul', '8':'Ago', '9':'Sep', '10':'Oct', '11':'Nov', '12':'Dic'}
                cond_am = []

                for anio in anios_validos:
                    # 2. Consultamos los meses REALES que existen para este año específico
                    try:
                        meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%' AND {cond_memoria}").df()['mes'].dropna().astype(int).tolist()
                        if not meses_reales:
                            meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%'").df()['mes'].dropna().astype(int).tolist()
                        meses_lista = [str(m) for m in sorted(meses_reales)]
                    except:
                        meses_lista = []
                        
                    if meses_lista:
                        # 3. Restauramos el diseño UI: Año a la izquierda, lista a la derecha (ocultando el título)
                        c_i, c_d = st.columns([1.2, 2.8])
                        with c_i: 
                            st.markdown(f"<div style='margin-top:6px; font-weight:700; color:#e2e8f0; font-size:14px;'>📅 {anio}</div>", unsafe_allow_html=True)
                        with c_d:
                            meses_sel = st.multiselect(f"Meses {anio}", options=meses_lista, format_func=lambda x: nombres_meses[x], key=f"frap_meses_{anio}", label_visibility="collapsed")
                        
                        if meses_sel:
                            m_str = ', '.join(meses_sel)
                            cond_am.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                        
                if cond_am:
                    filtros_sql.append(f"({' OR '.join(cond_am)})")

        crear_btn_filtro(cf5, "Auditor Asignado", "usuario_auditoria_tecnica")
        crear_btn_filtro(cf6, "Estado de Auditoria", "estado_tecnica")
        
        # --- 4. BUSCADOR PRINCIPAL BLINDADO (Fila 1) ---
        condicion_inteligente = "1=1"
        if filtro_vf == "VERDADERO": condicion_inteligente += " AND \"V_F\" = 'VERDADERO'"
        elif filtro_vf == "FALSO": condicion_inteligente += " AND \"V_F\" = 'FALSO'"
        if filtros_sql: condicion_inteligente += " AND " + " AND ".join(filtros_sql)

        with col_busqueda:
            c_tipo, c_valor = st.columns([1, 1.8])
            with c_tipo:
                tipo_busq = st.selectbox("Tipo", ["🔍 Global", "🏢 Razón Social", "🆔 NIT", "🧾 Factura", "📦 Radicado"], label_visibility="collapsed", key="memoria_tipo_busq")
            
            with c_valor:
                termino_busqueda = ""
                mapa_columnas = {"🏢 Razón Social": "razon_social", "🆔 NIT": "nit", "🧾 Factura": "factura", "📦 Radicado": "numero_radicacion"}
                
                if tipo_busq == "🔍 Global":
                    termino_busqueda = st.text_input("Valor", placeholder="Buscar en todo...", label_visibility="collapsed", key="memoria_global")
                else:
                    col_db = mapa_columnas[tipo_busq]
                    if col_db in columnas_db:
                        if tipo_busq in ["🏢 Razón Social", "🆔 NIT"]:
                            query_opciones = f"SELECT DISTINCT \"{col_db}\" FROM facturas WHERE \"{col_db}\" IS NOT NULL AND {condicion_inteligente}"
                            opciones = conn.execute(query_opciones).df()[col_db].astype(str).tolist()
                            
                            clave_select = f"memoria_select_{col_db}"
                            valor_guardado = st.session_state.get(clave_select)
                            if valor_guardado and valor_guardado not in opciones:
                                opciones.append(valor_guardado)
                                
                            termino_busqueda = st.selectbox("Valor", sorted(opciones), index=None, placeholder="Seleccione...", label_visibility="collapsed", key=clave_select)
                        else:
                            termino_busqueda = st.text_input("Valor", placeholder=f"Escriba {tipo_busq}...", label_visibility="collapsed", key=f"memoria_text_{col_db}")
                    else:
                        termino_busqueda = st.text_input("Valor", placeholder="Columna no hallada...", label_visibility="collapsed", key="memoria_fallback")
                        tipo_busq = "🔍 Global"

        with col_macro:
            # Cambiamos dinámicamente el título del popover si la macro está encendida
            label_vistas = f"🟢 Vista {st.session_state.macro_activa}" if st.session_state.macro_activa else "⚡ Vistas"
            
            with st.popover(label_vistas, use_container_width=True):
                if st.session_state.macro_activa:
                    def limpiar_vista(): st.session_state.macro_activa = False
                    st.button("Limpiar Vista", on_click=limpiar_vista, use_container_width=True, type="primary")
                else:
                    def activar_conciliacion(): st.session_state.macro_activa = "Conciliación"
                    def activar_capitado(): st.session_state.macro_activa = "Capitado"
                    def activar_aceptaciones(): st.session_state.macro_activa = "Aceptaciones" # NUEVO BOTÓN
                    
                    st.button("Conciliación", on_click=activar_conciliacion, use_container_width=True)
                    st.button("Capitado", on_click=activar_capitado, use_container_width=True)
                    st.button("Aceptaciones", on_click=activar_aceptaciones, use_container_width=True) # NUEVO BOTÓN

        with col_copiar:
            with st.popover("📋 Copiar Datos", use_container_width=True):
                if st.session_state.macro_activa == "Conciliación" or st.session_state.macro_activa is True:
                    cols_disponibles = ['factura', 'numero_radicacion', 'total_servicios', 'fecha_radicado', 'total_glosas', 'valor_total_acepta_eps', 'valor_total_acepta_ips', 'V_F', 'PENDIENTE_CONCILIAR']
                elif st.session_state.macro_activa == "Capitado":
                    cols_disponibles = [
                        'factura', 'numero_radicacion', 'valor_factura', 'fecha_radicado', 
                        'total_glosas', 'valor_total_acepta_eps', 'valor_total_acepta_ips', 
                        'PENDIENTE_CONCILIAR', 'fecha_servicio_inicio_rips', 'fecha_servicio_fin_rips', 
                        'tipo_regimen', 'numero_contrato', 'tipo_contrato'
                    ]
                elif st.session_state.macro_activa == "Aceptaciones": # 🎯 NUEVA VISTA
                    cols_disponibles = [
                        'factura', 'numero_radicacion', 'fecha_radicado', 'total_servicios', 
                        'total_glosas', 'valor_aceptado_ips_1', 'valor_aceptado_eps_1', 
                        'valor_aceptado_ips_2', 'valor_aceptado_eps_2', 'valor_aceptado_ips_gerencial', 
                        'valor_aceptado_eps_gerencial', 'valor_total_acepta_eps', 'valor_total_acepta_ips', 
                        'V_F', 'PENDIENTE_CONCILIAR'
                    ]
                else:
                    cols_disponibles = columnas_db
                
                cols_disponibles = [c for c in cols_disponibles if c in columnas_db]
                cols_por_defecto = cols_disponibles if st.session_state.macro_activa else columnas_db[:5]

                cols_elegidas = st.multiselect("Columnas a copiar:", cols_disponibles, placeholder="Selecciona casillas...", default=cols_por_defecto)
                
                if cols_elegidas:
                    if st.button("Confirmar Copia", use_container_width=True):
                        try:
                            with st.spinner("Procesando y copiando datos..."):
                                cond_copia = "1=1"
                                if filtro_vf == "VERDADERO": cond_copia += " AND \"V_F\" = 'VERDADERO'"
                                elif filtro_vf == "FALSO": cond_copia += " AND \"V_F\" = 'FALSO'"
                                if filtros_sql: cond_copia += " AND " + " AND ".join(filtros_sql)
                                
                                if termino_busqueda and termino_busqueda != "":
                                    term = termino_busqueda.replace("'", "''")
                                    if tipo_busq == "🔍 Global":
                                        conds = [f"\"{c}\" ILIKE '%{term}%'" for c in columnas_busqueda_rapida]
                                        cond_copia += " AND (" + " OR ".join(conds) + ")"
                                    else:
                                        col_db = mapa_columnas[tipo_busq]
                                        cond_copia += f" AND CAST(\"{col_db}\" AS VARCHAR) ILIKE '%{term}%'"
                                
                                cols_sql = ", ".join([f'"{c}"' for c in cols_elegidas])
                                query_final_copia = f"SELECT {cols_sql} FROM facturas WHERE {cond_copia}"
                                df_copia = conn.execute(query_final_copia).df()
                                
                                if not df_copia.empty:
                                    df_copia.to_clipboard(index=False, sep='\t')
                                    st.success(f"¡{len(df_copia):,} registros copiados!")
                                else:
                                    st.warning("No hay registros para copiar.")
                        except Exception as e:
                            st.error(f"Error al copiar: {e}")

        # Lógica de construcción de la Vista Activa
        if st.session_state.macro_activa == "Conciliación" or st.session_state.macro_activa is True:
            columnas_macro = ['factura', 'numero_radicacion', 'total_servicios', 'fecha_radicado', 'total_glosas', 'valor_total_acepta_eps', 'valor_total_acepta_ips', 'V_F', 'PENDIENTE_CONCILIAR']
        elif st.session_state.macro_activa == "Capitado":
            columnas_macro = [
                'factura', 'numero_radicacion', 'valor_factura', 'fecha_radicado', 
                'total_glosas', 'valor_total_acepta_eps', 'valor_total_acepta_ips', 
                'PENDIENTE_CONCILIAR', 'fecha_servicio_inicio_rips', 'fecha_servicio_fin_rips', 
                'tipo_regimen', 'numero_contrato', 'tipo_contrato'
            ]
        elif st.session_state.macro_activa == "Aceptaciones": # 🎯 NUEVA VISTA EN TABLA
            columnas_macro = [
                'factura', 'numero_radicacion', 'fecha_radicado', 'total_servicios', 
                'total_glosas', 'valor_aceptado_ips_1', 'valor_aceptado_eps_1', 
                'valor_aceptado_ips_2', 'valor_aceptado_eps_2', 'valor_aceptado_ips_gerencial', 
                'valor_aceptado_eps_gerencial', 'valor_total_acepta_eps', 'valor_total_acepta_ips', 
                'V_F', 'PENDIENTE_CONCILIAR'
            ]
        else:
            query_base = "SELECT * FROM facturas WHERE 1=1"
            columnas_macro = []

        if columnas_macro:
            columnas_existentes = [c for c in columnas_macro if c in columnas_db]
            columnas_sql = ", ".join([f'"{col}"' for col in columnas_existentes])
            query_base = f"SELECT {columnas_sql} FROM facturas WHERE 1=1"
        
        if filtro_vf == "VERDADERO":
            query_base += " AND \"V_F\" = 'VERDADERO'"
        elif filtro_vf == "FALSO":
            query_base += " AND \"V_F\" = 'FALSO'"
            
        if termino_busqueda and termino_busqueda != "":
            termino_limpio = termino_busqueda.replace("'", "''")
            if tipo_busq == "🔍 Global":
                condiciones_globales = [f"\"{col}\" ILIKE '%{termino_limpio}%'" for col in columnas_busqueda_rapida]
                query_base += " AND (" + " OR ".join(condiciones_globales) + ")"
            else:
                col_db = mapa_columnas[tipo_busq]
                query_base += f" AND CAST(\"{col_db}\" AS VARCHAR) ILIKE '%{termino_limpio}%'"
                
        if filtros_sql:
            query_base += " AND " + " AND ".join(filtros_sql)
            
        with col_export:
            with st.popover("📥 Exportar", use_container_width=True):
                if st.button("Generar CSV", use_container_width=True):
                    with st.spinner("Procesando y formateando datos..."):
                        df_export = conn.execute(query_base).df()
                        
                        columnas_financieras = [
                            'total_cuota_moderadora', 'total_copago', 'valor_neto', 'valor_factura', 
                            'valor_contrato', 'total_servicios', 'total_glosas', 'valor_aceptado_ips_1', 
                            'saldo_ips_1', 'valor_aceptado_eps_1', 'saldo_eps_1', 'valor_aceptado_ips_2', 
                            'saldo_ips_2', 'valor_aceptado_eps_2', 'saldo_eps_2', 'valor_aceptado_ips_gerencial', 
                            'valor_aceptado_eps_gerencial', 'valor_total_acepta_eps', 'valor_total_acepta_ips',
                            'PENDIENTE_CONCILIAR'
                        ]
                        
                        # Destrucción manual y forzosa del punto y el cero
                        for col in df_export.columns:
                            if col in columnas_financieras:
                                # Convertimos a número para rellenar vacíos, luego a texto y CORTAMOS en el punto
                                df_export[col] = pd.to_numeric(df_export[col], errors='coerce').fillna(0)
                                df_export[col] = df_export[col].astype(str).apply(lambda x: x.split('.')[0])
                            else:
                                # Para las columnas de texto, aplicamos limpieza agresiva de '.0' o 'nan'
                                df_export[col] = df_export[col].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
                                
                        df_export.to_csv('export_temporal.csv', index=False, sep=';', encoding='utf-8-sig')
                        st.session_state['csv_listo'] = True
                        
                if st.session_state.get('csv_listo'):
                    if os.path.exists('export_temporal.csv'):
                        with open('export_temporal.csv', 'rb') as f:
                            st.download_button("⬇️ Descargar", data=f, file_name="exportacion_eps.csv", mime="text/csv", type="primary", use_container_width=True)

        query_kpis = f"SELECT COUNT(*) as cuentas_totales, SUM(PENDIENTE_CONCILIAR) as suma_pendiente, SUM(total_glosas) as suma_glosas FROM ({query_base}) AS subconsulta"
        df_kpis = conn.execute(query_kpis).df().fillna(0)
        
        val_cuentas = f"{int(df_kpis['cuentas_totales'][0]):,}".replace(',', '.')
        val_pendiente = f"$ {float(df_kpis['suma_pendiente'][0]):,.0f}".replace(',', '.')
        val_glosas = f"$ {float(df_kpis['suma_glosas'][0]):,.0f}".replace(',', '.')

        # 🎯 Consulta para el Visor Dinámico del Prestador (Blindado para Vistas)
        try:
            # Extraemos los filtros actuales sin depender de las columnas visibles
            condiciones_filtros = query_base.split("WHERE 1=1")[1]
            
            # Blindamos la búsqueda por si el archivo no trae municipio o departamento
            cols_visor = ['razon_social', 'nit']
            if 'municipio' in columnas_db: cols_visor.append('municipio')
            if 'departamento' in columnas_db: cols_visor.append('departamento')
            
            query_visor = f"SELECT DISTINCT {', '.join(cols_visor)} FROM facturas WHERE 1=1 {condiciones_filtros} AND razon_social IS NOT NULL AND razon_social != '' LIMIT 2"
            df_visor = conn.execute(query_visor).df()
        except Exception:
            df_visor = pd.DataFrame(columns=['razon_social', 'nit'])
        
        with header_container:
            col_tit, col_indicadores, col_btn_limpiar, col_btn_vaciar, col_btn_apagar = st.columns([3, 5.5, 0.5, 0.5, 0.5])
            
            with col_tit:
                # Si los filtros aislaron a un solo prestador, mostramos el Visor Dinámico
                if len(df_visor) == 1:
                    p_nombre = str(df_visor['razon_social'].iloc[0]).upper()
                    p_nit = str(df_visor['nit'].iloc[0])
                    
                    # Extraemos y formateamos la ubicación de manera sutil (Blanco, mismo tamaño, sin emoji)
                    p_ubi = ""
                    m_val = str(df_visor['municipio'].iloc[0]).title() if 'municipio' in df_visor.columns and pd.notna(df_visor['municipio'].iloc[0]) and str(df_visor['municipio'].iloc[0]).strip() not in ['', 'nan', 'None'] else ""
                    d_val = str(df_visor['departamento'].iloc[0]).title() if 'departamento' in df_visor.columns and pd.notna(df_visor['departamento'].iloc[0]) and str(df_visor['departamento'].iloc[0]).strip() not in ['', 'nan', 'None'] else ""
                    
                    if m_val and d_val:
                        p_ubi = f"<span style='color: #ffffff; font-size: 0.85rem; font-weight: 500; margin-left: 12px; border-left: 1px solid #334155; padding-left: 12px;'>{m_val}, {d_val}</span>"
                    elif m_val:
                        p_ubi = f"<span style='color: #ffffff; font-size: 0.85rem; font-weight: 500; margin-left: 12px; border-left: 1px solid #334155; padding-left: 12px;'>{m_val}</span>"
                    elif d_val:
                        p_ubi = f"<span style='color: #ffffff; font-size: 0.85rem; font-weight: 500; margin-left: 12px; border-left: 1px solid #334155; padding-left: 12px;'>{d_val}</span>"

                    st.markdown(f"""
                        <div style='background: rgba(15, 23, 42, 0.4); border-left: 4px solid #38bdf8; padding: 10px 15px; border-radius: 6px; margin-top: 15px;'>
                            <h3 style='margin: 0; color: #f8fafc; font-size: 1.1rem; font-weight: 800; line-height: 1.2; word-wrap: break-word;'>🏥 {p_nombre}</h3>
                            <p style='margin: 0; color: #38bdf8; font-size: 0.85rem; font-weight: 600; letter-spacing: 0.5px; margin-top: 4px; display: flex; align-items: center;'>
                                NIT: {p_nit} {p_ubi}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    # Si hay varios o no hay filtros, mostramos el título por defecto
                    st.title("Base de Datos")
                
            with col_indicadores:
                html_kpis = f"""
                <div style="display: flex; justify-content: flex-end; align-items: center; padding-top: 1.55rem; gap: 8px;">
                    <span style="background-color: rgba(248,250,252,0.05); border: 1px solid rgba(226,232,240,0.2); color: #f8fafc; padding: 0 15px; border-radius: 8px; height: 40px; display: inline-flex; align-items: center; font-family: 'Inter', sans-serif; font-size: 0.95rem; box-sizing: border-box; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"><b>{val_cuentas}</b>&nbsp;Facturas</span>
                    <span style="background-color: rgba(240,253,244,0.05); border: 1px solid rgba(187,247,208,0.2); color: #4ade80; padding: 0 15px; border-radius: 8px; height: 40px; display: inline-flex; align-items: center; font-family: 'Inter', sans-serif; font-size: 0.95rem; box-sizing: border-box; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">Pendiente por Conciliar:&nbsp;<b>{val_pendiente}</b></span>
                    <span style="background-color: rgba(254,242,242,0.05); border: 1px solid rgba(254,202,202,0.2); color: #f87171; padding: 0 15px; border-radius: 8px; height: 40px; display: inline-flex; align-items: center; font-family: 'Inter', sans-serif; font-size: 0.95rem; box-sizing: border-box; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">Total Glosado:&nbsp;<b>{val_glosas}</b></span>
                </div>
                """
                st.markdown(html_kpis, unsafe_allow_html=True)
                
            with col_btn_limpiar:
                st.markdown("<div style='height: 1.55rem;'></div>", unsafe_allow_html=True)
                if st.button("🧹", help="Limpiar todos los filtros y búsquedas", use_container_width=True):
                    for key in list(st.session_state.keys()):
                        if key.startswith(('memoria_', 'frap_')):
                            del st.session_state[key]
                    st.rerun()
                
            with col_btn_vaciar:
                st.markdown("<div style='height: 1.55rem;'></div>", unsafe_allow_html=True)
                with st.popover("🗑️", help="Vaciar Base de Datos", use_container_width=True):
                    try:
                        tablas = conn.execute("SHOW TABLES").df()
                        if not tablas.empty and 'facturas' in tablas['name'].values:
                            anios_db = conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()
                            anios_lista = sorted([str(a) for a in anios_db['anio'].dropna().tolist() if a != ''], reverse=True)
                            
                            st.markdown("🗑️ **Borrar Registros**")
                            borrar_todo = st.checkbox("Borrar TODA la base de datos")
                            anios_a_borrar = []
                            
                            if not borrar_todo and anios_lista:
                                anios_a_borrar = st.multiselect("Borrar por Año(s):", anios_lista)
                            
                            if st.button("Confirmar Borrado", type="primary", use_container_width=True):
                                if borrar_todo:
                                    conn.execute("DELETE FROM facturas")
                                    st.toast("Base de datos vaciada por completo.", icon="✅")
                                elif anios_a_borrar:
                                    condiciones = " OR ".join([f"fecha_radicado LIKE '%{anio}%'" for anio in anios_a_borrar])
                                    conn.execute(f"DELETE FROM facturas WHERE {condiciones}")
                                    st.toast(f"Registros de {', '.join(anios_a_borrar)} eliminados.", icon="✅")
                                
                                if borrar_todo or anios_a_borrar:
                                    time.sleep(1)
                                    st.rerun()
                    except Exception as e:
                        st.error(f"Error al limpiar: {e}")
                        
            with col_btn_apagar:
                st.markdown("<div style='height: 1.55rem;'></div>", unsafe_allow_html=True)
                if st.button("🛑", help="Apagar Servidor Local", use_container_width=True):
                    try:
                        conn.close() 
                    except:
                        pass
                    os._exit(0)

        query_pantalla = query_base + (" LIMIT 5000" if (termino_busqueda or filtros_sql or filtro_vf != "Todos los Estados") else " LIMIT 1000")
        t_inicio_query = time.time()
        df_resultados = conn.execute(query_pantalla).df()
        t_fin_query = time.time()
        
        ms_query = int((t_fin_query - t_inicio_query) * 1000)
        
        if ms_query >= 0:
            uid = int(time.time() * 1000) 
            html_popup = f"""
            <style>
            @keyframes slideFade_{uid} {{
                0% {{ bottom: -50px; opacity: 0; }}
                10% {{ bottom: 25px; opacity: 1; }}
                80% {{ bottom: 25px; opacity: 1; }}
                100% {{ bottom: 25px; opacity: 0; visibility: hidden; }}
            }}
            .speed-popup-{uid} {{
                position: fixed; bottom: -50px; right: 25px; background: rgba(15, 23, 42, 0.95);
                backdrop-filter: blur(10px); border-left: 4px solid #38bdf8; color: #f8fafc;
                padding: 12px 20px; border-radius: 8px; font-family: 'Inter', sans-serif;
                font-size: 0.9rem; z-index: 9999999; box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                pointer-events: none; animation: slideFade_{uid} 2.5s ease-in-out forwards;
            }}
            </style>
            <div class="speed-popup-{uid}">🏎️ Consulta ejecutada en <b>{ms_query} ms</b></div>
            """
            st.markdown(html_popup, unsafe_allow_html=True)

        columnas_para_formato = [
            'total_cuota_moderadora', 'total_copago', 'valor_neto', 'valor_factura', 
            'valor_contrato', 'total_servicios', 'total_glosas', 'valor_aceptado_ips_1', 
            'saldo_ips_1', 'valor_aceptado_eps_1', 'saldo_eps_1', 'valor_aceptado_ips_2', 
            'saldo_ips_2', 'valor_aceptado_eps_2', 'saldo_eps_2', 'valor_aceptado_ips_gerencial', 
            'valor_aceptado_eps_gerencial', 'valor_total_acepta_eps', 'valor_total_acepta_ips',
            'PENDIENTE_CONCILIAR'
        ]
        
        if not df_resultados.empty:
            for col in df_resultados.columns:
                if col not in columnas_para_formato:
                    df_resultados[col] = df_resultados[col].astype(str).replace('nan', '')

            for col in columnas_para_formato:
                if col in df_resultados.columns:
                    df_resultados[col] = pd.to_numeric(df_resultados[col], errors='coerce').fillna(0).astype('int64')
                    df_resultados[col] = df_resultados[col].apply(lambda x: f"$ {x:,.0f}".replace(',', '.'))
            
            if not st.session_state.macro_activa:
                df_resultados.insert(0, '#', range(1, len(df_resultados) + 1))
                
        # 6. Lógica del Radar de Fechas y Totales (Integrado)
        hay_filtro_activo = (tipo_busq in ["🏢 Razón Social", "🆔 NIT", "🧾 Factura", "📦 Radicado"]) and (termino_busqueda and str(termino_busqueda).strip() != "")

        if hay_filtro_activo:
            try:
                # 1. Traemos la info de fechas, facturas, contratos, pendiente Y numero_contrato
                col_fecha_rips = ", fecha_servicio_inicio_rips" if (st.session_state.macro_activa == "Capitado" and 'fecha_servicio_inicio_rips' in columnas_db) else ""
                query_radar = f"SELECT fecha_radicado, valor_factura, tipo_contrato, PENDIENTE_CONCILIAR, numero_contrato{col_fecha_rips} FROM ({query_base}) AS subconsulta"
                df_radar = conn.execute(query_radar).df()
                
                if not df_radar.empty:
                    # 2. Cálculos de Valor Factura 
                    total_factura = pd.to_numeric(df_radar['valor_factura'], errors='coerce').fillna(0).sum() if 'valor_factura' in df_radar.columns else 0
                    total_factura_str = f"$ {total_factura:,.0f}".replace(',', '.')
                    
                    # 3. Cálculo Dinámico: Pendiente por Contrato (AHORA EN PILLS HORIZONTALES)
                    html_contratos_radar = ""
                    if 'tipo_contrato' in df_radar.columns and 'PENDIENTE_CONCILIAR' in df_radar.columns:
                        df_radar['tipo_contrato'] = df_radar['tipo_contrato'].fillna('SIN ESPECIFICAR').replace('', 'SIN ESPECIFICAR')
                        df_radar['PENDIENTE_CONCILIAR'] = pd.to_numeric(df_radar['PENDIENTE_CONCILIAR'], errors='coerce').fillna(0)
                        
                        agrupado_contratos = df_radar.groupby('tipo_contrato')['PENDIENTE_CONCILIAR'].sum().reset_index()
                        agrupado_contratos = agrupado_contratos.sort_values(by='PENDIENTE_CONCILIAR', ascending=False)
                        
                        # Usamos flex-wrap para que se acomoden horizontalmente
                        html_contratos_radar = "<div style='display: flex; flex-wrap: wrap; gap: 10px;'>"
                        for _, row in agrupado_contratos.iterrows():
                            c_nom = str(row['tipo_contrato'])
                            c_val = f"$ {float(row['PENDIENTE_CONCILIAR']):,.0f}".replace(',', '.')
                            html_contratos_radar += f"<span style='background-color: rgba(244, 114, 182, 0.1); border: 1px solid rgba(244, 114, 182, 0.4); color: #f472b6; padding: 4px 12px; border-radius: 15px; font-size: 0.85rem; display: inline-flex; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);'><b style='color: #e2e8f0; margin-right: 6px;'>{c_nom}:</b> {c_val}</span>"
                        html_contratos_radar += "</div>"
                    else:
                        html_contratos_radar = "<span style='color: #94a3b8; font-size: 0.85rem;'>Sin datos de contrato</span>"

                    # 4. Extracción de Números de Contrato (NUEVO BLOQUE DE PILLS)
                    html_numeros_contrato = ""
                    if 'numero_contrato' in df_radar.columns and 'PENDIENTE_CONCILIAR' in df_radar.columns:
                        
                        # Agrupamos por número de contrato y sumamos el pendiente
                        agrupado_nums = df_radar.groupby('numero_contrato')['PENDIENTE_CONCILIAR'].sum().reset_index()
                        agrupado_nums = agrupado_nums.sort_values(by='PENDIENTE_CONCILIAR', ascending=False)
                        
                        # Filtramos nulos o vacíos
                        agrupado_nums = agrupado_nums[~agrupado_nums['numero_contrato'].astype(str).str.strip().isin(['', 'nan', 'None', 'SIN_DATO'])]
                        
                        if not agrupado_nums.empty:
                            html_numeros_contrato = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
                            for _, row in agrupado_nums.iterrows():
                                n_nom = str(row['numero_contrato']).strip()
                                n_val = f"$ {float(row['PENDIENTE_CONCILIAR']):,.0f}".replace(',', '.')
                                html_numeros_contrato += f"<span style='background-color: rgba(167, 139, 250, 0.1); border: 1px solid rgba(167, 139, 250, 0.4); color: #c084fc; padding: 4px 12px; border-radius: 15px; font-size: 0.85rem; display: inline-flex; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);'>📄 <b style='color: #e2e8f0; margin-right: 6px;'>{n_nom}:</b> {n_val}</span>"
                            html_numeros_contrato += "</div>"
                        else:
                            html_numeros_contrato = "<span style='color: #94a3b8; font-size: 0.85rem;'>Sin números detectados</span>"
                    else:
                        html_numeros_contrato = "<span style='color: #94a3b8; font-size: 0.85rem;'>Columna no encontrada</span>"

                    # 5. Lógica de Fechas (Radar original)
                    fechas_validas = pd.to_datetime(df_radar['fecha_radicado'], format='%d/%m/%Y', errors='coerce').dropna()
                    html_tags = ""
                    
                    if not fechas_validas.empty:
                        hoy = pd.Timestamp.now().normalize()
                        fechas_reales = fechas_validas[fechas_validas <= hoy]
                        
                        if not fechas_reales.empty:
                            resumen_fechas = fechas_reales.groupby(fechas_reales.dt.year).apply(lambda x: sorted(list(set(x.dt.month)))).to_dict()
                            meses_map = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
                            
                            for anio in sorted(resumen_fechas.keys()):
                                meses_num = resumen_fechas[anio]
                                nombres_meses = ", ".join([meses_map[m] for m in meses_num])
                                html_tags += f"<span style='background-color: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; padding: 4px 12px; border-radius: 15px; margin-right: 10px; font-size: 0.85rem; display: inline-block; margin-top: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);'><b>{int(anio)}:</b> {nombres_meses}</span>"
                    
                    if html_tags == "":
                        html_tags = "<span style='color: #94a3b8; font-size: 0.85rem; margin-top: 5px; display: block;'>Periodos no detectables</span>"

                    # --- NUEVO: 5.5 Lógica de Fechas de Servicio (SOLO CAPITADO Y CON CONTRATO SELECCIONADO) ---
                    html_tags_rips = ""
                    contratos_seleccionados = st.session_state.get('frap_numero_contrato', [])
                    
                    if st.session_state.macro_activa == "Capitado" and contratos_seleccionados and 'fecha_servicio_inicio_rips' in df_radar.columns:
                        fechas_rips_validas = pd.to_datetime(df_radar['fecha_servicio_inicio_rips'], format='%d/%m/%Y', errors='coerce').dropna()
                        if not fechas_rips_validas.empty:
                            hoy = pd.Timestamp.now().normalize()
                            fechas_rips_reales = fechas_rips_validas[fechas_rips_validas <= hoy]
                            
                            if not fechas_rips_reales.empty:
                                resumen_fechas_rips = fechas_rips_reales.groupby(fechas_rips_reales.dt.year).apply(lambda x: sorted(list(set(x.dt.month)))).to_dict()
                                for anio in sorted(resumen_fechas_rips.keys()):
                                    meses_num = resumen_fechas_rips[anio]
                                    nombres_meses = ", ".join([meses_map[m] for m in meses_num])
                                    html_tags_rips += f"<span style='background-color: rgba(167, 139, 250, 0.1); border: 1px solid rgba(167, 139, 250, 0.4); color: #c084fc; padding: 4px 12px; border-radius: 15px; margin-right: 10px; font-size: 0.85rem; display: inline-block; margin-top: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);'><b>{int(anio)}:</b> {nombres_meses}</span>"
                        
                        if html_tags_rips == "":
                            html_tags_rips = "<span style='color: #94a3b8; font-size: 0.85rem; margin-top: 5px; display: block;'>Periodos de servicio no detectables</span>"

                    # 6. Renderizado UI Integrado (Reorganizado en 2 filas para aprovechar espacio)
                    bloque_servicios = ""
                    if html_tags_rips:
                        bloque_servicios = f"<div style='flex-grow: 1;'><div style='color: #94a3b8; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;'>🏥 Meses de Servicio (Capitado):</div><div style='display: flex; flex-wrap: wrap;'>{html_tags_rips}</div></div>"
                    
                    html_final_radar = f"""<div style='background: rgba(30, 41, 59, 0.4); border-left: 4px solid #38bdf8; padding: 15px; border-radius: 6px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
<div style='display: flex; gap: 20px; align-items: flex-start;'>
<div style='min-width: 25%;'>
<div style='color: #94a3b8; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 4px;'>💰 Total Facturado:</div>
<div style='color: #4ade80; font-size: 1.3rem; font-weight: 800;'>{total_factura_str}</div>
</div>
<div style='flex-grow: 1;'>
<div style='color: #94a3b8; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;'>⏱️ Meses de radicación:</div>
<div style='display: flex; flex-wrap: wrap;'>{html_tags}</div>
</div>
{bloque_servicios}
</div>
<div style='border-top: 1px solid rgba(255,255,255,0.05); margin: 0;'></div>
<div style='display: flex; gap: 20px; align-items: flex-start;'>
<div style='width: 50%; border-right: 1px solid rgba(255,255,255,0.05); padding-right: 15px;'>
<div style='color: #94a3b8; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 10px;'>📋 Pendiente por Conciliar:</div>
{html_contratos_radar}
</div>
<div style='width: 50%; padding-left: 5px;'>
<div style='color: #94a3b8; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 10px;'>🔢 Números de Contrato:</div>
{html_numeros_contrato}
</div>
</div>
</div>"""
                    st.markdown(html_final_radar, unsafe_allow_html=True)
            except Exception as e:
                pass
            
        st.dataframe(df_resultados, use_container_width=True, hide_index=True, height=600)
    
    # =========================================================================
    # PANTALLA 2: KPIs
    # =========================================================================
    elif st.session_state.modulo_activo == "KPIs":
        st.title("KPIs de Auditoría")
        
        # 1. Parámetros de tiempo dinámicos
        try:
            anios_ext = conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()
            lista_anios = sorted([str(a) for a in anios_ext['anio'].dropna().tolist() if a != ''])
        except:
            lista_anios = ["2024", "2025", "2026"] 
            
        lista_meses = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

        # 2. FILTROS HORIZONTALES
        col_fil_rs, col_fil_anio, col_fil_mes = st.columns([2, 1, 1])
        
        with col_fil_rs:
            rs_disponibles = conn.execute("SELECT DISTINCT razon_social FROM facturas WHERE razon_social IS NOT NULL").df()['razon_social'].astype(str).tolist()
            kpi_rs = st.selectbox("Razón Social:", sorted(rs_disponibles), index=None, placeholder="Todas las IPS")

        with col_fil_anio:
            kpi_anios_sel = st.multiselect("Años:", lista_anios, placeholder="Todos")

        with col_fil_mes:
            kpi_meses_sel = st.multiselect("Meses:", lista_meses, placeholder="Todos")

        # Construcción de la base del filtro SQL
        filtro_global_kpi = " WHERE 1=1 "
        if kpi_rs: 
            filtro_global_kpi += f" AND razon_social = '{kpi_rs.replace("'", "''")}'"
        if kpi_anios_sel:
            cond_a = " OR ".join([f"fecha_radicado LIKE '%{a}%'" for a in kpi_anios_sel])
            filtro_global_kpi += f" AND ({cond_a})"
        if kpi_meses_sel:
            filtro_global_kpi += f" AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({','.join(kpi_meses_sel)})"
        
        # 3. CONFIGURACIÓN DE INDICADORES AUTOMÁTICOS
        opciones_kpi = [
            "Facturas por Mes (Barras)",
            "Relación Glosa vs Servicios (%)",
            "Aceptación Glosa EPS vs IPS",
            "Estado y Glosa por Auditor",
            "Oportunidad de Notificación (Días)"
        ]
        
        kpis_seleccionados = st.multiselect(
            "Visualizar indicadores:",
            options=opciones_kpi,
            default=opciones_kpi, 
            placeholder="Seleccionar..."
        )
        st.write("---")

        if kpis_seleccionados:
            c1, c2 = st.columns(2)
            cols_disp = [c1, c2]
            idx_col = 0 

            # --- KPI 1: Facturas por Mes (Con Línea de Tendencia) ---
            if "Facturas por Mes (Barras)" in kpis_seleccionados:
                with cols_disp[idx_col % 2]:
                    with st.container(border=True):
                        st.markdown("#### Facturas por Mes")
                        df_meses = conn.execute(f"""
                            SELECT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes, COUNT(*) as Cantidad 
                            FROM facturas {filtro_global_kpi} GROUP BY num_mes HAVING num_mes IS NOT NULL ORDER BY num_mes
                        """).df()
                        
                        if not df_meses.empty:
                            meses_map = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
                            df_meses['Mes'] = df_meses['num_mes'].map(meses_map)
                            
                            base_meses = alt.Chart(df_meses).encode(
                                x=alt.X('Mes:N', sort=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'], title="")
                            )
                            barras = base_meses.mark_bar(color="#93c5fd", opacity=0.8).encode(
                                y=alt.Y('Cantidad:Q', title="Facturas"),
                                tooltip=[alt.Tooltip('Mes:N'), alt.Tooltip('Cantidad:Q', format=',.0f', title="Total")]
                            )
                            linea = base_meses.mark_line(color="#ef4444", strokeWidth=3, point=alt.OverlayMarkDef(color="#b91c1c", size=70)).encode(
                                y=alt.Y('Cantidad:Q')
                            )
                            
                            st.altair_chart((barras + linea).interactive(), use_container_width=True)
                        else: st.info("Sin datos.")
                idx_col += 1

            # --- KPI 2: Relación Glosa vs Servicios (CORREGIDO) ---
            if "Relación Glosa vs Servicios (%)" in kpis_seleccionados:
                with cols_disp[idx_col % 2]:
                    with st.container(border=True):
                        st.markdown("#### Glosa vs Servicios")
                        df_rel = conn.execute(f"""
                            SELECT 
                                SUM(TRY_CAST(total_servicios AS DOUBLE)) as t_serv, 
                                SUM(TRY_CAST(total_glosas AS DOUBLE)) as t_glosa,
                                COUNT(CASE WHEN TRY_CAST(total_glosas AS DOUBLE) > 0 THEN 1 END) as facturas_con_glosa
                            FROM facturas {filtro_global_kpi}
                        """).df()
                        
                        if not df_rel.empty and df_rel['t_serv'][0] is not None:
                            t_serv = df_rel['t_serv'][0] or 0
                            t_glosa = df_rel['t_glosa'][0] or 0
                            f_con_glosa = df_rel['facturas_con_glosa'][0] or 0
                            
                            df_plot = pd.DataFrame({
                                "Concepto": ["Glosado", "Aprobado"],
                                "Monto": [t_glosa, t_serv - t_glosa],
                                "Total Facturas": [f_con_glosa, "N/A"]
                            })
                            df_plot['Porcentaje'] = df_plot['Monto'] / df_plot['Monto'].sum()
                            
                            # 🎯 CORRECCIÓN: stack=True obliga a Altair a calcular la posición del arco para el texto
                            base_rel = alt.Chart(df_plot).encode(
                                theta=alt.Theta(field="Monto", type="quantitative", stack=True),
                                color=alt.Color(field="Concepto", type="nominal", scale=alt.Scale(range=["#f87171", "#34d399"]))
                            )
                            
                            dona_rel = base_rel.mark_arc(innerRadius=50, outerRadius=90).encode(
                                tooltip=[
                                    alt.Tooltip("Concepto:N"), 
                                    alt.Tooltip("Monto:Q", format="$,.0f", title="Monto"), 
                                    alt.Tooltip("Porcentaje:Q", format=".1%", title="Proporción"),
                                    alt.Tooltip("Total Facturas:N", title="Facturas Glosadas") 
                                ]
                            )
                            
                            # 🎯 CORRECCIÓN: radius=110 empuja el texto fuera de la dona para evitar solapamientos sucios
                            texto_rel = base_rel.mark_text(radius=115, size=12, fontWeight="bold", fill="#f8fafc").encode(
                                text=alt.Text('Porcentaje:Q', format='.1%')
                            )
                            
                            st.altair_chart((dona_rel + texto_rel).interactive(), use_container_width=True)
                        else: st.info("Sin datos.")
                idx_col += 1

            # --- KPI 3: Aceptación EPS vs IPS (CORREGIDO) ---
            if "Aceptación Glosa EPS vs IPS" in kpis_seleccionados:
                with cols_disp[idx_col % 2]:
                    with st.container(border=True):
                        st.markdown("#### Aceptación EPS vs IPS")
                        df_ac = conn.execute(f"""
                            SELECT SUM(TRY_CAST(valor_total_acepta_eps AS DOUBLE)) as v_eps, 
                                   SUM(TRY_CAST(valor_total_acepta_ips AS DOUBLE)) as v_ips 
                            FROM facturas {filtro_global_kpi}
                        """).df()
                        
                        if not df_ac.empty and (df_ac['v_eps'][0] is not None or df_ac['v_ips'][0] is not None):
                            v_eps = df_ac['v_eps'][0] or 0
                            v_ips = df_ac['v_ips'][0] or 0
                            
                            df_dona = pd.DataFrame({"Entidad": ["Acepta EPS", "Acepta IPS"], "Monto": [v_eps, v_ips]})
                            total_ac = df_dona['Monto'].sum()
                            df_dona['Porcentaje'] = df_dona['Monto'] / total_ac if total_ac > 0 else 0
                            
                            base_ac = alt.Chart(df_dona).encode(
                                theta=alt.Theta("Monto:Q", stack=True),
                                color=alt.Color("Entidad:N", scale=alt.Scale(range=["#818cf8", "#f472b6"]))
                            )
                            
                            dona_ac = base_ac.mark_arc(innerRadius=50, outerRadius=90).encode(
                                tooltip=[
                                    alt.Tooltip("Entidad:N"), 
                                    alt.Tooltip("Monto:Q", format="$,.0f", title="Valor Aceptado"),
                                    alt.Tooltip("Porcentaje:Q", format=".1%", title="Proporción")
                                ]
                            )
                            
                            texto_ac = base_ac.mark_text(radius=115, size=12, fontWeight="bold", fill="#f8fafc").encode(
                                text=alt.Text('Porcentaje:Q', format='.1%')
                            )
                            
                            st.altair_chart((dona_ac + texto_ac).interactive(), use_container_width=True)
                        else: st.info("Sin datos.")
                idx_col += 1

            # --- KPI 4: Estado de Facturas por Auditor (CORREGIDO RENDERIZADO BARRAS) ---
            if "Estado y Glosa por Auditor" in kpis_seleccionados:
                with cols_disp[idx_col % 2]:
                    with st.container(border=True):
                        c_tit_aud, c_sel_aud = st.columns([6, 4])
                        with c_tit_aud: 
                            st.markdown("#### Estado de Facturas")
                        
                        auditores = ["Todos"] + sorted(conn.execute("SELECT DISTINCT usuario_auditoria_tecnica FROM facturas WHERE usuario_auditoria_tecnica IS NOT NULL").df()['usuario_auditoria_tecnica'].tolist())
                        with c_sel_aud:
                            aud_sel = st.selectbox("Auditor:", auditores, label_visibility="collapsed", key="auditor_kpi_selector")

                        f_aud = filtro_global_kpi
                        if aud_sel != "Todos": 
                            f_aud += f" AND usuario_auditoria_tecnica = '{aud_sel}'"

                        # 1. SQL Blindado: Agregamos COALESCE a la suma para evitar que valores NULL rompan la gráfica en Altair
                        df_aud = conn.execute(f"""
                            SELECT 
                                CASE 
                                    WHEN estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR LOWER(CAST(estado_tecnica AS VARCHAR)) = 'nan' 
                                    THEN 'Sin Estado' 
                                    ELSE CAST(estado_tecnica AS VARCHAR) 
                                END as estado_limpio,
                                COUNT(*) as Cantidad, 
                                COALESCE(SUM(TRY_CAST(total_glosas AS DOUBLE)), 0) as total_glosa
                            FROM facturas 
                            {f_aud} 
                            GROUP BY estado_limpio
                            ORDER BY Cantidad DESC
                        """).df()

                        if not df_aud.empty:
                            total_facturas_auditor = int(df_aud['Cantidad'].sum())
                            val_total_fmt = f"{total_facturas_auditor:,}".replace(',', '.')
                            
                            st.markdown(f"""
                                <div style="margin-bottom: 15px; display: flex; align-items: center; gap: 8px;">
                                    <span style="background-color: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; padding: 2px 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 700;">
                                        Total General: {val_total_fmt} Facturas
                                    </span>
                                </div>
                            """, unsafe_allow_html=True)

                            # 2. Gráfico con sintaxis de compatibilidad máxima
                            base_aud = alt.Chart(df_aud).encode(
                                y=alt.Y('estado_limpio:N', sort=alt.EncodingSortField(field='Cantidad', order='descending'), title=""),
                                x=alt.X('Cantidad:Q', title="Cantidad", axis=alt.Axis(format=",")),
                                tooltip=[
                                    alt.Tooltip('estado_limpio:N', title="Estado"),
                                    alt.Tooltip('Cantidad:Q', format=',.0f', title="Facturas"),
                                    alt.Tooltip('total_glosa:Q', format="$,.0f", title="Monto Glosado")
                                ]
                            )
                            
                            # Removido el cornerRadiusEnd para evitar conflictos de versión
                            barras_aud = base_aud.mark_bar(color="#fbbf24", opacity=0.85)
                            
                            texto_aud = base_aud.mark_text(align='left', baseline='middle', dx=5, fontWeight='bold', color="#f8fafc").encode(
                                text=alt.Text('Cantidad:Q', format=',.0f')
                            )
                            
                            st.altair_chart((barras_aud + texto_aud).interactive(), use_container_width=True)
                        else: 
                            st.info("Sin registros.")
                idx_col += 1

                # --- KPI 5: Oportunidad de Notificación ---
            if "Oportunidad de Notificación (Días)" in kpis_seleccionados:
                with cols_disp[idx_col % 2]:
                    with st.container(border=True):
                        st.markdown("#### Oportunidad de Notificación")
                        
                        # Query blindado: Calcula días reales ignorando errores de fechas cruzadas
                        query_oportunidad = f"""
                            SELECT 
                                COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                                AVG(DATE_DIFF('day', 
                                    COALESCE(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y'), TRY_CAST(fecha_radicado AS DATE)), 
                                    COALESCE(TRY_STRPTIME(fecha_notificado, '%d/%m/%Y'), TRY_CAST(fecha_notificado AS DATE))
                                )) as promedio_dias
                            FROM facturas 
                            {filtro_global_kpi}
                              AND fecha_notificado IS NOT NULL AND TRIM(CAST(fecha_notificado AS VARCHAR)) != ''
                              AND fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''
                              AND COALESCE(TRY_STRPTIME(fecha_notificado, '%d/%m/%Y'), TRY_CAST(fecha_notificado AS DATE)) >= COALESCE(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y'), TRY_CAST(fecha_radicado AS DATE))
                            GROUP BY num_mes
                            HAVING num_mes IS NOT NULL
                            ORDER BY num_mes
                        """
                        
                        df_op = conn.execute(query_oportunidad).df()
                        
                        if not df_op.empty:
                            meses_map = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
                            df_op['Mes'] = df_op['num_mes'].map(meses_map)
                            df_op['promedio_dias'] = df_op['promedio_dias'].round(1)
                            
                            base_op = alt.Chart(df_op).encode(
                                x=alt.X('Mes:N', sort=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'], title="")
                            )
                            
                            # Línea de tendencia (Morada)
                            linea_op = base_op.mark_line(color="#a855f7", strokeWidth=3).encode(
                                y=alt.Y('promedio_dias:Q', title="Promedio en Días", scale=alt.Scale(zero=False)),
                                tooltip=[
                                    alt.Tooltip('Mes:N', title="Mes"), 
                                    alt.Tooltip('promedio_dias:Q', title="Días Promedio")
                                ]
                            )
                            
                            # Puntos interactivos
                            puntos_op = base_op.mark_circle(color="#9333ea", size=80).encode(
                                y=alt.Y('promedio_dias:Q')
                            )
                            
                            # Texto exacto de días sobre cada punto
                            texto_op = base_op.mark_text(align='center', baseline='bottom', dy=-10, fontWeight='bold', color="#f8fafc").encode(
                                y=alt.Y('promedio_dias:Q'),
                                text=alt.Text('promedio_dias:Q', format='.1f')
                            )
                            
                            st.altair_chart((linea_op + puntos_op + texto_op).interactive(), use_container_width=True)
                        else: 
                            st.info("Datos insuficientes o fechas inválidas para calcular oportunidad.")
                idx_col += 1

    # =========================================================================
    # PANTALLA 3: TABLAS DINÁMICAS 
    # =========================================================================
    elif st.session_state.modulo_activo == "Dinámica":
        header_container_din = st.container()
        
        # 1. Extracción dinámica de datos para los filtros
        try:
            anios_ext = conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()
            lista_anios_din = sorted([str(a) for a in anios_ext['anio'].dropna().tolist() if a != ''])
        except:
            lista_anios_din = ["2024", "2025", "2026"] 
        
        lista_meses_din = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
        
        try:
            if 'tipo_contrato' in columnas_db:
                contratos_ext = conn.execute("SELECT DISTINCT tipo_contrato FROM facturas WHERE tipo_contrato IS NOT NULL AND tipo_contrato != ''").df()
                lista_contratos_din = sorted(contratos_ext['tipo_contrato'].astype(str).tolist())
            else:
                lista_contratos_din = []
        except:
            lista_contratos_din = []

        try:
            if 'departamento' in columnas_db:
                deptos_ext = conn.execute("SELECT DISTINCT departamento FROM facturas WHERE departamento IS NOT NULL AND departamento != ''").df()
                lista_deptos_din = sorted(deptos_ext['departamento'].astype(str).tolist())
            else:
                lista_deptos_din = []
        except:
            lista_deptos_din = []

        # 2. Renderizado de la fila de filtros
        st.write("") 
        
        col_vista, col_d1, col_d2, col_d_depto, col_d3, col_d4, col_btn_exportar = st.columns([1.3, 0.9, 1.2, 1.2, 1.1, 0.8, 1.0])
        
        with col_vista:
            tipo_vista = st.selectbox("Nivel de Análisis:", ["🏥 Prestador", "🗺️ Departamento", "📄 Contratos", "💼 Cartera"])
            
        with col_d1:
            filtro_vf_dinamica = st.selectbox("Estado:", ["Todos", "VERDADERO", "FALSO"])
        with col_d2:
            filtros_contrato_din = st.multiselect("Contratos:", lista_contratos_din, placeholder="Todos...")
        with col_d_depto:
            filtros_depto_din = st.multiselect("Departamentos:", lista_deptos_din, placeholder="Todos...")
        with col_d3:
            ordenar_por = st.selectbox("Ordenar:", ["Mayor a menor", "Menor a mayor", "A a Z", "Z a A"])
        with col_d4:
            st.markdown("<div style='font-size: 14px; margin-bottom: 6px; color: #f8fafc;'>Periodo:</div>", unsafe_allow_html=True)
            with st.popover("📅", use_container_width=True):
                anios_sel = st.multiselect("Años", lista_anios_din, placeholder="Años...", key="multi_a_din")
                meses_sel = st.multiselect("Meses", lista_meses_din, placeholder="Meses...", key="multi_m_din")

        # 3. Construcción de la consulta SQL dinámica BLINDADA
        if tipo_vista == "🗺️ Departamento":
            query_dinamica = """
                SELECT 
                    CASE WHEN departamento IS NULL OR TRIM(departamento) = '' THEN 'SIN DEPARTAMENTO' ELSE departamento END as "Departamento",
                    SUM(PENDIENTE_CONCILIAR) as "Pendiente por Conciliar"
                FROM facturas 
                WHERE 1=1
            """
        elif tipo_vista == "📄 Contratos":
            query_dinamica = """
                SELECT 
                    CASE WHEN nit IS NULL OR TRIM(CAST(nit AS VARCHAR)) = '' THEN 'SIN NIT' ELSE CAST(nit AS VARCHAR) END as "NIT",
                    CASE WHEN razon_social IS NULL OR TRIM(CAST(razon_social AS VARCHAR)) = '' THEN 'SIN PRESTADOR' ELSE CAST(razon_social AS VARCHAR) END as "Razón Social",
                    CASE WHEN departamento IS NULL OR TRIM(CAST(departamento AS VARCHAR)) = '' THEN 'SIN DEPARTAMENTO' ELSE CAST(departamento AS VARCHAR) END as "Departamento",
                    CASE WHEN numero_contrato IS NULL OR TRIM(CAST(numero_contrato AS VARCHAR)) = '' THEN 'SIN NUMERO' ELSE CAST(numero_contrato AS VARCHAR) END as "Número de Contrato",
                    CASE WHEN tipo_contrato IS NULL OR TRIM(CAST(tipo_contrato AS VARCHAR)) = '' THEN 'SIN TIPO' ELSE CAST(tipo_contrato AS VARCHAR) END as "Tipo de Contrato",
                    SUM(PENDIENTE_CONCILIAR) as "Pendiente por Conciliar"
                FROM facturas 
                WHERE 1=1
            """
        elif tipo_vista == "💼 Cartera":
            # 🎯 CORRECCIÓN: SUM() del valor de la factura en los estados de auditoría en lugar de COUNT()
            query_dinamica = """
                SELECT 
                    CASE WHEN nit IS NULL OR TRIM(CAST(nit AS VARCHAR)) = '' THEN 'SIN NIT' ELSE CAST(nit AS VARCHAR) END as "NIT",
                    CASE WHEN razon_social IS NULL OR TRIM(CAST(razon_social AS VARCHAR)) = '' THEN 'SIN PRESTADOR' ELSE CAST(razon_social AS VARCHAR) END as "Razón Social",
                    COUNT(factura) as "Número de Facturas",
                    SUM(TRY_CAST(valor_factura AS DOUBLE)) as "Total Facturado",
                    SUM(CASE WHEN UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'AUDITADO' THEN TRY_CAST(valor_factura AS DOUBLE) ELSE 0 END) as "Auditado",
                    SUM(CASE WHEN UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'CERRADO' THEN TRY_CAST(valor_factura AS DOUBLE) ELSE 0 END) as "Cerrado",
                    SUM(CASE WHEN UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NOTIFICADO' THEN TRY_CAST(valor_factura AS DOUBLE) ELSE 0 END) as "Notificado",
                    SUM(CASE WHEN UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'PENDIENTE' THEN TRY_CAST(valor_factura AS DOUBLE) ELSE 0 END) as "Pendiente",
                    SUM(TRY_CAST(total_glosas AS DOUBLE)) as "Total Glosado",
                    SUM(TRY_CAST(valor_total_acepta_ips AS DOUBLE)) as "Valor Acepta IPS",
                    SUM(TRY_CAST(valor_total_acepta_eps AS DOUBLE)) as "Valor Acepta EPS",
                    SUM(PENDIENTE_CONCILIAR) as "Pendiente por Conciliar"
                FROM facturas 
                WHERE 1=1
            """
        else:
            # Prestador
            query_dinamica = """
                SELECT 
                    CASE WHEN nit IS NULL OR TRIM(nit) = '' THEN 'SIN NIT' ELSE nit END as "NIT",
                    CASE WHEN razon_social IS NULL OR TRIM(razon_social) = '' THEN 'SIN PRESTADOR' ELSE razon_social END as "Razón Social",
                    CASE WHEN departamento IS NULL OR TRIM(departamento) = '' THEN 'SIN DEPARTAMENTO' ELSE departamento END as "Departamento",
                    SUM(PENDIENTE_CONCILIAR) as "Pendiente por Conciliar"
                FROM facturas 
                WHERE 1=1
            """
        
        if filtro_vf_dinamica != "Todos":
            query_dinamica += f" AND \"V_F\" = '{filtro_vf_dinamica}'"
            
        if filtros_contrato_din:
            contratos_limpios = [c.replace("'", "''") for c in filtros_contrato_din]
            in_clause = ", ".join([f"'{c}'" for c in contratos_limpios])
            query_dinamica += f" AND tipo_contrato IN ({in_clause})"

        if filtros_depto_din:
            deptos_limpios = [d.replace("'", "''") for d in filtros_depto_din]
            in_clause_depto = ", ".join([f"'{d}'" for d in deptos_limpios])
            query_dinamica += f" AND departamento IN ({in_clause_depto})"
            
        if anios_sel:
            condiciones_anios = [f"fecha_radicado LIKE '%{a}%'" for a in anios_sel]
            query_dinamica += f" AND ({' OR '.join(condiciones_anios)})"
            
        if meses_sel:
            meses_str = ", ".join(meses_sel)
            query_dinamica += f" AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({meses_str})"
            
        # 🎯 Agrupamos de forma inteligente dependiendo de la vista elegida
        if tipo_vista == "🗺️ Departamento":
            query_dinamica += " GROUP BY 1"
        elif tipo_vista == "📄 Contratos":
            query_dinamica += " GROUP BY 1, 2, 3, 4, 5"
        elif tipo_vista == "💼 Cartera":
            query_dinamica += " GROUP BY 1, 2"
        else:
            query_dinamica += " GROUP BY 1, 2, 3"
        
        # 4. Ejecución y Visualización
        df_dinamico = conn.execute(query_dinamica).df().fillna(0)
        
        if not df_dinamico.empty:
            # Preparación de datos para la UI de Arriba
            t_pendiente = float(df_dinamico["Pendiente por Conciliar"].sum())
            val_pend = f"$ {t_pendiente:,.0f}".replace(',', '.')

            with header_container_din:
                col_tit_d, col_ind_d = st.columns([1, 1])
                with col_tit_d:
                    if tipo_vista == "🗺️ Departamento":
                        st.title("Análisis Geográfico")
                    elif tipo_vista == "📄 Contratos":
                        st.title("Análisis por Contratos")
                    elif tipo_vista == "💼 Cartera":
                        st.title("Análisis de Cartera")
                    else:
                        st.title("Análisis de Prestadores")
                        
                with col_ind_d:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end; align-items: center; padding-top: 1.55rem;">
                        <span style="background-color: rgba(240,253,244,0.05); border: 1px solid rgba(187,247,208,0.2); color: #4ade80; padding: 0 15px; border-radius: 8px; height: 40px; display: inline-flex; align-items: center; font-family: 'Inter', sans-serif; font-size: 0.95rem; box-sizing: border-box; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">Pendiente Total:&nbsp;<b>{val_pend}</b></span>
                    </div>
                    """, unsafe_allow_html=True)

            col_texto_ord = "Departamento" if tipo_vista == "🗺️ Departamento" else "Razón Social"
            
            # Lógica de Ordenamiento
            if ordenar_por == "Mayor a menor":
                df_dinamico = df_dinamico.sort_values(by="Pendiente por Conciliar", ascending=False)
            elif ordenar_por == "Menor a mayor":
                df_dinamico = df_dinamico.sort_values(by="Pendiente por Conciliar", ascending=True)
            elif ordenar_por == "A a Z":
                df_dinamico = df_dinamico.sort_values(by=col_texto_ord, ascending=True)
            elif ordenar_por == "Z a A":
                df_dinamico = df_dinamico.sort_values(by=col_texto_ord, ascending=False)
            
            with col_btn_exportar:
                st.markdown("<div style='font-size: 14px; margin-bottom: 6px; color: transparent;'>Copiar</div>", unsafe_allow_html=True)
                
                if st.button("📋 Copiar", type="primary", use_container_width=True):
                    try:
                        # 1. Creamos una copia aislada solo para el portapapeles
                        df_copia = df_dinamico.copy()
                        
                        # 2. Identificamos todas las columnas que deben ser números en Excel
                        cols_numericas = [
                            "Pendiente por Conciliar", "Total Facturado", "Total Glosado", 
                            "Valor Acepta IPS", "Valor Acepta EPS", "Auditado", "Cerrado", 
                            "Notificado", "Pendiente", "Número de Facturas"
                        ]
                        
                        # 3. Forzamos a entero (int64) para matar los decimales (.0) que confunden a Excel
                        for col in cols_numericas:
                            if col in df_copia.columns:
                                df_copia[col] = pd.to_numeric(df_copia[col], errors='coerce').fillna(0).astype('int64')
                        
                        # 4. Exportamos con decimal=',' por blindaje regional (Configuración Colombia/Latam)
                        df_copia.to_clipboard(index=False, sep='\t', decimal=',')
                        
                        st.toast("¡Datos copiados al portapapeles como números puros!", icon="✅")
                    except Exception as e:
                        st.error(f"Error al copiar: {e}")
            
            # 🎯 CORRECCIÓN: Los estados de auditoría ahora son dinero y pasan al bloque de la moneda
            columnas_moneda_din = [
                "Pendiente por Conciliar", "Total Facturado", "Total Glosado", 
                "Valor Acepta IPS", "Valor Acepta EPS", "Auditado", "Cerrado", 
                "Notificado", "Pendiente"
            ]
            for col_mon in columnas_moneda_din:
                if col_mon in df_dinamico.columns:
                    df_dinamico[col_mon] = df_dinamico[col_mon].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
            
            columnas_cuenta_din = ["Número de Facturas"]
            for col_cnt in columnas_cuenta_din:
                if col_cnt in df_dinamico.columns:
                    df_dinamico[col_cnt] = df_dinamico[col_cnt].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                
            st.dataframe(df_dinamico, use_container_width=True, hide_index=True, height=600)
            
        else:
            with header_container_din:
                if tipo_vista == "🗺️ Departamento": st.title("Análisis Geográfico")
                elif tipo_vista == "📄 Contratos": st.title("Análisis por Contratos")
                elif tipo_vista == "💼 Cartera": st.title("Análisis de Cartera")
                else: st.title("Análisis de Prestadores")
            st.info("No hay datos para mostrar con estos filtros.")

    # =========================================================================
    # PANTALLA 4: GERENCIAL
    # =========================================================================
    elif st.session_state.modulo_activo == "Gerencial":
        st.title("Panel Gerencial")
        
        # 🎯 NUEVO: Función maestra para Pills GRANDES y destacadas (SIN LÍMITE DE TEXTO)
        def mostrar_pills_filtros(filtros_dict):
            html_pills = "<div style='display: flex; flex-wrap: wrap; justify-content: flex-start; gap: 10px; margin-bottom: 15px;'>"
            hay_filtros = False
            for nombre, valor in filtros_dict.items():
                if valor:
                    hay_filtros = True
                    if isinstance(valor, list):
                        # Aquí unimos los valores directamente sin cortarlos
                        val_str = ", ".join([str(v) for v in valor])
                    else:
                        val_str = str(valor)
                    
                    html_pills += f"<span style='background-color: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; padding: 6px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 600; display: inline-flex; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{nombre}: <span style='color:#f8fafc; font-weight:400; margin-left:8px;'>{val_str}</span></span>"
            
            html_pills += "</div>"
            if hay_filtros:
                st.markdown(html_pills, unsafe_allow_html=True)
                
        # Creamos las 6 vistas mediante pestañas
        vista1, vista2, vista3, vista4, vista5, vista6 = st.tabs([
            "MES", "CONSULTA POR CONTRATO", "POS - NO POS", 
            "ESTADOS", "AUDITORES ESTADO", "RENDIMIENTO"
        ])

        with vista1:
            header_v1 = st.container()
            
            # --- 1. SECCIÓN DE FILTROS EN CASCADA (10 Filtros) ---
            f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
            f_col6, f_col7, f_col8, f_col9, f_col10 = st.columns(5)
            
            def obtener_opciones_v1(col_name, clave_propia):
                if col_name not in columnas_db: return []
                cond_cascada = "1=1"
                mapa_filtros = {'razon_social': 'v1_rs', 'nit': 'v1_nit', 'tipo_contrato': 'v1_tc', 'numero_contrato': 'v1_nc', 'tipo_regimen': 'v1_tr', 'usuario_auditoria_tecnica': 'v1_aud', 'pos': 'v1_pos', 'estado_tecnica': 'v1_est'}
                
                for col_db, session_key in mapa_filtros.items():
                    if session_key != clave_propia:
                        valores = st.session_state.get(session_key, [])
                        if valores:
                            limpios = [v.replace("'", "''") for v in valores]
                            cond_cascada += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                
                cond_fechas = []
                for k in st.session_state.keys():
                    if k.startswith('v1_meses_') and st.session_state.get(k):
                        anio = k.replace('v1_meses_', '')
                        m_str = ', '.join(st.session_state[k])
                        cond_fechas.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                if cond_fechas:
                    cond_cascada += f" AND ({' OR '.join(cond_fechas)})"
                    
                query = f"SELECT DISTINCT \"{col_name}\" FROM facturas WHERE \"{col_name}\" IS NOT NULL AND TRIM(CAST(\"{col_name}\" AS VARCHAR)) != '' AND {cond_cascada}"
                try:
                    res = conn.execute(query).df()[col_name].dropna().astype(str).tolist()
                    activos = st.session_state.get(clave_propia, [])
                    for a in activos:
                        if a not in res: res.append(a)
                    return sorted(res)
                except: return []

            def crear_popover_v1(col, titulo, col_db, clave):
                with col:
                    seleccion = st.session_state.get(clave, [])
                    label = f"🟢 {titulo}" if seleccion else titulo
                    with st.popover(label, use_container_width=True):
                        opciones = obtener_opciones_v1(col_db, clave)
                        return st.multiselect(titulo, opciones, key=clave, label_visibility="collapsed", placeholder="Buscar...")

            v1_rs = crear_popover_v1(f_col1, "Razón Social", 'razon_social', "v1_rs")
            v1_nit = crear_popover_v1(f_col2, "NIT", 'nit', "v1_nit")
            v1_tc = crear_popover_v1(f_col3, "Tipo Contrato", 'tipo_contrato', "v1_tc")
            v1_nc = crear_popover_v1(f_col4, "Núm Contrato", 'numero_contrato', "v1_nc")
            
            # 🎯 FECHA JERÁRQUICA BLINDADA V1
            with f_col5:
                hay_fechas_v1 = any(k.startswith('v1_meses_') and st.session_state.get(k) for k in st.session_state.keys())
                label_fechas_v1 = "🟢 Fecha Radicado" if hay_fechas_v1 else "Fecha Radicado"
                
                with st.popover(label_fechas_v1, use_container_width=True):
                    cond_a = "1=1"
                    map_a = {'razon_social': 'v1_rs', 'nit': 'v1_nit', 'tipo_contrato': 'v1_tc', 'numero_contrato': 'v1_nc', 'tipo_regimen': 'v1_tr', 'usuario_auditoria_tecnica': 'v1_aud', 'pos': 'v1_pos', 'estado_tecnica': 'v1_est'}
                    for col_db, skey in map_a.items():
                        vals = st.session_state.get(skey, [])
                        if vals:
                            l_vals = [v.replace("'", "''") for v in vals]
                            cond_a += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(l_vals) + "')"
                    try:
                        a_disp = sorted(list(set([str(a) for a in conn.execute(f"SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL AND {cond_a}").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                        if not a_disp:
                            a_disp = sorted(list(set([str(a) for a in conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                    except:
                        a_disp = []

                    if not a_disp:
                        st.caption("No hay periodos en la base de datos.")

                    nombres_meses = {'1':'Ene', '2':'Feb', '3':'Mar', '4':'Abr', '5':'May', '6':'Jun', '7':'Jul', '8':'Ago', '9':'Sep', '10':'Oct', '11':'Nov', '12':'Dic'}
                    
                    cond_fechas_sql_v1 = []
                    fechas_pill_v1 = []
                    
                    for anio in a_disp:
                        try:
                            meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%' AND {cond_a}").df()['mes'].dropna().astype(int).tolist()
                            if not meses_reales:
                                meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%'").df()['mes'].dropna().astype(int).tolist()
                            meses_lista = [str(m) for m in sorted(meses_reales)]
                        except:
                            meses_lista = []
                            
                        if meses_lista:
                            c_i, c_d = st.columns([1.2, 2.8])
                            with c_i: 
                                st.markdown(f"<div style='margin-top:6px; font-weight:700; color:#e2e8f0; font-size:14px;'>📅 {anio}</div>", unsafe_allow_html=True)
                            with c_d:
                                meses_sel = st.multiselect(f"Meses {anio}", options=meses_lista, format_func=lambda x: nombres_meses[x], key=f"v1_meses_{anio}", label_visibility="collapsed")
                            
                            if meses_sel:
                                m_str = ', '.join(meses_sel)
                                cond_fechas_sql_v1.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                                fechas_pill_v1.append(f"{anio}: {', '.join([nombres_meses[m] for m in meses_sel])}")

            v1_tr = crear_popover_v1(f_col6, "Tipo Régimen", 'tipo_regimen', "v1_tr")
            v1_aud = crear_popover_v1(f_col7, "Auditor", 'usuario_auditoria_tecnica', "v1_aud")
            v1_pos = crear_popover_v1(f_col8, "POS", 'pos', "v1_pos")
            v1_est = crear_popover_v1(f_col9, "Estado Técnica", 'estado_tecnica', "v1_est")
            
            with f_col10:
                v1_fac_val = st.session_state.get("v1_fac", "")
                label_fac = "🟢 Factura" if v1_fac_val else "Factura"
                with st.popover(label_fac, use_container_width=True):
                    v1_fac = st.text_input("Factura", key="v1_fac", placeholder="Escribir factura...", label_visibility="collapsed")

            st.write("---")

            # --- 2. VALIDACIÓN Y CONSULTA SQL ---
            where_v1 = "1=1"
            def aplicar_filtro(lista, col_name):
                if lista and col_name in columnas_db:
                    limpios = [v.replace("'", "''") for v in lista]
                    return f" AND CAST(\"{col_name}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                return ""
            
            where_v1 += aplicar_filtro(v1_rs, 'razon_social')
            where_v1 += aplicar_filtro(v1_nit, 'nit')
            where_v1 += aplicar_filtro(v1_tc, 'tipo_contrato')
            where_v1 += aplicar_filtro(v1_nc, 'numero_contrato')
            where_v1 += aplicar_filtro(v1_tr, 'tipo_regimen')
            where_v1 += aplicar_filtro(v1_aud, 'usuario_auditoria_tecnica')
            where_v1 += aplicar_filtro(v1_pos, 'pos')
            where_v1 += aplicar_filtro(v1_est, 'estado_tecnica')
            
            if v1_fac and 'factura' in columnas_db:
                where_v1 += f" AND CAST(factura AS VARCHAR) ILIKE '%{v1_fac.replace('\"', '')}%'"
            if cond_fechas_sql_v1:
                where_v1 += f" AND ({' OR '.join(cond_fechas_sql_v1)})"

            # --- 3. CONTEXTO Y HEADER ---
            rs_pill_v1 = v1_rs
            nit_pill_v1 = v1_nit
            
            if any([v1_rs, v1_nit, v1_nc, v1_fac]):
                try:
                    df_ctx = conn.execute(f"SELECT DISTINCT razon_social, nit FROM facturas WHERE {where_v1} AND razon_social IS NOT NULL LIMIT 4").df()
                    if not df_ctx.empty and len(df_ctx) <= 3:
                        rs_pill_v1 = df_ctx['razon_social'].dropna().astype(str).unique().tolist()
                        nit_pill_v1 = df_ctx['nit'].dropna().astype(str).unique().tolist()
                except: pass

            with header_v1:
                mostrar_pills_filtros({
                    "Razón Social": rs_pill_v1, "NIT": nit_pill_v1, 
                    "Tipo Contrato": v1_tc, "Núm Contrato": v1_nc, 
                    "Periodo": fechas_pill_v1, "Régimen": v1_tr, 
                    "Auditor": v1_aud, "POS": v1_pos, 
                    "Estado": v1_est, "Factura": v1_fac
                })

            # --- 4. EXTRACCIÓN Y TABLA ---
            query_v1 = f"""
                SELECT 
                    COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                    COUNT(factura) as "Cuenta de factura",
                    SUM(TRY_CAST(valor_factura AS DOUBLE)) as sum_vf,
                    SUM(TRY_CAST(total_glosas AS DOUBLE)) as sum_tg,
                    SUM(TRY_CAST(valor_total_acepta_eps AS DOUBLE)) as sum_eps,
                    SUM(TRY_CAST(valor_total_acepta_ips AS DOUBLE)) as sum_ips
                FROM facturas
                WHERE {where_v1} AND fecha_radicado IS NOT NULL AND fecha_radicado != ''
                GROUP BY num_mes
                HAVING num_mes IS NOT NULL
                ORDER BY num_mes
            """
            
            df_v1 = conn.execute(query_v1).df().fillna(0)
            
            if not df_v1.empty:
                meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                df_v1['fecha_radicado'] = df_v1['num_mes'].map(meses_min)
                
                total_cuenta = df_v1['Cuenta de factura'].sum()
                total_vf = df_v1['sum_vf'].sum()
                total_tg = df_v1['sum_tg'].sum()
                total_eps = df_v1['sum_eps'].sum()
                total_ips = df_v1['sum_ips'].sum()
                
                df_final_v1 = pd.DataFrame({
                    'fecha_radicado': df_v1['fecha_radicado'].tolist() + ['TOTAL GENERAL'],
                    'Cuenta de factura': df_v1['Cuenta de factura'].tolist() + [total_cuenta],
                    'Suma de valor_factura': df_v1['sum_vf'].tolist() + [total_vf],
                    'Suma de total_glosas': df_v1['sum_tg'].tolist() + [total_tg],
                    'Suma de valor_total_acepta_eps': df_v1['sum_eps'].tolist() + [total_eps],
                    'Suma de valor_total_acepta_ips': df_v1['sum_ips'].tolist() + [total_ips]
                })
                
                df_final_v1['Suma de DIFERENCIA'] = df_final_v1['Suma de total_glosas'] - (df_final_v1['Suma de valor_total_acepta_eps'] + df_final_v1['Suma de valor_total_acepta_ips'])
                
                for col in ['Suma de valor_factura', 'Suma de total_glosas', 'Suma de valor_total_acepta_eps', 'Suma de valor_total_acepta_ips', 'Suma de DIFERENCIA']:
                    df_final_v1[col] = df_final_v1[col].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                
                df_final_v1['Cuenta de factura'] = df_final_v1['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                
                def resaltar_ultima_fila(row):
                    if row.name == df_final_v1.index[-1]:
                        return ['font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'] * len(row)
                    return [''] * len(row)
                
                df_styled_v1 = df_final_v1.style.apply(resaltar_ultima_fila, axis=1)
                altura_tabla = (len(df_final_v1) * 36) + 43
                
                st.dataframe(df_styled_v1, use_container_width=True, hide_index=True, height=altura_tabla)
            else:
                st.info("Sin resultados para los filtros aplicados en esta vista.")
            
        with vista2:
            header_v2 = st.container()
            
            # --- 1. SECCIÓN DE FILTROS EN CASCADA (Aumentado a 6 columnas) ---
            f2_col1, f2_col2, f2_col3, f2_col4, f2_col5, f2_col6 = st.columns(6)
            
            def obtener_opciones_v2(col_name, clave_propia):
                if col_name not in columnas_db: return []
                cond_cascada = "1=1"
                mapa_filtros = {'razon_social': 'v2_rs', 'tipo_contrato': 'v2_tc', 'numero_contrato': 'v2_nc', 'nit': 'v2_nit'}
                
                for col_db, session_key in mapa_filtros.items():
                    if session_key != clave_propia:
                        valores = st.session_state.get(session_key, [])
                        if valores:
                            limpios = [v.replace("'", "''") for v in valores]
                            cond_cascada += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                
                cond_fechas = []
                for k in st.session_state.keys():
                    if k.startswith('v2_meses_') and st.session_state.get(k):
                        anio = k.replace('v2_meses_', '')
                        m_str = ', '.join(st.session_state[k])
                        cond_fechas.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                if cond_fechas:
                    cond_cascada += f" AND ({' OR '.join(cond_fechas)})"
                    
                query = f"SELECT DISTINCT \"{col_name}\" FROM facturas WHERE \"{col_name}\" IS NOT NULL AND TRIM(CAST(\"{col_name}\" AS VARCHAR)) != '' AND {cond_cascada}"
                try:
                    res = conn.execute(query).df()[col_name].dropna().astype(str).tolist()
                    activos = st.session_state.get(clave_propia, [])
                    for a in activos:
                        if a not in res: res.append(a)
                    return sorted(res)
                except: return []

            def crear_popover_v2(col, titulo, col_db, clave):
                with col:
                    seleccion = st.session_state.get(clave, [])
                    label = f"🟢 {titulo}" if seleccion else titulo
                    with st.popover(label, use_container_width=True):
                        opciones = obtener_opciones_v2(col_db, clave)
                        return st.multiselect(titulo, opciones, key=clave, label_visibility="collapsed", placeholder="Buscar...")

            # Filtros reordenados (RS y NIT de primeros)
            v2_rs = crear_popover_v2(f2_col1, "Razón Social", 'razon_social', "v2_rs")
            v2_nit = crear_popover_v2(f2_col2, "NIT", 'nit', "v2_nit")
            v2_tc = crear_popover_v2(f2_col3, "Tipo Contrato", 'tipo_contrato', "v2_tc")
            v2_nc = crear_popover_v2(f2_col4, "Núm Contrato", 'numero_contrato', "v2_nc")
            
            with f2_col5:
                hay_fechas_v2 = any(k.startswith('v2_meses_') and st.session_state.get(k) for k in st.session_state.keys())
                label_fechas_v2 = "🟢 Fecha Radicado" if hay_fechas_v2 else "Fecha Radicado"
                
                with st.popover(label_fechas_v2, use_container_width=True):
                    cond_a = "1=1"
                    map_a = {'razon_social': 'v2_rs', 'tipo_contrato': 'v2_tc', 'numero_contrato': 'v2_nc', 'nit': 'v2_nit'}
                    for col_db, skey in map_a.items():
                        vals = st.session_state.get(skey, [])
                        if vals:
                            l_vals = [v.replace("'", "''") for v in vals]
                            cond_a += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(l_vals) + "')"
                    try:
                        a_disp = sorted(list(set([str(a) for a in conn.execute(f"SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL AND {cond_a}").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                        if not a_disp:
                            a_disp = sorted(list(set([str(a) for a in conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                    except:
                        a_disp = []

                    if not a_disp:
                        st.caption("No hay periodos en la base de datos.")

                    nombres_meses = {'1':'Ene', '2':'Feb', '3':'Mar', '4':'Abr', '5':'May', '6':'Jun', '7':'Jul', '8':'Ago', '9':'Sep', '10':'Oct', '11':'Nov', '12':'Dic'}
                    
                    cond_fechas_sql_v2 = []
                    fechas_pill_v2 = []
                    
                    for anio in a_disp:
                        try:
                            meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%' AND {cond_a}").df()['mes'].dropna().astype(int).tolist()
                            if not meses_reales:
                                meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%'").df()['mes'].dropna().astype(int).tolist()
                            meses_lista = [str(m) for m in sorted(meses_reales)]
                        except:
                            meses_lista = []
                            
                        if meses_lista:
                            c_i, c_d = st.columns([1.2, 2.8])
                            with c_i: 
                                st.markdown(f"<div style='margin-top:6px; font-weight:700; color:#e2e8f0; font-size:14px;'>📅 {anio}</div>", unsafe_allow_html=True)
                            with c_d:
                                meses_sel = st.multiselect(f"Meses {anio}", options=meses_lista, format_func=lambda x: nombres_meses[x], key=f"v2_meses_{anio}", label_visibility="collapsed")
                            
                            if meses_sel:
                                m_str = ', '.join(meses_sel)
                                cond_fechas_sql_v2.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                                fechas_pill_v2.append(f"{anio}: {', '.join([nombres_meses[m] for m in meses_sel])}")

            with f2_col6:
                v2_fac_val = st.session_state.get("v2_fac", "")
                label_fac = "🟢 Factura" if v2_fac_val else "Factura"
                with st.popover(label_fac, use_container_width=True):
                    v2_fac = st.text_input("Factura", key="v2_fac", placeholder="Escribir factura...", label_visibility="collapsed")

            st.write("---")

            # --- 2. VALIDACIÓN Y CONSULTA SQL ---
            filtros_activos_v2 = any([v2_rs, v2_tc, v2_nc, v2_nit, v2_fac, hay_fechas_v2])
            
            where_v2 = "1=1"
            def aplicar_filtro_v2(lista, col_name):
                if lista and col_name in columnas_db:
                    limpios = [v.replace("'", "''") for v in lista]
                    return f" AND CAST(\"{col_name}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                return ""
                
            where_v2 += aplicar_filtro_v2(v2_rs, 'razon_social')
            where_v2 += aplicar_filtro_v2(v2_tc, 'tipo_contrato')
            where_v2 += aplicar_filtro_v2(v2_nc, 'numero_contrato')
            where_v2 += aplicar_filtro_v2(v2_nit, 'nit')
            
            if v2_fac and 'factura' in columnas_db:
                where_v2 += f" AND CAST(factura AS VARCHAR) ILIKE '%{v2_fac.replace('\"', '')}%'"
            if cond_fechas_sql_v2:
                where_v2 += f" AND ({' OR '.join(cond_fechas_sql_v2)})"

            # --- 3. CONTEXTO Y HEADER ---
            rs_pill_v2 = v2_rs
            nit_pill_v2 = v2_nit
            
            if any([v2_rs, v2_nit, v2_nc, v2_fac]):
                try:
                    df_ctx = conn.execute(f"SELECT DISTINCT razon_social, nit FROM facturas WHERE {where_v2} AND razon_social IS NOT NULL LIMIT 4").df()
                    if not df_ctx.empty and len(df_ctx) <= 3:
                        rs_pill_v2 = df_ctx['razon_social'].dropna().astype(str).unique().tolist()
                        nit_pill_v2 = df_ctx['nit'].dropna().astype(str).unique().tolist()
                except: pass

            with header_v2:
                mostrar_pills_filtros({
                    "Razón Social": rs_pill_v2, "NIT": nit_pill_v2, "Tipo Contrato": v2_tc, 
                    "Núm Contrato": v2_nc, "Periodo": fechas_pill_v2, "Factura": v2_fac
                })

            # --- 4. RENDERIZADO TABLA ---
            if not filtros_activos_v2:
                st.info("👆 Para optimizar el rendimiento, selecciona al menos un filtro en la parte superior para cargar los datos.")
            else:
                query_v2 = f"""
                    SELECT 
                        COALESCE(CAST(numero_contrato AS VARCHAR), 'SIN CONTRATO') as numero_contrato,
                        COALESCE(CAST(tipo_regimen AS VARCHAR), 'SIN REGIMEN') as tipo_regimen,
                        COUNT(factura) as "Cuenta de factura",
                        SUM(TRY_CAST(valor_factura AS DOUBLE)) as sum_vf,
                        SUM(TRY_CAST(total_glosas AS DOUBLE)) as sum_tg,
                        SUM(TRY_CAST(valor_total_acepta_eps AS DOUBLE)) as sum_eps,
                        SUM(TRY_CAST(valor_total_acepta_ips AS DOUBLE)) as sum_ips
                    FROM facturas
                    WHERE {where_v2}
                    GROUP BY numero_contrato, tipo_regimen
                    ORDER BY numero_contrato, tipo_regimen
                """
                
                df_v2 = conn.execute(query_v2).df().fillna(0)

                if not df_v2.empty:
                    total_cuenta = df_v2['Cuenta de factura'].sum()
                    total_vf = df_v2['sum_vf'].sum()
                    total_tg = df_v2['sum_tg'].sum()
                    total_eps = df_v2['sum_eps'].sum()
                    total_ips = df_v2['sum_ips'].sum()
                    
                    df_final_v2 = pd.DataFrame({
                        'numero_contrato': df_v2['numero_contrato'].tolist() + ['TOTAL GENERAL'],
                        'tipo_regimen': df_v2['tipo_regimen'].tolist() + [''],
                        'Cuenta de factura': df_v2['Cuenta de factura'].tolist() + [total_cuenta],
                        'Suma de valor_factura': df_v2['sum_vf'].tolist() + [total_vf],
                        'Suma de total_glosas': df_v2['sum_tg'].tolist() + [total_tg],
                        'Suma de valor_total_acepta_eps': df_v2['sum_eps'].tolist() + [total_eps],
                        'Suma de valor_total_acepta_ips': df_v2['sum_ips'].tolist() + [total_ips]
                    })
                    
                    df_final_v2['Suma de DIFERENCIA'] = df_final_v2['Suma de total_glosas'] - (df_final_v2['Suma de valor_total_acepta_eps'] + df_final_v2['Suma de valor_total_acepta_ips'])
                    
                    nc_list = df_final_v2['numero_contrato'].tolist()
                    for i in range(len(nc_list) - 2, 0, -1):
                        if nc_list[i] == nc_list[i-1]:
                            df_final_v2.at[i, 'numero_contrato'] = ""

                    for col in ['Suma de valor_factura', 'Suma de total_glosas', 'Suma de valor_total_acepta_eps', 'Suma de valor_total_acepta_ips', 'Suma de DIFERENCIA']:
                        df_final_v2[col] = df_final_v2[col].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                    
                    df_final_v2['Cuenta de factura'] = df_final_v2['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                    
                    def resaltar_ultima_fila_v2(row):
                        if row.name == df_final_v2.index[-1]:
                            return ['font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'] * len(row)
                        return [''] * len(row)
                    
                    df_styled_v2 = df_final_v2.style.apply(resaltar_ultima_fila_v2, axis=1)
                    altura_tabla_v2 = (len(df_final_v2) * 36) + 43
                    
                    st.dataframe(df_styled_v2, use_container_width=True, hide_index=True, height=altura_tabla_v2)
                else:
                    st.info("Sin resultados para los filtros aplicados en esta vista.")

        with vista3:
            header_v3 = st.container()
            
            # --- 1. SECCIÓN DE FILTROS EN CASCADA ---
            f3_col1, f3_col2, f3_col3, f3_col4, f3_col5 = st.columns(5)
            f3_col6, f3_col7, f3_col8, f3_col9 = st.columns(4)
            
            def obtener_opciones_v3(col_name, clave_propia):
                if col_name not in columnas_db: return []
                cond_cascada = "1=1"
                mapa_filtros = {'razon_social': 'v3_rs', 'nit': 'v3_nit', 'tipo_contrato': 'v3_tc', 'numero_contrato': 'v3_nc', 'tipo_regimen': 'v3_tr', 'usuario_auditoria_tecnica': 'v3_aud', 'pos': 'v3_pos'}
                
                for col_db, session_key in mapa_filtros.items():
                    if session_key != clave_propia:
                        valores = st.session_state.get(session_key, [])
                        if valores:
                            limpios = [v.replace("'", "''") for v in valores]
                            cond_cascada += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                
                cond_fechas = []
                for k in st.session_state.keys():
                    if k.startswith('v3_meses_') and st.session_state.get(k):
                        anio = k.replace('v3_meses_', '')
                        m_str = ', '.join(st.session_state[k])
                        cond_fechas.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                if cond_fechas:
                    cond_cascada += f" AND ({' OR '.join(cond_fechas)})"
                    
                query = f"SELECT DISTINCT \"{col_name}\" FROM facturas WHERE \"{col_name}\" IS NOT NULL AND TRIM(CAST(\"{col_name}\" AS VARCHAR)) != '' AND {cond_cascada}"
                try:
                    res = conn.execute(query).df()[col_name].dropna().astype(str).tolist()
                    activos = st.session_state.get(clave_propia, [])
                    for a in activos:
                        if a not in res: res.append(a)
                    return sorted(res)
                except: return []

            def crear_popover_v3(col, titulo, col_db, clave):
                with col:
                    seleccion = st.session_state.get(clave, [])
                    label = f"🟢 {titulo}" if seleccion else titulo
                    with st.popover(label, use_container_width=True):
                        opciones = obtener_opciones_v3(col_db, clave)
                        return st.multiselect(titulo, opciones, key=clave, label_visibility="collapsed", placeholder="Buscar...")

            # Fila 1 (RS, NIT, TC, NC, Fecha)
            v3_rs = crear_popover_v3(f3_col1, "Razón Social", 'razon_social', "v3_rs")
            v3_nit = crear_popover_v3(f3_col2, "NIT", 'nit', "v3_nit")
            v3_tc = crear_popover_v3(f3_col3, "Tipo Contrato", 'tipo_contrato', "v3_tc")
            v3_nc = crear_popover_v3(f3_col4, "Núm Contrato", 'numero_contrato', "v3_nc")
            
            with f3_col5:
                hay_fechas_v3 = any(k.startswith('v3_meses_') and st.session_state.get(k) for k in st.session_state.keys())
                label_fechas_v3 = "🟢 Fecha Radicado" if hay_fechas_v3 else "Fecha Radicado"
                
                with st.popover(label_fechas_v3, use_container_width=True):
                    cond_a = "1=1"
                    map_a = {'razon_social': 'v3_rs', 'nit': 'v3_nit', 'tipo_contrato': 'v3_tc', 'numero_contrato': 'v3_nc', 'tipo_regimen': 'v3_tr', 'usuario_auditoria_tecnica': 'v3_aud', 'pos': 'v3_pos'}
                    for col_db, skey in map_a.items():
                        vals = st.session_state.get(skey, [])
                        if vals:
                            l_vals = [v.replace("'", "''") for v in vals]
                            cond_a += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(l_vals) + "')"
                    try:
                        a_disp = sorted(list(set([str(a) for a in conn.execute(f"SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL AND {cond_a}").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                        if not a_disp:
                            a_disp = sorted(list(set([str(a) for a in conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                    except: a_disp = []

                    if not a_disp: st.caption("No hay periodos en la base de datos.")

                    nombres_meses = {'1':'Ene', '2':'Feb', '3':'Mar', '4':'Abr', '5':'May', '6':'Jun', '7':'Jul', '8':'Ago', '9':'Sep', '10':'Oct', '11':'Nov', '12':'Dic'}
                    cond_fechas_sql = []
                    fechas_pill_v3 = []
                    
                    for anio in a_disp:
                        try:
                            meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%' AND {cond_a}").df()['mes'].dropna().astype(int).tolist()
                            if not meses_reales:
                                meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%'").df()['mes'].dropna().astype(int).tolist()
                            meses_lista = [str(m) for m in sorted(meses_reales)]
                        except: meses_lista = []
                            
                        if meses_lista:
                            c_i, c_d = st.columns([1.2, 2.8])
                            with c_i: st.markdown(f"<div style='margin-top:6px; font-weight:700; color:#e2e8f0; font-size:14px;'>📅 {anio}</div>", unsafe_allow_html=True)
                            with c_d:
                                meses_sel = st.multiselect(f"Meses {anio}", options=meses_lista, format_func=lambda x: nombres_meses[x], key=f"v3_meses_{anio}", label_visibility="collapsed")
                            if meses_sel:
                                m_str = ', '.join(meses_sel)
                                cond_fechas_sql.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                                fechas_pill_v3.append(f"{anio}: {', '.join([nombres_meses[m] for m in meses_sel])}")

            # Fila 2 (TR, AUD, POS, FAC)
            v3_tr = crear_popover_v3(f3_col6, "Tipo Régimen", 'tipo_regimen', "v3_tr")
            v3_aud = crear_popover_v3(f3_col7, "Auditor", 'usuario_auditoria_tecnica', "v3_aud")
            v3_pos = crear_popover_v3(f3_col8, "POS", 'pos', "v3_pos")
            
            with f3_col9:
                v3_fac_val = st.session_state.get("v3_fac", "")
                label_fac = "🟢 Factura" if v3_fac_val else "Factura"
                with st.popover(label_fac, use_container_width=True):
                    v3_fac = st.text_input("Factura", key="v3_fac", placeholder="Escribir factura...", label_visibility="collapsed")

            st.write("---")

            # --- 2. VALIDACIÓN Y CONSTRUCCIÓN DE CONSULTA SQL ---
            where_v3 = "1=1"
            def aplicar_filtro_v3(lista, col_name):
                if lista and col_name in columnas_db:
                    limpios = [v.replace("'", "''") for v in lista]
                    return f" AND CAST(\"{col_name}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                return ""
            
            where_v3 += aplicar_filtro_v3(v3_rs, 'razon_social')
            where_v3 += aplicar_filtro_v3(v3_nit, 'nit')
            where_v3 += aplicar_filtro_v3(v3_tc, 'tipo_contrato')
            where_v3 += aplicar_filtro_v3(v3_nc, 'numero_contrato')
            where_v3 += aplicar_filtro_v3(v3_tr, 'tipo_regimen')
            where_v3 += aplicar_filtro_v3(v3_aud, 'usuario_auditoria_tecnica')
            where_v3 += aplicar_filtro_v3(v3_pos, 'pos')
            
            if v3_fac and 'factura' in columnas_db:
                where_v3 += f" AND CAST(factura AS VARCHAR) ILIKE '%{v3_fac.replace('\"', '')}%'"
            if cond_fechas_sql:
                where_v3 += f" AND ({' OR '.join(cond_fechas_sql)})"

            # --- 3. EXTRACCIÓN DE CONTEXTO (RS y NIT) Y RENDERIZADO DE HEADER ---
            rs_pill_v3 = v3_rs
            nit_pill_v3 = v3_nit
            
            if any([v3_rs, v3_nit, v3_nc, v3_fac]):
                try:
                    df_ctx = conn.execute(f"SELECT DISTINCT razon_social, nit FROM facturas WHERE {where_v3} AND razon_social IS NOT NULL LIMIT 4").df()
                    if not df_ctx.empty and len(df_ctx) <= 3:
                        rs_pill_v3 = df_ctx['razon_social'].dropna().astype(str).unique().tolist()
                        nit_pill_v3 = df_ctx['nit'].dropna().astype(str).unique().tolist()
                except: pass

            with header_v3:
                mostrar_pills_filtros({
                    "Razón Social": rs_pill_v3, "NIT": nit_pill_v3, "Tipo Contrato": v3_tc, 
                    "Núm Contrato": v3_nc, "Régimen": v3_tr, "Auditor": v3_aud, "POS": v3_pos, 
                    "Periodo": fechas_pill_v3, "Factura": v3_fac
                })

            # --- 4. EXTRACCIÓN DE DATOS Y RENDERIZADO TABLA ESTILO EXCEL ---
            query_v3 = f"""
                SELECT 
                    COALESCE(CAST(pos AS VARCHAR), 'SIN ESPECIFICAR') as pos,
                    COALESCE(CAST(estado_tecnica AS VARCHAR), 'SIN ESTADO') as estado_tecnica,
                    COUNT(factura) as "Cuenta de factura",
                    SUM(TRY_CAST(valor_factura AS DOUBLE)) as sum_vf,
                    SUM(TRY_CAST(total_glosas AS DOUBLE)) as sum_tg,
                    SUM(TRY_CAST(valor_total_acepta_eps AS DOUBLE)) as sum_eps,
                    SUM(TRY_CAST(valor_total_acepta_ips AS DOUBLE)) as sum_ips
                FROM facturas
                WHERE {where_v3}
                GROUP BY pos, estado_tecnica
                ORDER BY pos, estado_tecnica
            """
            
            df_v3 = conn.execute(query_v3).df().fillna(0)
            
            if not df_v3.empty:
                total_cuenta = df_v3['Cuenta de factura'].sum()
                total_vf = df_v3['sum_vf'].sum()
                total_tg = df_v3['sum_tg'].sum()
                total_eps = df_v3['sum_eps'].sum()
                total_ips = df_v3['sum_ips'].sum()
                
                df_final_v3 = pd.DataFrame({
                    'pos': df_v3['pos'].tolist() + ['TOTAL GENERAL'],
                    'estado_tecnica': df_v3['estado_tecnica'].tolist() + [''],
                    'Cuenta de factura': df_v3['Cuenta de factura'].tolist() + [total_cuenta],
                    'Suma de valor_factura': df_v3['sum_vf'].tolist() + [total_vf],
                    'Suma de total_glosas': df_v3['sum_tg'].tolist() + [total_tg],
                    'Suma de valor_total_acepta_eps': df_v3['sum_eps'].tolist() + [total_eps],
                    'Suma de valor_total_acepta_ips': df_v3['sum_ips'].tolist() + [total_ips]
                })
                
                df_final_v3['Suma de DIFERENCIA'] = df_final_v3['Suma de total_glosas'] - (df_final_v3['Suma de valor_total_acepta_eps'] + df_final_v3['Suma de valor_total_acepta_ips'])
                
                pos_list = df_final_v3['pos'].tolist()
                for i in range(len(pos_list) - 2, 0, -1):
                    if pos_list[i] == pos_list[i-1]:
                        df_final_v3.at[i, 'pos'] = ""

                for col in ['Suma de valor_factura', 'Suma de total_glosas', 'Suma de valor_total_acepta_eps', 'Suma de valor_total_acepta_ips', 'Suma de DIFERENCIA']:
                    df_final_v3[col] = df_final_v3[col].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                
                df_final_v3['Cuenta de factura'] = df_final_v3['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                
                def resaltar_ultima_fila_v3(row):
                    if row.name == df_final_v3.index[-1]:
                        return ['font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'] * len(row)
                    return [''] * len(row)
                
                df_styled_v3 = df_final_v3.style.apply(resaltar_ultima_fila_v3, axis=1)
                altura_tabla = (len(df_final_v3) * 36) + 43
                
                st.dataframe(df_styled_v3, use_container_width=True, hide_index=True, height=altura_tabla)
            else:
                st.info("Sin resultados para los filtros aplicados en esta vista.")
            
        with vista4:
            header_v4 = st.container()
            
            # --- 1. SECCIÓN DE FILTROS EN CASCADA (9 Filtros: 5 arriba, 4 abajo) ---
            f4_col1, f4_col2, f4_col3, f4_col4, f4_col5 = st.columns(5)
            f4_col6, f4_col7, f4_col8, f4_col9 = st.columns(4)
            
            def obtener_opciones_v4(col_name, clave_propia):
                if col_name not in columnas_db: return []
                cond_cascada = "1=1"
                mapa_filtros = {'razon_social': 'v4_rs', 'nit': 'v4_nit', 'tipo_contrato': 'v4_tc', 'numero_contrato': 'v4_nc', 'tipo_regimen': 'v4_tr', 'usuario_auditoria_tecnica': 'v4_aud', 'pos': 'v4_pos'}
                
                for col_db, session_key in mapa_filtros.items():
                    if session_key != clave_propia:
                        valores = st.session_state.get(session_key, [])
                        if valores:
                            limpios = [v.replace("'", "''") for v in valores]
                            cond_cascada += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                
                cond_fechas = []
                for k in st.session_state.keys():
                    if k.startswith('v4_meses_') and st.session_state.get(k):
                        anio = k.replace('v4_meses_', '')
                        m_str = ', '.join(st.session_state[k])
                        cond_fechas.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                if cond_fechas:
                    cond_cascada += f" AND ({' OR '.join(cond_fechas)})"
                    
                query = f"SELECT DISTINCT \"{col_name}\" FROM facturas WHERE \"{col_name}\" IS NOT NULL AND TRIM(CAST(\"{col_name}\" AS VARCHAR)) != '' AND {cond_cascada}"
                try:
                    res = conn.execute(query).df()[col_name].dropna().astype(str).tolist()
                    activos = st.session_state.get(clave_propia, [])
                    for a in activos:
                        if a not in res: res.append(a)
                    return sorted(res)
                except: return []

            def crear_popover_v4(col, titulo, col_db, clave):
                with col:
                    seleccion = st.session_state.get(clave, [])
                    label = f"🟢 {titulo}" if seleccion else titulo
                    with st.popover(label, use_container_width=True):
                        opciones = obtener_opciones_v4(col_db, clave)
                        return st.multiselect(titulo, opciones, key=clave, label_visibility="collapsed", placeholder="Buscar...")

            # Fila 1 (RS, NIT, TC, NC, Fecha)
            v4_rs = crear_popover_v4(f4_col1, "Razón Social", 'razon_social', "v4_rs")
            v4_nit = crear_popover_v4(f4_col2, "NIT", 'nit', "v4_nit")
            v4_tc = crear_popover_v4(f4_col3, "Tipo Contrato", 'tipo_contrato', "v4_tc")
            v4_nc = crear_popover_v4(f4_col4, "Núm Contrato", 'numero_contrato', "v4_nc")
            
            with f4_col5:
                hay_fechas_v4 = any(k.startswith('v4_meses_') and st.session_state.get(k) for k in st.session_state.keys())
                label_fechas_v4 = "🟢 Fecha Radicado" if hay_fechas_v4 else "Fecha Radicado"
                
                with st.popover(label_fechas_v4, use_container_width=True):
                    cond_a = "1=1"
                    map_a = {'razon_social': 'v4_rs', 'nit': 'v4_nit', 'tipo_contrato': 'v4_tc', 'numero_contrato': 'v4_nc', 'tipo_regimen': 'v4_tr', 'usuario_auditoria_tecnica': 'v4_aud', 'pos': 'v4_pos'}
                    for col_db, skey in map_a.items():
                        vals = st.session_state.get(skey, [])
                        if vals:
                            l_vals = [v.replace("'", "''") for v in vals]
                            cond_a += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(l_vals) + "')"
                    try:
                        a_disp = sorted(list(set([str(a) for a in conn.execute(f"SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL AND {cond_a}").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                        if not a_disp:
                            a_disp = sorted(list(set([str(a) for a in conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                    except: a_disp = []

                    if not a_disp: st.caption("No hay periodos en la base de datos.")

                    nombres_meses = {'1':'Ene', '2':'Feb', '3':'Mar', '4':'Abr', '5':'May', '6':'Jun', '7':'Jul', '8':'Ago', '9':'Sep', '10':'Oct', '11':'Nov', '12':'Dic'}
                    cond_fechas_sql_v4 = []
                    fechas_pill_v4 = []
                    
                    for anio in a_disp:
                        try:
                            meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%' AND {cond_a}").df()['mes'].dropna().astype(int).tolist()
                            if not meses_reales:
                                meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%'").df()['mes'].dropna().astype(int).tolist()
                            meses_lista = [str(m) for m in sorted(meses_reales)]
                        except: meses_lista = []
                            
                        if meses_lista:
                            c_i, c_d = st.columns([1.2, 2.8])
                            with c_i: st.markdown(f"<div style='margin-top:6px; font-weight:700; color:#e2e8f0; font-size:14px;'>📅 {anio}</div>", unsafe_allow_html=True)
                            with c_d:
                                meses_sel = st.multiselect(f"Meses {anio}", options=meses_lista, format_func=lambda x: nombres_meses[x], key=f"v4_meses_{anio}", label_visibility="collapsed")
                            if meses_sel:
                                m_str = ', '.join(meses_sel)
                                cond_fechas_sql_v4.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                                fechas_pill_v4.append(f"{anio}: {', '.join([nombres_meses[m] for m in meses_sel])}")

            # Fila 2 (TR, AUD, POS, FAC)
            v4_tr = crear_popover_v4(f4_col6, "Tipo Régimen", 'tipo_regimen', "v4_tr")
            v4_aud = crear_popover_v4(f4_col7, "Auditor", 'usuario_auditoria_tecnica', "v4_aud")
            v4_pos = crear_popover_v4(f4_col8, "POS", 'pos', "v4_pos")
            
            with f4_col9:
                v4_fac_val = st.session_state.get("v4_fac", "")
                label_fac = "🟢 Factura" if v4_fac_val else "Factura"
                with st.popover(label_fac, use_container_width=True):
                    v4_fac = st.text_input("Factura", key="v4_fac", placeholder="Escribir factura...", label_visibility="collapsed")

            st.write("---")

            # --- 2. VALIDACIÓN Y CONSTRUCCIÓN DE CONSULTA SQL ---
            where_v4 = "1=1"
            def aplicar_filtro_v4(lista, col_name):
                if lista and col_name in columnas_db:
                    limpios = [v.replace("'", "''") for v in lista]
                    return f" AND CAST(\"{col_name}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                return ""
            
            where_v4 += aplicar_filtro_v4(v4_rs, 'razon_social')
            where_v4 += aplicar_filtro_v4(v4_tc, 'tipo_contrato')
            where_v4 += aplicar_filtro_v4(v4_nc, 'numero_contrato')
            where_v4 += aplicar_filtro_v4(v4_nit, 'nit')
            where_v4 += aplicar_filtro_v4(v4_tr, 'tipo_regimen')
            where_v4 += aplicar_filtro_v4(v4_aud, 'usuario_auditoria_tecnica')
            where_v4 += aplicar_filtro_v4(v4_pos, 'pos')
            
            if v4_fac and 'factura' in columnas_db:
                where_v4 += f" AND CAST(factura AS VARCHAR) ILIKE '%{v4_fac.replace('\"', '')}%'"
            if cond_fechas_sql_v4:
                where_v4 += f" AND ({' OR '.join(cond_fechas_sql_v4)})"

            # --- 3. EXTRACCIÓN DE CONTEXTO (RS y NIT) Y RENDERIZADO DE HEADER ---
            rs_pill_v4 = v4_rs
            nit_pill_v4 = v4_nit
            
            if any([v4_rs, v4_nit, v4_nc, v4_fac]):
                try:
                    df_ctx = conn.execute(f"SELECT DISTINCT razon_social, nit FROM facturas WHERE {where_v4} AND razon_social IS NOT NULL LIMIT 4").df()
                    if not df_ctx.empty and len(df_ctx) <= 3:
                        rs_pill_v4 = df_ctx['razon_social'].dropna().astype(str).unique().tolist()
                        nit_pill_v4 = df_ctx['nit'].dropna().astype(str).unique().tolist()
                except: pass

            with header_v4:
                mostrar_pills_filtros({
                    "Razón Social": rs_pill_v4, "NIT": nit_pill_v4, "Tipo Contrato": v4_tc, 
                    "Núm Contrato": v4_nc, "Régimen": v4_tr, "Auditor": v4_aud, "POS": v4_pos, 
                    "Periodo": fechas_pill_v4, "Factura": v4_fac
                })

            # --- 4. EXTRACCIÓN DE DATOS Y RENDERIZADO TABLA ESTILO EXCEL ---
            query_v4 = f"""
                SELECT 
                    COALESCE(CAST(estado_tecnica AS VARCHAR), 'SIN ESTADO') as estado_tecnica,
                    COUNT(factura) as "Cuenta de factura",
                    SUM(TRY_CAST(valor_factura AS DOUBLE)) as sum_vf,
                    SUM(TRY_CAST(total_glosas AS DOUBLE)) as sum_tg,
                    SUM(TRY_CAST(valor_total_acepta_eps AS DOUBLE)) as sum_eps,
                    SUM(TRY_CAST(valor_total_acepta_ips AS DOUBLE)) as sum_ips
                FROM facturas
                WHERE {where_v4}
                GROUP BY estado_tecnica
                ORDER BY estado_tecnica
            """
            
            df_v4 = conn.execute(query_v4).df().fillna(0)
            
            if not df_v4.empty:
                total_cuenta = df_v4['Cuenta de factura'].sum()
                total_vf = df_v4['sum_vf'].sum()
                total_tg = df_v4['sum_tg'].sum()
                total_eps = df_v4['sum_eps'].sum()
                total_ips = df_v4['sum_ips'].sum()
                
                df_final_v4 = pd.DataFrame({
                    'estado_tecnica': df_v4['estado_tecnica'].tolist() + ['TOTAL GENERAL'],
                    'Cuenta de factura': df_v4['Cuenta de factura'].tolist() + [total_cuenta],
                    'Suma de valor_factura': df_v4['sum_vf'].tolist() + [total_vf],
                    'Suma de total_glosas': df_v4['sum_tg'].tolist() + [total_tg],
                    'Suma de valor_total_acepta_eps': df_v4['sum_eps'].tolist() + [total_eps],
                    'Suma de valor_total_acepta_ips': df_v4['sum_ips'].tolist() + [total_ips]
                })
                
                df_final_v4['Suma de DIFERENCIA'] = df_final_v4['Suma de total_glosas'] - (df_final_v4['Suma de valor_total_acepta_eps'] + df_final_v4['Suma de valor_total_acepta_ips'])
                
                for col in ['Suma de valor_factura', 'Suma de total_glosas', 'Suma de valor_total_acepta_eps', 'Suma de valor_total_acepta_ips', 'Suma de DIFERENCIA']:
                    df_final_v4[col] = df_final_v4[col].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                
                df_final_v4['Cuenta de factura'] = df_final_v4['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                
                def resaltar_ultima_fila_v4(row):
                    if row.name == df_final_v4.index[-1]:
                        return ['font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'] * len(row)
                    return [''] * len(row)
                
                df_styled_v4 = df_final_v4.style.apply(resaltar_ultima_fila_v4, axis=1)
                altura_tabla = (len(df_final_v4) * 36) + 43
                
                st.dataframe(df_styled_v4, use_container_width=True, hide_index=True, height=altura_tabla)
            else:
                st.info("Sin resultados para los filtros aplicados en esta vista.")
            
        with vista5:
            header_v5 = st.container()
            
            # --- 1. SECCIÓN DE FILTROS EN CASCADA (9 Filtros: 5 arriba, 4 abajo) ---
            f5_col1, f5_col2, f5_col3, f5_col4, f5_col5 = st.columns(5)
            f5_col6, f5_col7, f5_col8, f5_col9 = st.columns(4)
            
            def obtener_opciones_v5(col_name, clave_propia):
                if col_name not in columnas_db: return []
                cond_cascada = "1=1"
                mapa_filtros = {'razon_social': 'v5_rs', 'nit': 'v5_nit', 'tipo_contrato': 'v5_tc', 'numero_contrato': 'v5_nc', 'tipo_regimen': 'v5_tr', 'estado_tecnica': 'v5_est', 'pos': 'v5_pos'}
                
                for col_db, session_key in mapa_filtros.items():
                    if session_key != clave_propia:
                        valores = st.session_state.get(session_key, [])
                        if valores:
                            limpios = [v.replace("'", "''") for v in valores]
                            cond_cascada += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                
                cond_fechas = []
                for k in st.session_state.keys():
                    if k.startswith('v5_meses_') and st.session_state.get(k):
                        anio = k.replace('v5_meses_', '')
                        m_str = ', '.join(st.session_state[k])
                        cond_fechas.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                if cond_fechas:
                    cond_cascada += f" AND ({' OR '.join(cond_fechas)})"
                    
                query = f"SELECT DISTINCT \"{col_name}\" FROM facturas WHERE \"{col_name}\" IS NOT NULL AND TRIM(CAST(\"{col_name}\" AS VARCHAR)) != '' AND {cond_cascada}"
                try:
                    res = conn.execute(query).df()[col_name].dropna().astype(str).tolist()
                    activos = st.session_state.get(clave_propia, [])
                    for a in activos:
                        if a not in res: res.append(a)
                    return sorted(res)
                except: return []

            def crear_popover_v5(col, titulo, col_db, clave):
                with col:
                    seleccion = st.session_state.get(clave, [])
                    label = f"🟢 {titulo}" if seleccion else titulo
                    with st.popover(label, use_container_width=True):
                        opciones = obtener_opciones_v5(col_db, clave)
                        return st.multiselect(titulo, opciones, key=clave, label_visibility="collapsed", placeholder="Buscar...")

            # Fila 1 (RS, NIT, TC, NC, Fecha)
            v5_rs = crear_popover_v5(f5_col1, "Razón Social", 'razon_social', "v5_rs")
            v5_nit = crear_popover_v5(f5_col2, "NIT", 'nit', "v5_nit")
            v5_tc = crear_popover_v5(f5_col3, "Tipo Contrato", 'tipo_contrato', "v5_tc")
            v5_nc = crear_popover_v5(f5_col4, "Núm Contrato", 'numero_contrato', "v5_nc")
            
            with f5_col5:
                hay_fechas_v5 = any(k.startswith('v5_meses_') and st.session_state.get(k) for k in st.session_state.keys())
                label_fechas_v5 = "🟢 Fecha Radicado" if hay_fechas_v5 else "Fecha Radicado"
                
                with st.popover(label_fechas_v5, use_container_width=True):
                    cond_a = "1=1"
                    map_a = {'razon_social': 'v5_rs', 'nit': 'v5_nit', 'tipo_contrato': 'v5_tc', 'numero_contrato': 'v5_nc', 'tipo_regimen': 'v5_tr', 'estado_tecnica': 'v5_est', 'pos': 'v5_pos'}
                    for col_db, skey in map_a.items():
                        vals = st.session_state.get(skey, [])
                        if vals:
                            l_vals = [v.replace("'", "''") for v in vals]
                            cond_a += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(l_vals) + "')"
                    try:
                        a_disp = sorted(list(set([str(a) for a in conn.execute(f"SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL AND {cond_a}").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                        if not a_disp:
                            a_disp = sorted(list(set([str(a) for a in conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                    except: a_disp = []

                    if not a_disp: st.caption("No hay periodos en la base de datos.")

                    nombres_meses = {'1':'Ene', '2':'Feb', '3':'Mar', '4':'Abr', '5':'May', '6':'Jun', '7':'Jul', '8':'Ago', '9':'Sep', '10':'Oct', '11':'Nov', '12':'Dic'}
                    cond_fechas_sql_v5 = []
                    fechas_pill_v5 = []
                    
                    for anio in a_disp:
                        try:
                            meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%' AND {cond_a}").df()['mes'].dropna().astype(int).tolist()
                            if not meses_reales:
                                meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%'").df()['mes'].dropna().astype(int).tolist()
                            meses_lista = [str(m) for m in sorted(meses_reales)]
                        except: meses_lista = []
                            
                        if meses_lista:
                            c_i, c_d = st.columns([1.2, 2.8])
                            with c_i: st.markdown(f"<div style='margin-top:6px; font-weight:700; color:#e2e8f0; font-size:14px;'>📅 {anio}</div>", unsafe_allow_html=True)
                            with c_d:
                                meses_sel = st.multiselect(f"Meses {anio}", options=meses_lista, format_func=lambda x: nombres_meses[x], key=f"v5_meses_{anio}", label_visibility="collapsed")
                            if meses_sel:
                                m_str = ', '.join(meses_sel)
                                cond_fechas_sql_v5.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                                fechas_pill_v5.append(f"{anio}: {', '.join([nombres_meses[m] for m in meses_sel])}")

            # Fila 2 (TR, POS, EST, FAC)
            v5_tr = crear_popover_v5(f5_col6, "Tipo Régimen", 'tipo_regimen', "v5_tr")
            v5_pos = crear_popover_v5(f5_col7, "POS", 'pos', "v5_pos")
            v5_est = crear_popover_v5(f5_col8, "Estado Técnica", 'estado_tecnica', "v5_est")
            
            with f5_col9:
                v5_fac_val = st.session_state.get("v5_fac", "")
                label_fac = "🟢 Factura" if v5_fac_val else "Factura"
                with st.popover(label_fac, use_container_width=True):
                    v5_fac = st.text_input("Factura", key="v5_fac", placeholder="Escribir factura...", label_visibility="collapsed")

            st.write("---")

            # --- 2. VALIDACIÓN Y CONSTRUCCIÓN DE CONSULTA SQL ---
            where_v5 = "1=1"
            def aplicar_filtro_v5(lista, col_name):
                if lista and col_name in columnas_db:
                    limpios = [v.replace("'", "''") for v in lista]
                    return f" AND CAST(\"{col_name}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                return ""
            
            where_v5 += aplicar_filtro_v5(v5_rs, 'razon_social')
            where_v5 += aplicar_filtro_v5(v5_nit, 'nit')
            where_v5 += aplicar_filtro_v5(v5_tc, 'tipo_contrato')
            where_v5 += aplicar_filtro_v5(v5_nc, 'numero_contrato')
            where_v5 += aplicar_filtro_v5(v5_tr, 'tipo_regimen')
            where_v5 += aplicar_filtro_v5(v5_est, 'estado_tecnica')
            where_v5 += aplicar_filtro_v5(v5_pos, 'pos')
            
            if v5_fac and 'factura' in columnas_db:
                where_v5 += f" AND CAST(factura AS VARCHAR) ILIKE '%{v5_fac.replace('\"', '')}%'"
            if cond_fechas_sql_v5:
                where_v5 += f" AND ({' OR '.join(cond_fechas_sql_v5)})"

            # --- 3. EXTRACCIÓN DE CONTEXTO (RS y NIT) Y RENDERIZADO DE HEADER ---
            rs_pill_v5 = v5_rs
            nit_pill_v5 = v5_nit
            
            if any([v5_rs, v5_nit, v5_nc, v5_fac]):
                try:
                    df_ctx = conn.execute(f"SELECT DISTINCT razon_social, nit FROM facturas WHERE {where_v5} AND razon_social IS NOT NULL LIMIT 4").df()
                    if not df_ctx.empty and len(df_ctx) <= 3:
                        rs_pill_v5 = df_ctx['razon_social'].dropna().astype(str).unique().tolist()
                        nit_pill_v5 = df_ctx['nit'].dropna().astype(str).unique().tolist()
                except: pass

            with header_v5:
                mostrar_pills_filtros({
                    "Razón Social": rs_pill_v5, "NIT": nit_pill_v5, "Tipo Contrato": v5_tc, 
                    "Núm Contrato": v5_nc, "Régimen": v5_tr, "Estado Técnica": v5_est, "POS": v5_pos, 
                    "Periodo": fechas_pill_v5, "Factura": v5_fac
                })

            # --- 4. EXTRACCIÓN DE DATOS Y RENDERIZADO TABLA ESTILO EXCEL ---
            query_v5 = f"""
                SELECT 
                    COALESCE(CAST(estado_tecnica AS VARCHAR), 'SIN ESTADO') as estado_tecnica,
                    COALESCE(CAST(usuario_auditoria_tecnica AS VARCHAR), 'SIN AUDITOR') as usuario_auditoria_tecnica,
                    COUNT(factura) as "Cuenta de factura",
                    SUM(TRY_CAST(valor_factura AS DOUBLE)) as sum_vf,
                    SUM(TRY_CAST(total_glosas AS DOUBLE)) as sum_tg,
                    SUM(TRY_CAST(valor_total_acepta_eps AS DOUBLE)) as sum_eps,
                    SUM(TRY_CAST(valor_total_acepta_ips AS DOUBLE)) as sum_ips
                FROM facturas
                WHERE {where_v5}
                GROUP BY estado_tecnica, usuario_auditoria_tecnica
                ORDER BY estado_tecnica, usuario_auditoria_tecnica
            """
            
            df_v5 = conn.execute(query_v5).df().fillna(0)
            
            if not df_v5.empty:
                total_cuenta = df_v5['Cuenta de factura'].sum()
                total_vf = df_v5['sum_vf'].sum()
                total_tg = df_v5['sum_tg'].sum()
                total_eps = df_v5['sum_eps'].sum()
                total_ips = df_v5['sum_ips'].sum()
                
                df_final_v5 = pd.DataFrame({
                    'estado_tecnica': df_v5['estado_tecnica'].tolist() + ['TOTAL GENERAL'],
                    'usuario_auditoria_tecnica': df_v5['usuario_auditoria_tecnica'].tolist() + [''],
                    'Cuenta de factura': df_v5['Cuenta de factura'].tolist() + [total_cuenta],
                    'Suma de valor_factura': df_v5['sum_vf'].tolist() + [total_vf],
                    'Suma de total_glosas': df_v5['sum_tg'].tolist() + [total_tg],
                    'Suma de valor_total_acepta_eps': df_v5['sum_eps'].tolist() + [total_eps],
                    'Suma de valor_total_acepta_ips': df_v5['sum_ips'].tolist() + [total_ips]
                })
                
                df_final_v5['Suma de DIFERENCIA'] = df_final_v5['Suma de total_glosas'] - (df_final_v5['Suma de valor_total_acepta_eps'] + df_final_v5['Suma de valor_total_acepta_ips'])
                
                # 🎯 MAGIA: Efecto Tabla Dinámica (Ocultar textos repetidos)
                est_list = df_final_v5['estado_tecnica'].tolist()
                for i in range(len(est_list) - 2, 0, -1):
                    if est_list[i] == est_list[i-1]:
                        df_final_v5.at[i, 'estado_tecnica'] = ""

                for col in ['Suma de valor_factura', 'Suma de total_glosas', 'Suma de valor_total_acepta_eps', 'Suma de valor_total_acepta_ips', 'Suma de DIFERENCIA']:
                    df_final_v5[col] = df_final_v5[col].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                
                df_final_v5['Cuenta de factura'] = df_final_v5['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                
                def resaltar_ultima_fila_v5(row):
                    if row.name == df_final_v5.index[-1]:
                        return ['font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'] * len(row)
                    return [''] * len(row)
                
                df_styled_v5 = df_final_v5.style.apply(resaltar_ultima_fila_v5, axis=1)
                altura_tabla = (len(df_final_v5) * 36) + 43
                
                st.dataframe(df_styled_v5, use_container_width=True, hide_index=True, height=altura_tabla)
            else:
                st.info("Sin resultados para los filtros aplicados en esta vista.")
            
        with vista6:
            header_v6 = st.container()
            
            # --- 1. SECCIÓN DE FILTROS EN CASCADA (10 Filtros: 2 filas de 5) ---
            f6_col1, f6_col2, f6_col3, f6_col4, f6_col5 = st.columns(5)
            f6_col6, f6_col7, f6_col8, f6_col9, f6_col10 = st.columns(5)
            
            def obtener_opciones_v6(col_name, clave_propia):
                if col_name not in columnas_db: return []
                cond_cascada = "1=1"
                mapa_filtros = {'razon_social': 'v6_rs', 'nit': 'v6_nit', 'tipo_contrato': 'v6_tc', 'numero_contrato': 'v6_nc', 'tipo_regimen': 'v6_tr', 'usuario_auditoria_tecnica': 'v6_aud', 'pos': 'v6_pos', 'estado_tecnica': 'v6_est'}
                
                for col_db, session_key in mapa_filtros.items():
                    if session_key != clave_propia:
                        valores = st.session_state.get(session_key, [])
                        if valores:
                            limpios = [v.replace("'", "''") for v in valores]
                            cond_cascada += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                
                cond_fechas = []
                for k in st.session_state.keys():
                    if k.startswith('v6_meses_') and st.session_state.get(k):
                        anio = k.replace('v6_meses_', '')
                        m_str = ', '.join(st.session_state[k])
                        cond_fechas.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                if cond_fechas:
                    cond_cascada += f" AND ({' OR '.join(cond_fechas)})"
                    
                query = f"SELECT DISTINCT \"{col_name}\" FROM facturas WHERE \"{col_name}\" IS NOT NULL AND TRIM(CAST(\"{col_name}\" AS VARCHAR)) != '' AND {cond_cascada}"
                try:
                    res = conn.execute(query).df()[col_name].dropna().astype(str).tolist()
                    activos = st.session_state.get(clave_propia, [])
                    for a in activos:
                        if a not in res: res.append(a)
                    return sorted(res)
                except: return []

            def crear_popover_v6(col, titulo, col_db, clave):
                with col:
                    seleccion = st.session_state.get(clave, [])
                    label = f"🟢 {titulo}" if seleccion else titulo
                    with st.popover(label, use_container_width=True):
                        opciones = obtener_opciones_v6(col_db, clave)
                        return st.multiselect(titulo, opciones, key=clave, label_visibility="collapsed", placeholder="Buscar...")

            # Fila 1 (RS, NIT, TC, NC, Fecha)
            v6_rs = crear_popover_v6(f6_col1, "Razón Social", 'razon_social', "v6_rs")
            v6_nit = crear_popover_v6(f6_col2, "NIT", 'nit', "v6_nit")
            v6_tc = crear_popover_v6(f6_col3, "Tipo Contrato", 'tipo_contrato', "v6_tc")
            v6_nc = crear_popover_v6(f6_col4, "Núm Contrato", 'numero_contrato', "v6_nc")
            
            with f6_col5:
                hay_fechas_v6 = any(k.startswith('v6_meses_') and st.session_state.get(k) for k in st.session_state.keys())
                label_fechas_v6 = "🟢 Fecha Radicado" if hay_fechas_v6 else "Fecha Radicado"
                
                with st.popover(label_fechas_v6, use_container_width=True):
                    cond_a = "1=1"
                    map_a = {'razon_social': 'v6_rs', 'nit': 'v6_nit', 'tipo_contrato': 'v6_tc', 'numero_contrato': 'v6_nc', 'tipo_regimen': 'v6_tr', 'usuario_auditoria_tecnica': 'v6_aud', 'pos': 'v6_pos', 'estado_tecnica': 'v6_est'}
                    for col_db, skey in map_a.items():
                        vals = st.session_state.get(skey, [])
                        if vals:
                            l_vals = [v.replace("'", "''") for v in vals]
                            cond_a += f" AND CAST(\"{col_db}\" AS VARCHAR) IN ('" + "', '".join(l_vals) + "')"
                    try:
                        a_disp = sorted(list(set([str(a) for a in conn.execute(f"SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL AND {cond_a}").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                        if not a_disp:
                            a_disp = sorted(list(set([str(a) for a in conn.execute("SELECT DISTINCT REGEXP_EXTRACT(fecha_radicado, '20[0-9]{2}') as anio FROM facturas WHERE fecha_radicado IS NOT NULL").df()['anio'].dropna().tolist() if a != ''])), reverse=True)
                    except: a_disp = []

                    if not a_disp: st.caption("No hay periodos en la base de datos.")

                    nombres_meses = {'1':'Ene', '2':'Feb', '3':'Mar', '4':'Abr', '5':'May', '6':'Jun', '7':'Jul', '8':'Ago', '9':'Sep', '10':'Oct', '11':'Nov', '12':'Dic'}
                    cond_fechas_sql_v6 = []
                    fechas_pill_v6 = []
                    
                    for anio in a_disp:
                        try:
                            meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%' AND {cond_a}").df()['mes'].dropna().astype(int).tolist()
                            if not meses_reales:
                                meses_reales = conn.execute(f"SELECT DISTINCT COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as mes FROM facturas WHERE fecha_radicado IS NOT NULL AND fecha_radicado LIKE '%{anio}%'").df()['mes'].dropna().astype(int).tolist()
                            meses_lista = [str(m) for m in sorted(meses_reales)]
                        except: meses_lista = []
                            
                        if meses_lista:
                            c_i, c_d = st.columns([1.2, 2.8])
                            with c_i: st.markdown(f"<div style='margin-top:6px; font-weight:700; color:#e2e8f0; font-size:14px;'>📅 {anio}</div>", unsafe_allow_html=True)
                            with c_d:
                                meses_sel = st.multiselect(f"Meses {anio}", options=meses_lista, format_func=lambda x: nombres_meses[x], key=f"v6_meses_{anio}", label_visibility="collapsed")
                            if meses_sel:
                                m_str = ', '.join(meses_sel)
                                cond_fechas_sql_v6.append(f"(fecha_radicado LIKE '%{anio}%' AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) IN ({m_str}))")
                                fechas_pill_v6.append(f"{anio}: {', '.join([nombres_meses[m] for m in meses_sel])}")

            # Fila 2 (TR, AUD, POS, EST, FAC)
            v6_tr = crear_popover_v6(f6_col6, "Tipo Régimen", 'tipo_regimen', "v6_tr")
            v6_aud = crear_popover_v6(f6_col7, "Auditor", 'usuario_auditoria_tecnica', "v6_aud")
            v6_pos = crear_popover_v6(f6_col8, "POS", 'pos', "v6_pos")
            v6_est = crear_popover_v6(f6_col9, "Estado Técnica", 'estado_tecnica', "v6_est")
            
            with f6_col10:
                v6_fac_val = st.session_state.get("v6_fac", "")
                label_fac = "🟢 Factura" if v6_fac_val else "Factura"
                with st.popover(label_fac, use_container_width=True):
                    v6_fac = st.text_input("Factura", key="v6_fac", placeholder="Escribir factura...", label_visibility="collapsed")
            st.write("---")

            # --- 2. VALIDACIÓN Y CONSTRUCCIÓN DE CONSULTA SQL ---
            where_v6 = "1=1"
            def aplicar_filtro_v6(lista, col_name):
                if lista and col_name in columnas_db:
                    limpios = [v.replace("'", "''") for v in lista]
                    return f" AND CAST(\"{col_name}\" AS VARCHAR) IN ('" + "', '".join(limpios) + "')"
                return ""
            
            where_v6 += aplicar_filtro_v6(v6_rs, 'razon_social')
            where_v6 += aplicar_filtro_v6(v6_nit, 'nit')
            where_v6 += aplicar_filtro_v6(v6_tc, 'tipo_contrato')
            where_v6 += aplicar_filtro_v6(v6_nc, 'numero_contrato')
            where_v6 += aplicar_filtro_v6(v6_tr, 'tipo_regimen')
            where_v6 += aplicar_filtro_v6(v6_aud, 'usuario_auditoria_tecnica')
            where_v6 += aplicar_filtro_v6(v6_pos, 'pos')
            where_v6 += aplicar_filtro_v6(v6_est, 'estado_tecnica')
            
            if v6_fac and 'factura' in columnas_db:
                where_v6 += f" AND CAST(factura AS VARCHAR) ILIKE '%{v6_fac.replace('\"', '')}%'"
            if cond_fechas_sql_v6:
                where_v6 += f" AND ({' OR '.join(cond_fechas_sql_v6)})"

            # --- 3. EXTRACCIÓN DE CONTEXTO (RS y NIT) Y RENDERIZADO DE HEADER ---
            rs_pill_v6 = v6_rs
            nit_pill_v6 = v6_nit
            
            if any([v6_rs, v6_nit, v6_nc, v6_fac]):
                try:
                    df_ctx = conn.execute(f"SELECT DISTINCT razon_social, nit FROM facturas WHERE {where_v6} AND razon_social IS NOT NULL LIMIT 4").df()
                    if not df_ctx.empty and len(df_ctx) <= 3:
                        rs_pill_v6 = df_ctx['razon_social'].dropna().astype(str).unique().tolist()
                        nit_pill_v6 = df_ctx['nit'].dropna().astype(str).unique().tolist()
                except: pass

            with header_v6:
                mostrar_pills_filtros({
                    "Razón Social": rs_pill_v6, "NIT": nit_pill_v6, "Tipo Contrato": v6_tc, 
                    "Núm Contrato": v6_nc, "Régimen": v6_tr, "Auditor": v6_aud, "POS": v6_pos, 
                    "Estado Técnica": v6_est, "Periodo": fechas_pill_v6, "Factura": v6_fac
                })

            # --- 4. EXTRACCIÓN DE DATOS Y RENDERIZADO TABLA ESTILO EXCEL ---
            query_v6 = f"""
                SELECT 
                    COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                    COUNT(factura) as "Cuenta de rango factura",
                    SUM(TRY_CAST(valor_factura AS DOUBLE)) as sum_vf,
                    SUM(TRY_CAST(total_glosas AS DOUBLE)) as sum_tg,
                    SUM(TRY_CAST(valor_total_acepta_eps AS DOUBLE)) as sum_eps,
                    SUM(TRY_CAST(valor_total_acepta_ips AS DOUBLE)) as sum_ips
                FROM facturas
                WHERE {where_v6} AND fecha_radicado IS NOT NULL AND fecha_radicado != ''
                GROUP BY num_mes
                HAVING num_mes IS NOT NULL
                ORDER BY num_mes
            """
            
            df_v6 = conn.execute(query_v6).df().fillna(0)
            
            if not df_v6.empty:
                meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                df_v6['fecha_radicado'] = df_v6['num_mes'].map(meses_min)
                
                total_cuenta = df_v6['Cuenta de rango factura'].sum()
                total_vf = df_v6['sum_vf'].sum()
                total_tg = df_v6['sum_tg'].sum()
                total_eps = df_v6['sum_eps'].sum()
                total_ips = df_v6['sum_ips'].sum()
                
                # Base de la tabla
                df_final_v6 = pd.DataFrame({
                    'fecha_radicado': df_v6['fecha_radicado'].tolist() + ['TOTAL GENERAL'],
                    'Cuenta de rango factura': df_v6['Cuenta de rango factura'].tolist() + [total_cuenta],
                    'Suma de valor_factura': df_v6['sum_vf'].tolist() + [total_vf],
                    'Suma de total_glosas': df_v6['sum_tg'].tolist() + [total_tg],
                    'Suma de valor_total_acepta_eps': df_v6['sum_eps'].tolist() + [total_eps],
                    'Suma de valor_total_acepta_ips': df_v6['sum_ips'].tolist() + [total_ips]
                })
                
                # Cálculos de Diferencia
                df_final_v6['Suma de DIFERENCIA'] = df_final_v6['Suma de total_glosas'] - (df_final_v6['Suma de valor_total_acepta_eps'] + df_final_v6['Suma de valor_total_acepta_ips'])
                
                # Cálculos de Porcentajes matemáticos (Controlando División por Cero)
                df_final_v6['%'] = (df_final_v6['Suma de total_glosas'] / df_final_v6['Suma de valor_factura']).fillna(0).replace([float('inf'), -float('inf')], 0)
                df_final_v6['% '] = (df_final_v6['Suma de valor_total_acepta_eps'] / df_final_v6['Suma de total_glosas']).fillna(0).replace([float('inf'), -float('inf')], 0)
                df_final_v6['%  '] = (df_final_v6['Suma de valor_total_acepta_ips'] / df_final_v6['Suma de total_glosas']).fillna(0).replace([float('inf'), -float('inf')], 0)
                
                # 🎯 NUEVO: Porcentaje de la Diferencia
                df_final_v6['%   '] = (df_final_v6['Suma de DIFERENCIA'] / df_final_v6['Suma de total_glosas']).fillna(0).replace([float('inf'), -float('inf')], 0)
                
                # Reordenar columnas exactamente como se solicitó + la nueva de porcentaje
                df_final_v6 = df_final_v6[[
                    'fecha_radicado', 'Cuenta de rango factura', 'Suma de valor_factura', 
                    'Suma de total_glosas', '%', 'Suma de valor_total_acepta_eps', '% ', 
                    'Suma de valor_total_acepta_ips', '%  ', 'Suma de DIFERENCIA', '%   '
                ]]
                
                # Formatear Moneda
                for col in ['Suma de valor_factura', 'Suma de total_glosas', 'Suma de valor_total_acepta_eps', 'Suma de valor_total_acepta_ips', 'Suma de DIFERENCIA']:
                    df_final_v6[col] = df_final_v6[col].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                
                # Formatear Cuenta
                df_final_v6['Cuenta de rango factura'] = df_final_v6['Cuenta de rango factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                
                # Formatear Porcentajes (Ej: 15,2%) agregando el cuarto elemento
                for col in ['%', '% ', '%  ', '%   ']:
                    df_final_v6[col] = df_final_v6[col].apply(lambda x: "0,0%" if x == 0 else f"{x*100:.1f}%".replace('.', ','))
                
                # 🎯 ESTILOS: Rojo para Glosas, Azul para los demás porcentajes
                def resaltar_estilos_v6(row):
                    styles = [''] * len(row)
                    es_total = (row.name == df_final_v6.index[-1])
                    for i, col in enumerate(df_final_v6.columns):
                        if es_total:
                            styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                        elif col == '%': # 🔴 Específicamente el % de Glosa en Rojo
                            styles[i] = 'font-weight: bold; color: #ef4444;' 
                        elif '%' in col: # 🔵 Los demás % en Azul (EPS, IPS, Diferencia)
                            styles[i] = 'font-weight: bold; color: #38bdf8;' 
                    return styles
                
                df_styled_v6 = df_final_v6.style.apply(resaltar_estilos_v6, axis=1)
                altura_tabla = (len(df_final_v6) * 36) + 43
                
                st.dataframe(df_styled_v6, use_container_width=True, hide_index=True, height=altura_tabla)
            else:
                st.info("Sin resultados para los filtros aplicados en esta vista.")

# =========================================================================
    # PANTALLA 5: SEGUIMIENTO OPERATIVO
    # =========================================================================
    elif st.session_state.modulo_activo == "Seguimiento Operativo":
        st.title("Seguimiento Operativo")
        
        # 1. Botón de Nivel de Análisis (Tipo de Seguimiento)
        col_vista, _ = st.columns([2, 8])
        with col_vista:
            tipo_seguimiento = st.selectbox(
                "Tipo de Seguimiento:", 
                ["Productividad", "Pendientes"]
            )
            
        st.write("---")
        
        # 2. Enrutador según el Tipo de Seguimiento
        if tipo_seguimiento == "Pendientes":
            # 7 Vistas para Pendientes
            v_pend_1, v_pend_2, v_pend_3, v_pend_4, v_pend_5, v_pend_6, v_pend_7 = st.tabs([
                "Por Mes", 
                "Por Estado de Factura", 
                "Por Tipo de Contrato", 
                "Por Rango de Factura", 
                "Por Perfil de Auditor",
                "Por Auditor", 
                "Por Radicación"
            ])
            
            with v_pend_1:
                st.markdown("#### 📅 Pendientes por Mes")
                
                try:
                    # 1. Estados válidos
                    cond_pendientes = "(UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('AUDITADO', 'PENDIENTE') OR estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN')"
                    
                    # 2. Query Principal (Ordenado ASCENDENTE para ver lo más antiguo arriba)
                    query_pend1 = f"""
                        SELECT 
                            COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                            COALESCE(YEAR(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), YEAR(TRY_CAST(fecha_radicado AS DATE))) as num_anio,
                            COUNT(factura) as "Cant. Factura",
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as "Valor Factura"
                        FROM facturas
                        WHERE {cond_pendientes} AND fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''
                        GROUP BY num_anio, num_mes
                        HAVING num_mes IS NOT NULL AND num_anio IS NOT NULL
                        ORDER BY num_anio ASC, num_mes ASC
                    """
                    
                    df_pend1 = conn.execute(query_pend1).df().fillna(0)
                    
                    if not df_pend1.empty:
                        meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                        
                        # Asignamos el mes en minúscula como en la Vista 2. 
                        # Solo le pegamos el año si la base de datos detecta facturas de varios años distintos para evitar confusiones.
                        if len(df_pend1['num_anio'].unique()) > 1:
                            df_pend1['Mes'] = df_pend1.apply(lambda row: f"{meses_min[int(row['num_mes'])]} {int(row['num_anio'])}", axis=1)
                        else:
                            df_pend1['Mes'] = df_pend1['num_mes'].apply(lambda x: meses_min[int(x)])
                        
                        total_cant = df_pend1['Cant. Factura'].sum()
                        total_vf = df_pend1['Valor Factura'].sum()
                        
                        # Exactamente 3 columnas solicitadas
                        df_final_pend1 = pd.DataFrame({
                            'Mes': df_pend1['Mes'].tolist() + ['Total general'],
                            'Cant. Factura': df_pend1['Cant. Factura'].tolist() + [total_cant],
                            'Valor Factura': df_pend1['Valor Factura'].tolist() + [total_vf]
                        })
                        
                        # Formateo Visual
                        df_final_pend1['Cant. Factura'] = df_final_pend1['Cant. Factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final_pend1['Valor Factura'] = df_final_pend1['Valor Factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        st.markdown("<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>TOTAL PENDIENTES POR MES</div>", unsafe_allow_html=True)
                        
                        def estilo_pend1(row):
                            styles = [''] * len(row)
                            if row.name == df_final_pend1.index[-1]:
                                for i in range(len(row)):
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                            return styles
                            
                        altura_dinamica = (len(df_final_pend1) * 36) + 43
                        st.dataframe(df_final_pend1.style.apply(estilo_pend1, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica)
                    else:
                        st.info("No hay facturas pendientes registradas.")
                except Exception as e:
                    st.warning(f"Esperando datos válidos... ({e})")
                
            with v_pend_2:
                st.markdown("#### 🏷️ Pendientes por Estado de Factura")
                
                try:
                    # 1. Estados válidos
                    cond_pendientes = "(UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('AUDITADO', 'PENDIENTE') OR estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN')"
                    
                    # 2. Query Principal sin INITCAP
                    query_pend2 = f"""
                        SELECT 
                            COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                            COALESCE(YEAR(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), YEAR(TRY_CAST(fecha_radicado AS DATE))) as num_anio,
                            CASE 
                                WHEN estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN' THEN 'Sin Estado'
                                ELSE TRIM(CAST(estado_tecnica AS VARCHAR))
                            END as estado_tecnica,
                            COUNT(factura) as cant_factura,
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as valor_factura
                        FROM facturas
                        WHERE {cond_pendientes} AND fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''
                        GROUP BY num_anio, num_mes, estado_tecnica
                        HAVING num_mes IS NOT NULL AND num_anio IS NOT NULL
                        ORDER BY num_anio ASC, num_mes ASC, estado_tecnica ASC
                    """
                    
                    df_pend2 = conn.execute(query_pend2).df().fillna(0)
                    
                    if not df_pend2.empty:
                        # 🎯 BLINDAJE: Capitalizar el estado usando Pandas en lugar de DuckDB
                        df_pend2['estado_tecnica'] = df_pend2['estado_tecnica'].astype(str).str.capitalize()
                        
                        meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                        
                        # 3. Construcción de la tabla tipo Pivot / Cascada
                        filas_pivot = []
                        agrupado = df_pend2.groupby(['num_anio', 'num_mes'])
                        
                        total_general_cant = 0
                        total_general_val = 0
                        
                        for (anio, mes), grupo in agrupado:
                            subtotal_cant = grupo['cant_factura'].sum()
                            subtotal_val = grupo['valor_factura'].sum()
                            
                            total_general_cant += subtotal_cant
                            total_general_val += subtotal_val
                            
                            # Fila del Mes (Padre/Subtotal)
                            nombre_mes = meses_min[int(mes)]
                            # Si hay facturas de varios años, pegamos el año para diferenciarlas (ej: "abr 2025")
                            if len(df_pend2['num_anio'].unique()) > 1:
                                nombre_mes += f" {int(anio)}"
                                
                            filas_pivot.append({
                                'Etiquetas de fila': nombre_mes,
                                'Cuenta de factura': subtotal_cant,
                                'Suma de valor_factura': subtotal_val
                            })
                            
                            # Filas de los Estados (Hijos)
                            for _, row in grupo.iterrows():
                                filas_pivot.append({
                                    # Usamos un carácter especial de espacio (U+3164) para forzar la indentación visual en la tabla
                                    'Etiquetas de fila': f"ㅤㅤ{row['estado_tecnica']}", 
                                    'Cuenta de factura': row['cant_factura'],
                                    'Suma de valor_factura': row['valor_factura']
                                })
                                
                        # 4. Fila de Total General
                        filas_pivot.append({
                            'Etiquetas de fila': 'Total general',
                            'Cuenta de factura': total_general_cant,
                            'Suma de valor_factura': total_general_val
                        })
                        
                        df_final_pend2 = pd.DataFrame(filas_pivot)
                        
                        # 5. Formateo Visual
                        df_final_pend2['Cuenta de factura'] = df_final_pend2['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final_pend2['Suma de valor_factura'] = df_final_pend2['Suma de valor_factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        st.markdown("<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>TOTAL PENDIENTE POR ESTADO DE FACTURA</div>", unsafe_allow_html=True)
                        
                        # 6. Estilos Dinámicos: Negrita para meses y Total General
                        def estilo_pend2(row):
                            styles = [''] * len(row)
                            # Es mes o total general si NO empieza con el espacio invisible de indentación que le pusimos a los hijos
                            if not str(row['Etiquetas de fila']).startswith('ㅤㅤ'):
                                for i in range(len(row)):
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.02)'
                                    if row['Etiquetas de fila'] == 'Total general':
                                        styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                            return styles
                            
                        altura_dinamica = (len(df_final_pend2) * 36) + 43
                        st.dataframe(df_final_pend2.style.apply(estilo_pend2, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica)
                    else:
                        st.info("No hay facturas pendientes registradas.")
                except Exception as e:
                    st.warning(f"Esperando datos válidos... ({e})")
                
            with v_pend_3:
                st.markdown("#### 📄 Pendientes por Tipo de Contrato")
                
                try:
                    # 1. Estados válidos
                    cond_pendientes = "(UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('AUDITADO', 'PENDIENTE') OR estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN')"
                    
                    # 2. Query Principal (Agrupado por Año, Mes y Tipo de Contrato, ordenando los contratos de mayor a menor valor)
                    query_pend3 = f"""
                        SELECT 
                            COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                            COALESCE(YEAR(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), YEAR(TRY_CAST(fecha_radicado AS DATE))) as num_anio,
                            CASE 
                                WHEN tipo_contrato IS NULL OR TRIM(CAST(tipo_contrato AS VARCHAR)) = '' OR UPPER(TRIM(CAST(tipo_contrato AS VARCHAR))) = 'NAN' THEN 'Sin Contrato'
                                ELSE TRIM(CAST(tipo_contrato AS VARCHAR))
                            END as tipo_contrato,
                            COUNT(factura) as cant_factura,
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as valor_factura
                        FROM facturas
                        WHERE {cond_pendientes} AND fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''
                        GROUP BY num_anio, num_mes, tipo_contrato
                        HAVING num_mes IS NOT NULL AND num_anio IS NOT NULL
                        ORDER BY num_anio ASC, num_mes ASC, valor_factura DESC
                    """
                    
                    df_pend3 = conn.execute(query_pend3).df().fillna(0)
                    
                    if not df_pend3.empty:
                        meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                        
                        # 3. Construcción de la tabla tipo Pivot / Cascada
                        filas_pivot = []
                        
                        # sort=False asegura que Pandas respete el orden DESCENDENTE de los contratos que ya traemos del SQL
                        agrupado = df_pend3.groupby(['num_anio', 'num_mes'], sort=False)
                        
                        total_general_cant = 0
                        total_general_val = 0
                        
                        for (anio, mes), grupo in agrupado:
                            subtotal_cant = grupo['cant_factura'].sum()
                            subtotal_val = grupo['valor_factura'].sum()
                            
                            total_general_cant += subtotal_cant
                            total_general_val += subtotal_val
                            
                            # Fila del Mes (Padre/Subtotal)
                            nombre_mes = meses_min[int(mes)]
                            if len(df_pend3['num_anio'].unique()) > 1:
                                nombre_mes += f" {int(anio)}"
                                
                            filas_pivot.append({
                                'Etiquetas de fila': nombre_mes,
                                'Cuenta de factura': subtotal_cant,
                                'Suma de valor_factura': subtotal_val
                            })
                            
                            # Filas de los Contratos (Hijos)
                            for _, row in grupo.iterrows():
                                filas_pivot.append({
                                    # Espacio invisible (U+3164) para forzar la indentación visual
                                    'Etiquetas de fila': f"ㅤㅤ{row['tipo_contrato']}", 
                                    'Cuenta de factura': row['cant_factura'],
                                    'Suma de valor_factura': row['valor_factura']
                                })
                                
                        # 4. Fila de Total General
                        filas_pivot.append({
                            'Etiquetas de fila': 'Total general',
                            'Cuenta de factura': total_general_cant,
                            'Suma de valor_factura': total_general_val
                        })
                        
                        df_final_pend3 = pd.DataFrame(filas_pivot)
                        
                        # 5. Formateo Visual
                        df_final_pend3['Cuenta de factura'] = df_final_pend3['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final_pend3['Suma de valor_factura'] = df_final_pend3['Suma de valor_factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        st.markdown("<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>TOTAL PENDIENTE POR TIPO DE CONTRATO</div>", unsafe_allow_html=True)
                        
                        # 6. Estilos Dinámicos: Negrita para meses y Total General
                        def estilo_pend3(row):
                            styles = [''] * len(row)
                            # Identificamos a los "padres" asegurándonos que no empiecen con el espacio de indentación
                            if not str(row['Etiquetas de fila']).startswith('ㅤㅤ'):
                                for i in range(len(row)):
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.02)'
                                    if row['Etiquetas de fila'] == 'Total general':
                                        styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                            return styles
                            
                        altura_dinamica = (len(df_final_pend3) * 36) + 43
                        st.dataframe(df_final_pend3.style.apply(estilo_pend3, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica)
                    else:
                        st.info("No hay facturas pendientes registradas.")
                except Exception as e:
                    st.warning(f"Esperando datos válidos... ({e})")
                
            with v_pend_4:
                st.markdown("#### 💰 Pendientes por Rango de Factura")
                
                try:
                    # 1. Estados válidos
                    cond_pendientes = "(UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('AUDITADO', 'PENDIENTE') OR estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN')"
                    
                    # 2. Query Principal (Agrupado por Año, Mes y Rango de Factura, ordenando por valor de mayor a menor)
                    query_pend4 = f"""
                        SELECT 
                            COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                            COALESCE(YEAR(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), YEAR(TRY_CAST(fecha_radicado AS DATE))) as num_anio,
                            CASE 
                                WHEN rango_factura IS NULL OR TRIM(CAST(rango_factura AS VARCHAR)) = '' OR UPPER(TRIM(CAST(rango_factura AS VARCHAR))) = 'NAN' THEN 'Sin Rango'
                                ELSE TRIM(CAST(rango_factura AS VARCHAR))
                            END as rango_factura,
                            COUNT(factura) as cant_factura,
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as valor_factura
                        FROM facturas
                        WHERE {cond_pendientes} AND fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''
                        GROUP BY num_anio, num_mes, rango_factura
                        HAVING num_mes IS NOT NULL AND num_anio IS NOT NULL
                        ORDER BY num_anio ASC, num_mes ASC, valor_factura DESC
                    """
                    
                    df_pend4 = conn.execute(query_pend4).df().fillna(0)
                    
                    if not df_pend4.empty:
                        meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                        
                        # 3. Construcción de la tabla tipo Pivot / Cascada
                        filas_pivot = []
                        
                        # sort=False para respetar el orden descendente de la consulta SQL
                        agrupado = df_pend4.groupby(['num_anio', 'num_mes'], sort=False)
                        
                        total_general_cant = 0
                        total_general_val = 0
                        
                        for (anio, mes), grupo in agrupado:
                            subtotal_cant = grupo['cant_factura'].sum()
                            subtotal_val = grupo['valor_factura'].sum()
                            
                            total_general_cant += subtotal_cant
                            total_general_val += subtotal_val
                            
                            # Fila del Mes (Padre/Subtotal)
                            nombre_mes = meses_min[int(mes)]
                            if len(df_pend4['num_anio'].unique()) > 1:
                                nombre_mes += f" {int(anio)}"
                                
                            filas_pivot.append({
                                'Etiquetas de fila': nombre_mes,
                                'Cuenta de factura': subtotal_cant,
                                'Suma de valor_factura': subtotal_val
                            })
                            
                            # Filas de los Rangos (Hijos)
                            for _, row in grupo.iterrows():
                                filas_pivot.append({
                                    # Espacio invisible (U+3164) para forzar la indentación visual
                                    'Etiquetas de fila': f"ㅤㅤ{row['rango_factura']}", 
                                    'Cuenta de factura': row['cant_factura'],
                                    'Suma de valor_factura': row['valor_factura']
                                })
                                
                        # 4. Fila de Total General
                        filas_pivot.append({
                            'Etiquetas de fila': 'Total general',
                            'Cuenta de factura': total_general_cant,
                            'Suma de valor_factura': total_general_val
                        })
                        
                        df_final_pend4 = pd.DataFrame(filas_pivot)
                        
                        # 5. Formateo Visual
                        df_final_pend4['Cuenta de factura'] = df_final_pend4['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final_pend4['Suma de valor_factura'] = df_final_pend4['Suma de valor_factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        st.markdown("<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>TOTAL PENDIENTE POR RANGO DE FACTURA</div>", unsafe_allow_html=True)
                        
                        # 6. Estilos Dinámicos: Negrita para meses y Total General
                        def estilo_pend4(row):
                            styles = [''] * len(row)
                            # Identificamos a los "padres" asegurándonos que no empiecen con el espacio de indentación
                            if not str(row['Etiquetas de fila']).startswith('ㅤㅤ'):
                                for i in range(len(row)):
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.02)'
                                    if row['Etiquetas de fila'] == 'Total general':
                                        styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                            return styles
                            
                        altura_dinamica = (len(df_final_pend4) * 36) + 43
                        st.dataframe(df_final_pend4.style.apply(estilo_pend4, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica)
                    else:
                        st.info("No hay facturas pendientes registradas.")
                except Exception as e:
                    st.warning(f"Esperando datos válidos... ({e})")
                
            with v_pend_5:
                st.markdown("#### 👤 Pendientes por Perfil de Auditor")
                
                try:
                    # 1. Estados válidos
                    cond_pendientes = "(UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('AUDITADO', 'PENDIENTE') OR estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN')"
                    
                    # 2. Query Principal (Agrupado por Año, Mes y Perfil, ordenando por valor de mayor a menor)
                    query_pend5 = f"""
                        SELECT 
                            COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                            COALESCE(YEAR(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), YEAR(TRY_CAST(fecha_radicado AS DATE))) as num_anio,
                            CASE 
                                WHEN perfil_auditor IS NULL OR TRIM(CAST(perfil_auditor AS VARCHAR)) = '' OR UPPER(TRIM(CAST(perfil_auditor AS VARCHAR))) = 'NAN' THEN 'Sin Perfil'
                                ELSE TRIM(CAST(perfil_auditor AS VARCHAR))
                            END as perfil_auditor,
                            COUNT(factura) as cant_factura,
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as valor_factura
                        FROM facturas
                        WHERE {cond_pendientes} AND fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''
                        GROUP BY num_anio, num_mes, perfil_auditor
                        HAVING num_mes IS NOT NULL AND num_anio IS NOT NULL
                        ORDER BY num_anio ASC, num_mes ASC, valor_factura DESC
                    """
                    
                    df_pend5 = conn.execute(query_pend5).df().fillna(0)
                    
                    if not df_pend5.empty:
                        meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                        
                        # 3. Construcción de la tabla tipo Pivot / Cascada
                        filas_pivot = []
                        
                        # sort=False para respetar el orden descendente de los perfiles que ya traemos del SQL
                        agrupado = df_pend5.groupby(['num_anio', 'num_mes'], sort=False)
                        
                        total_general_cant = 0
                        total_general_val = 0
                        
                        for (anio, mes), grupo in agrupado:
                            subtotal_cant = grupo['cant_factura'].sum()
                            subtotal_val = grupo['valor_factura'].sum()
                            
                            total_general_cant += subtotal_cant
                            total_general_val += subtotal_val
                            
                            # Fila del Mes (Padre/Subtotal)
                            nombre_mes = meses_min[int(mes)]
                            if len(df_pend5['num_anio'].unique()) > 1:
                                nombre_mes += f" {int(anio)}"
                                
                            filas_pivot.append({
                                'Etiquetas de fila': nombre_mes,
                                'Cuenta de factura': subtotal_cant,
                                'Suma de valor_factura': subtotal_val
                            })
                            
                            # Filas de los Perfiles (Hijos)
                            for _, row in grupo.iterrows():
                                filas_pivot.append({
                                    # Espacio invisible (U+3164) para forzar la indentación visual
                                    'Etiquetas de fila': f"ㅤㅤ{row['perfil_auditor']}", 
                                    'Cuenta de factura': row['cant_factura'],
                                    'Suma de valor_factura': row['valor_factura']
                                })
                                
                        # 4. Fila de Total General
                        filas_pivot.append({
                            'Etiquetas de fila': 'Total general',
                            'Cuenta de factura': total_general_cant,
                            'Suma de valor_factura': total_general_val
                        })
                        
                        df_final_pend5 = pd.DataFrame(filas_pivot)
                        
                        # 5. Formateo Visual
                        df_final_pend5['Cuenta de factura'] = df_final_pend5['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final_pend5['Suma de valor_factura'] = df_final_pend5['Suma de valor_factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        st.markdown("<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>TOTAL PENDIENTE POR PERFIL DE AUDITOR</div>", unsafe_allow_html=True)
                        
                        # 6. Estilos Dinámicos: Negrita para meses y Total General
                        def estilo_pend5(row):
                            styles = [''] * len(row)
                            # Identificamos a los "padres" asegurándonos que no empiecen con el espacio de indentación
                            if not str(row['Etiquetas de fila']).startswith('ㅤㅤ'):
                                for i in range(len(row)):
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.02)'
                                    if row['Etiquetas de fila'] == 'Total general':
                                        styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                            return styles
                            
                        altura_dinamica = (len(df_final_pend5) * 36) + 43
                        st.dataframe(df_final_pend5.style.apply(estilo_pend5, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica)
                    else:
                        st.info("No hay facturas pendientes registradas.")
                except Exception as e:
                    st.warning(f"Esperando datos válidos... ({e})")

            with v_pend_6:
                st.markdown("#### 🧑‍💻 Pendientes por Auditor")
                
                try:
                    # 1. Estados válidos
                    cond_pendientes = "(UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('AUDITADO', 'PENDIENTE') OR estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN')"
                    
                    # 2. Query Principal (Agrupado por Año, Mes, Perfil y Auditor)
                    query_pend6 = f"""
                        SELECT 
                            COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes,
                            COALESCE(YEAR(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), YEAR(TRY_CAST(fecha_radicado AS DATE))) as num_anio,
                            CASE 
                                WHEN perfil_auditor IS NULL OR TRIM(CAST(perfil_auditor AS VARCHAR)) = '' OR UPPER(TRIM(CAST(perfil_auditor AS VARCHAR))) = 'NAN' THEN 'Sin Perfil'
                                ELSE TRIM(CAST(perfil_auditor AS VARCHAR))
                            END as perfil_auditor,
                            CASE 
                                WHEN usuario_auditoria_tecnica IS NULL OR TRIM(CAST(usuario_auditoria_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(usuario_auditoria_tecnica AS VARCHAR))) = 'NAN' THEN 'Sin Asignar'
                                ELSE TRIM(CAST(usuario_auditoria_tecnica AS VARCHAR))
                            END as auditor,
                            COUNT(factura) as cant_factura,
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as valor_factura
                        FROM facturas
                        WHERE {cond_pendientes} AND fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''
                        GROUP BY num_anio, num_mes, perfil_auditor, auditor
                        HAVING num_mes IS NOT NULL AND num_anio IS NOT NULL
                        ORDER BY num_anio ASC, num_mes ASC
                    """
                    
                    df_pend6 = conn.execute(query_pend6).df().fillna(0)
                    
                    if not df_pend6.empty:
                        meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                        
                        filas_pivot = []
                        agrupado_mes = df_pend6.groupby(['num_anio', 'num_mes'], sort=False)
                        
                        total_general_cant = 0
                        total_general_val = 0
                        
                        # 3. Triple iteración: MES -> PERFIL -> AUDITOR
                        for (anio, mes), grupo_mes in agrupado_mes:
                            subtotal_mes_cant = grupo_mes['cant_factura'].sum()
                            subtotal_mes_val = grupo_mes['valor_factura'].sum()
                            
                            total_general_cant += subtotal_mes_cant
                            total_general_val += subtotal_mes_val
                            
                            nombre_mes = meses_min[int(mes)]
                            if len(df_pend6['num_anio'].unique()) > 1:
                                nombre_mes += f" {int(anio)}"
                                
                            # (Nivel 1) Fila del Mes
                            filas_pivot.append({
                                'Etiquetas de fila': nombre_mes,
                                'Cuenta de factura': subtotal_mes_cant,
                                'Suma de valor_factura': subtotal_mes_val,
                                'nivel': 1
                            })
                            
                            # Agrupar por Perfiles ordenados por valor descendente
                            perfiles = grupo_mes.groupby('perfil_auditor')['valor_factura'].sum().sort_values(ascending=False).index
                            
                            for perfil in perfiles:
                                grupo_perfil = grupo_mes[grupo_mes['perfil_auditor'] == perfil].sort_values(by='valor_factura', ascending=False)
                                subtotal_perf_cant = grupo_perfil['cant_factura'].sum()
                                subtotal_perf_val = grupo_perfil['valor_factura'].sum()
                                
                                # (Nivel 2) Fila del Perfil (Indentado 1 vez)
                                filas_pivot.append({
                                    'Etiquetas de fila': f"ㅤ {perfil}", 
                                    'Cuenta de factura': subtotal_perf_cant,
                                    'Suma de valor_factura': subtotal_perf_val,
                                    'nivel': 2
                                })
                                
                                # (Nivel 3) Filas de Auditores (Indentado 2 veces)
                                for _, row in grupo_perfil.iterrows():
                                    aud_name = str(row['auditor']).lower()
                                    filas_pivot.append({
                                        'Etiquetas de fila': f"ㅤㅤㅤ {aud_name}", 
                                        'Cuenta de factura': row['cant_factura'],
                                        'Suma de valor_factura': row['valor_factura'],
                                        'nivel': 3
                                    })
                                    
                        # Fila de Total General
                        filas_pivot.append({
                            'Etiquetas de fila': 'Total general',
                            'Cuenta de factura': total_general_cant,
                            'Suma de valor_factura': total_general_val,
                            'nivel': 1
                        })
                        
                        df_final_pend6 = pd.DataFrame(filas_pivot)
                        
                        # Extraemos los niveles para los estilos antes de borrarlos
                        niveles_mask = df_final_pend6['nivel'].tolist()
                        df_final_pend6 = df_final_pend6.drop(columns=['nivel'])
                        
                        # 4. Formateo Visual
                        df_final_pend6['Cuenta de factura'] = df_final_pend6['Cuenta de factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final_pend6['Suma de valor_factura'] = df_final_pend6['Suma de valor_factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        st.markdown("<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>TOTAL PENDIENTE POR AUDITOR</div>", unsafe_allow_html=True)
                        
                        # 5. Estilos: Niveles 1 y 2 en negrita (Meses y Perfiles), Nivel 3 normal (Auditores)
                        def estilo_pend6(row):
                            styles = [''] * len(row)
                            idx = row.name
                            if niveles_mask[idx] in [1, 2]:
                                for i in range(len(row)):
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.02)'
                                    if str(row['Etiquetas de fila']) == 'Total general':
                                        styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                            return styles
                            
                        altura_dinamica = (len(df_final_pend6) * 36) + 43
                        st.dataframe(df_final_pend6.style.apply(estilo_pend6, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica)
                    else:
                        st.info("No hay facturas pendientes registradas.")
                except Exception as e:
                    st.warning(f"Esperando datos válidos... ({e})")        
    
            with v_pend_7:
                st.markdown("#### 📦 Estado de Auditoría por Radicación")
                
                try:
                    # 1. Filtros de Año y Mes (Obligatorios para esta vista)
                    query_fechas = "SELECT DISTINCT fecha_radicado FROM facturas WHERE fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''"
                    df_fechas = conn.execute(query_fechas).df()
                    
                    # Leemos fechas dinámicamente para extraer los periodos reales de tu base
                    df_fechas['fecha_dt'] = pd.to_datetime(df_fechas['fecha_radicado'], format='%d/%m/%Y', errors='coerce')
                    df_fechas = df_fechas.dropna(subset=['fecha_dt'])
                    
                    anios_disp = sorted(df_fechas['fecha_dt'].dt.year.astype(int).unique().tolist(), reverse=True)
                    
                    if not anios_disp:
                        st.info("No hay fechas de radicación válidas para generar este reporte.")
                    else:
                        c_anio, c_mes, _ = st.columns([2, 2, 6])
                        
                        with c_anio:
                            anio_sel = st.selectbox("Año de Radicación:", anios_disp, key="vp6_anio")
                        
                        meses_reales = sorted(df_fechas[df_fechas['fecha_dt'].dt.year == anio_sel]['fecha_dt'].dt.month.astype(int).unique().tolist())
                        meses_nombres = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
                        
                        with c_mes:
                            mes_sel = st.selectbox("Mes de Radicación:", meses_reales, format_func=lambda x: meses_nombres[x], key="vp6_mes")
                            
                        st.write("---")
                        
                        # Título dinámico para la columna combinada principal
                        nombre_mes_columna = f"TOTAL RADICADO {meses_nombres[mes_sel].upper()}"
                        
                        # 2. MEGA QUERY: Cruzando Radicados, Ejecutados y Pendientes
                        query_v6 = f"""
                            SELECT 
                                CASE 
                                    WHEN perfil_auditor IS NULL OR TRIM(CAST(perfil_auditor AS VARCHAR)) = '' OR UPPER(TRIM(CAST(perfil_auditor AS VARCHAR))) = 'NAN' THEN 'Sin Perfil'
                                    ELSE TRIM(CAST(perfil_auditor AS VARCHAR))
                                END as perfil,
                                CASE 
                                    WHEN usuario_auditoria_tecnica IS NULL OR TRIM(CAST(usuario_auditoria_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(usuario_auditoria_tecnica AS VARCHAR))) = 'NAN' THEN 'Sin Asignar'
                                    ELSE TRIM(CAST(usuario_auditoria_tecnica AS VARCHAR))
                                END as auditor,
                                
                                -- Radicados (TODO lo que entró en ese mes)
                                COUNT(factura) as cant_rad,
                                SUM(TRY_CAST(valor_factura AS DOUBLE)) as val_rad,
                                
                                -- Ejecutados (Solo CERRADO y NOTIFICADO)
                                COUNT(CASE WHEN UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('CERRADO', 'NOTIFICADO') THEN factura END) as cant_ejec,
                                SUM(CASE WHEN UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('CERRADO', 'NOTIFICADO') THEN TRY_CAST(valor_factura AS DOUBLE) ELSE 0 END) as val_ejec,
                                
                                -- Pendientes (PENDIENTE, AUDITADO o vacíos)
                                COUNT(CASE WHEN UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('AUDITADO', 'PENDIENTE') OR estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN' THEN factura END) as cant_pend,
                                SUM(CASE WHEN UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) IN ('AUDITADO', 'PENDIENTE') OR estado_tecnica IS NULL OR TRIM(CAST(estado_tecnica AS VARCHAR)) = '' OR UPPER(TRIM(CAST(estado_tecnica AS VARCHAR))) = 'NAN' THEN TRY_CAST(valor_factura AS DOUBLE) ELSE 0 END) as val_pend

                            FROM facturas
                            WHERE 
                                fecha_radicado IS NOT NULL 
                                AND fecha_radicado LIKE '%{anio_sel}%'
                                AND COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) = {mes_sel}
                            GROUP BY perfil, auditor
                        """
                        
                        df_v6 = conn.execute(query_v6).df().fillna(0)
                        
                        if not df_v6.empty:
                            filas_pivot = []
                            # Ordenamos perfiles de mayor a menor carga de trabajo (cantidad radicada)
                            perfiles = df_v6.groupby('perfil')['cant_rad'].sum().sort_values(ascending=False).index
                            
                            tot_r_c, tot_r_v = 0, 0
                            tot_e_c, tot_e_v = 0, 0
                            tot_p_c, tot_p_v = 0, 0
                            
                            # 3. Ensamblando la estructura Padre (Perfiles) e Hijos (Auditores)
                            for p in perfiles:
                                grupo = df_v6[df_v6['perfil'] == p].sort_values(by='cant_rad', ascending=False)
                                
                                # Sumas del Perfil Completo
                                p_r_c = grupo['cant_rad'].sum()
                                p_r_v = grupo['val_rad'].sum()
                                p_e_c = grupo['cant_ejec'].sum()
                                p_e_v = grupo['val_ejec'].sum()
                                p_p_c = grupo['cant_pend'].sum()
                                p_p_v = grupo['val_pend'].sum()
                                
                                # Acumulado para el Total General
                                tot_r_c += p_r_c
                                tot_r_v += p_r_v
                                tot_e_c += p_e_c
                                tot_e_v += p_e_v
                                tot_p_c += p_p_c
                                tot_p_v += p_p_v
                                
                                # Ejecución: Facturas ejecutadas / Facturas radicadas
                                p_pct = (p_e_c / p_r_c) if p_r_c > 0 else 0
                                
                                # Insertar fila PADRE
                                filas_pivot.append({
                                    'auditor': p,
                                    'r_c': p_r_c, 'r_v': p_r_v,
                                    'e_c': p_e_c, 'e_v': p_e_v,
                                    'p_c': p_p_c, 'p_v': p_p_v,
                                    'pct': p_pct,
                                    'es_padre': True
                                })
                                
                                # Insertar filas HIJOS
                                for _, row in grupo.iterrows():
                                    r_pct = (row['cant_ejec'] / row['cant_rad']) if row['cant_rad'] > 0 else 0
                                    filas_pivot.append({
                                        'auditor': f"ㅤㅤ{str(row['auditor']).lower()}", # Espacio invisible para indentar
                                        'r_c': row['cant_rad'], 'r_v': row['val_rad'],
                                        'e_c': row['cant_ejec'], 'e_v': row['val_ejec'],
                                        'p_c': row['cant_pend'], 'p_v': row['val_pend'],
                                        'pct': r_pct,
                                        'es_padre': False
                                    })
                            
                            # Insertar TOTAL GENERAL
                            t_pct = (tot_e_c / tot_r_c) if tot_r_c > 0 else 0
                            filas_pivot.append({
                                'auditor': 'Total general',
                                'r_c': tot_r_c, 'r_v': tot_r_v,
                                'e_c': tot_e_c, 'e_v': tot_e_v,
                                'p_c': tot_p_c, 'p_v': tot_p_v,
                                'pct': t_pct,
                                'es_padre': True
                            })
                            
                            df_final = pd.DataFrame(filas_pivot)
                            
                            # 4. Formateo Numérico Visual Estricto
                            for c in ['r_c', 'e_c', 'p_c']:
                                df_final[c] = df_final[c].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                            for v in ['r_v', 'e_v', 'p_v']:
                                df_final[v] = df_final[v].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                                
                            df_final['pct'] = df_final['pct'].apply(lambda x: "0,0%" if x == 0 else f"{x*100:.1f}%".replace('.', ','))
                            
                            # 5. CREACIÓN DE ENCABEZADOS COMBINADOS (MultiIndex nativo)
                            multi_cols = pd.MultiIndex.from_tuples([
                                (nombre_mes_columna, 'Auditor/Gestor'),
                                (nombre_mes_columna, 'Cant. factura'),
                                (nombre_mes_columna, 'Valor factura'),
                                ('TOTAL EJECUTADO', 'Cant. factura'),
                                ('TOTAL EJECUTADO', 'Valor factura'),
                                ('TOTAL PENDIENTE POR AUDITAR', 'Cant. factura'),
                                ('TOTAL PENDIENTE POR AUDITAR', 'Valor factura'),
                                ('EJECUCIÓN', '% Ejecución')
                            ])
                            
                            # Filtramos las columnas del sistema y asignamos el encabezado combinado
                            es_padre_mask = df_final['es_padre'].tolist()
                            df_display = df_final[['auditor', 'r_c', 'r_v', 'e_c', 'e_v', 'p_c', 'p_v', 'pct']]
                            df_display.columns = multi_cols
                            
                            # 6. Renderizado e Inyección de Estilos
                            st.markdown(f"<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>REPORTE DE ESTADO DE AUDITORÍA</div>", unsafe_allow_html=True)
                            
                            def estilo_v6(row):
                                styles = [''] * len(row)
                                idx = row.name
                                es_padre = es_padre_mask[idx]
                                
                                for i, col in enumerate(df_display.columns):
                                    if es_padre:
                                        # Estilo para la fila del perfil (Padre) o Total General
                                        styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                                        # Pintar la columna de porcentaje en rojo pero manteniendo el fondo oscuro y negrita
                                        if col[1] == '% Ejecución':
                                            styles[i] = 'font-weight: bold; color: #ef4444; background-color: rgba(255,255,255,0.05)'
                                    else:
                                        # Estilo para los Auditores (Hijos)
                                        if col[1] == '% Ejecución':
                                            styles[i] = 'font-weight: bold; color: #ef4444;'
                                            
                                return styles
                                
                            altura = (len(df_display) * 36) + 75
                            
                            # 🎯 APLICAMOS LOS ESTILOS AL DATAFRAME Y FORZAMOS EL CENTRADO DE ENCABEZADOS
                            df_styled = df_display.style.apply(estilo_v6, axis=1).set_table_styles([
                                dict(selector="th", props=[("text-align", "center")]),
                                dict(selector="th.col_heading", props=[("text-align", "center")])
                            ])
                            
                            st.dataframe(df_styled, use_container_width=True, hide_index=True, height=altura)
                            
                        else:
                            st.info(f"No hay facturas radicadas en el mes de {meses_nombres[mes_sel]} del año {anio_sel}.")
                            
                except Exception as e:
                    st.warning(f"Esperando datos válidos... ({e})")

        elif tipo_seguimiento == "Productividad":
            # 5 Vistas para Productividad
            v_prod_1, v_prod_2, v_prod_3, v_prod_4, v_prod_5 = st.tabs([
                "Total Ejecutado Diario", 
                "Ejecutado por Fecha de Radicación", 
                "Por Tipo de Contrato", 
                "Por Rango de Valores", 
                "Por Perfil de Auditor"
            ])
            
            with v_prod_1:
                st.markdown("#### 📈 Total Ejecutado Diario")
                
                # 1. Extracción de Fechas Únicas y Auditores para los filtros (Basado en la fecha de CIERRE y ESTADO)
                try:
                    # 🎯 REQUERIMIENTO: Solo estados Cerrado y Notificado
                    cond_estado = "UPPER(CAST(estado_tecnica AS VARCHAR)) IN ('CERRADO', 'NOTIFICADO')"
                    
                    # 🎯 Extraer lista de Auditores válidos
                    query_aud = f"SELECT DISTINCT usuario_auditoria_tecnica FROM facturas WHERE fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    df_aud_list = conn.execute(query_aud).df()['usuario_auditoria_tecnica'].dropna().astype(str).unique().tolist()
                    auditores_disp = sorted([x for x in df_aud_list if x.strip() != ''])

                    # 🎯 Extraer fechas válidas
                    query_fechas = f"SELECT DISTINCT fecha_cierre_auditoria_tecnica FROM facturas WHERE fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    df_f = conn.execute(query_fechas).df()
                    df_f['fecha_dt'] = pd.to_datetime(df_f['fecha_cierre_auditoria_tecnica'], format='%d/%m/%Y', errors='coerce')
                    df_f = df_f.dropna(subset=['fecha_dt'])
                    
                    # 🎯 Añadimos el filtro de Auditor al layout
                    c_aud, c_anio, c_mes, c_dia, _ = st.columns([2.5, 1.5, 1.5, 1.5, 3])
                    
                    with c_aud:
                        auditor_sel = st.selectbox("Auditor/Gestor", ["Todos"] + auditores_disp, key="prod_1_aud")

                    anios_disp = sorted(df_f['fecha_dt'].dt.year.astype(int).unique().tolist(), reverse=True)
                    with c_anio:
                        anio_sel = st.selectbox("Año", ["Todos"] + anios_disp, key="prod_1_anio")
                    
                    meses_disp = []
                    if anio_sel != "Todos":
                        meses_disp = sorted(df_f[df_f['fecha_dt'].dt.year == anio_sel]['fecha_dt'].dt.month.astype(int).unique().tolist())
                    with c_mes:
                        mes_sel = st.selectbox("Mes", ["Todos"] + meses_disp, key="prod_1_mes", disabled=(anio_sel == "Todos"))
                    
                    dias_disp = []
                    if mes_sel != "Todos" and anio_sel != "Todos":
                        dias_disp = sorted(df_f[(df_f['fecha_dt'].dt.year == anio_sel) & (df_f['fecha_dt'].dt.month == mes_sel)]['fecha_dt'].dt.day.astype(int).unique().tolist())
                    with c_dia:
                        dia_sel = st.selectbox("Día", ["Todos"] + dias_disp, key="prod_1_dia", disabled=(mes_sel == "Todos"))
                    
                    st.write("---")
                    
                    # 2. Construir condicional SQL cruzado para la tabla y la gráfica
                    where_p1 = f"fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    fecha_titulo = ""
                    
                    if auditor_sel != "Todos":
                        where_p1 += f" AND CAST(usuario_auditoria_tecnica AS VARCHAR) = '{auditor_sel}'"

                    if anio_sel != "Todos":
                        where_p1 += f" AND fecha_cierre_auditoria_tecnica LIKE '%{anio_sel}'" 
                        fecha_titulo = str(anio_sel)
                    if mes_sel != "Todos":
                        mes_str = f"{mes_sel:02d}"
                        where_p1 += f" AND fecha_cierre_auditoria_tecnica LIKE '%/{mes_str}/%'"
                        fecha_titulo = f"{mes_str}/{anio_sel}"
                    if dia_sel != "Todos":
                        dia_str = f"{dia_sel:02d}"
                        where_p1 += f" AND fecha_cierre_auditoria_tecnica LIKE '{dia_str}/%'"
                        fecha_titulo = f"{dia_str}/{mes_str}/{anio_sel}"
                    
                    # 3. Ejecutar Query Principal de Productividad (Para la Tabla)
                    query_p1 = f"""
                        SELECT 
                            COALESCE(CAST(usuario_auditoria_tecnica AS VARCHAR), 'SIN ASIGNAR') as "Auditor",
                            COUNT(factura) as "Cant. Factura",
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as "Valor Factura",
                            SUM(TRY_CAST(total_glosas AS DOUBLE)) as "Total Glosa"
                        FROM facturas
                        WHERE {where_p1}
                        GROUP BY usuario_auditoria_tecnica
                        ORDER BY "Valor Factura" DESC
                    """
                    
                    df_p1 = conn.execute(query_p1).df().fillna(0)
                    
                    if not df_p1.empty:
                        # 4. Cálculos Matemáticos y Fila de Totales
                        total_cant = df_p1['Cant. Factura'].sum()
                        total_vf = df_p1['Valor Factura'].sum()
                        total_tg = df_p1['Total Glosa'].sum()
                        
                        df_final = pd.DataFrame({
                            'Auditor': df_p1['Auditor'].tolist() + ['Total general'],
                            'Cant. Factura': df_p1['Cant. Factura'].tolist() + [total_cant],
                            'Valor Factura': df_p1['Valor Factura'].tolist() + [total_vf],
                            'Total Glosa': df_p1['Total Glosa'].tolist() + [total_tg]
                        })
                        
                        # Porcentaje seguro contra división por cero
                        df_final['%'] = (df_final['Total Glosa'] / df_final['Valor Factura']).fillna(0).replace([float('inf'), -float('inf')], 0)
                        
                        # 5. Formateo Visual
                        df_final['Cant. Factura'] = df_final['Cant. Factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final['Valor Factura'] = df_final['Valor Factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        df_final['Total Glosa'] = df_final['Total Glosa'].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        # Porcentaje con 1 decimal y coma
                        df_final['%'] = df_final['%'].apply(lambda x: "0,0%" if x == 0 else f"{x*100:.1f}%".replace('.', ','))
                        
                        # 6. Renderizado de la Tabla (Header oscuro con borde sutil)
                        tit_text = f"TOTAL EJECUTADO {fecha_titulo}" if fecha_titulo else "TOTAL EJECUTADO GENERAL"
                        st.markdown(f"<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>{tit_text.upper()}</div>", unsafe_allow_html=True)
                        
                        def estilo_prod1(row):
                            styles = [''] * len(row)
                            es_total = (row.name == df_final.index[-1])
                            for i, col in enumerate(df_final.columns):
                                if es_total:
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                                    if col == '%': 
                                        styles[i] = 'font-weight: bold; color: #ef4444; background-color: rgba(255,255,255,0.05)' 
                                elif col == '%': 
                                    styles[i] = 'font-weight: bold; color: #ef4444;' 
                            return styles
                        
                        altura_dinamica = (len(df_final) * 36) + 43
                        st.dataframe(df_final.style.apply(estilo_prod1, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica)

                        # --- 7. GRÁFICA DE TENDENCIA (SOLO SI SE SELECCIONA UN AUDITOR) ---
                        if auditor_sel != "Todos":
                            st.write("")
                            st.markdown(f"#### 📉 Tendencia Diaria: {auditor_sel}")
                            
                            # 🎯 CORRECCIÓN: Nombres de columnas SIN puntos para que Altair no colapse
                            query_chart = f"""
                                SELECT 
                                    fecha_cierre_auditoria_tecnica as fecha_str,
                                    COUNT(factura) as cantidad_facturas,
                                    SUM(TRY_CAST(valor_factura AS DOUBLE)) as valor_gestionado
                                FROM facturas
                                WHERE {where_p1}
                                GROUP BY fecha_cierre_auditoria_tecnica
                            """
                            df_chart = conn.execute(query_chart).df()
                            
                            if not df_chart.empty:
                                # Convertimos a Datetime en Pandas (más seguro y flexible)
                                df_chart['fecha_dt'] = pd.to_datetime(df_chart['fecha_str'], format='%d/%m/%Y', errors='coerce')
                                
                                # Forzar el tipo numérico explícito
                                df_chart['cantidad_facturas'] = pd.to_numeric(df_chart['cantidad_facturas'], errors='coerce').fillna(0).astype(int)
                                df_chart['valor_gestionado'] = pd.to_numeric(df_chart['valor_gestionado'], errors='coerce').fillna(0.0)
                                
                                df_chart = df_chart.dropna(subset=['fecha_dt']).sort_values('fecha_dt')
                                
                                if not df_chart.empty:
                                    with st.container(border=True):
                                        # Hacemos una gráfica de área y línea combinadas usando las nuevas variables sin puntos
                                        linea = alt.Chart(df_chart).mark_line(color="#38bdf8", strokeWidth=3, point=alt.OverlayMarkDef(color="#0ea5e9", size=80)).encode(
                                            x=alt.X('fecha_dt:T', title="Fecha de Cierre", axis=alt.Axis(format="%d %b", labelAngle=-45, grid=False)),
                                            y=alt.Y('cantidad_facturas:Q', title="Facturas Ejecutadas", scale=alt.Scale(zero=True, padding=10)),
                                            tooltip=[
                                                alt.Tooltip('fecha_dt:T', title="Fecha", format="%d/%m/%Y"),
                                                alt.Tooltip('cantidad_facturas:Q', title="Facturas Realizadas", format=","),
                                                alt.Tooltip('valor_gestionado:Q', title="Valor Revisado ($)", format="$,.0f")
                                            ]
                                        ).interactive()
                                        
                                        area = linea.mark_area(
                                            color=alt.Gradient(
                                                gradient='linear',
                                                stops=[alt.GradientStop(color='rgba(56, 189, 248, 0.4)', offset=0),
                                                       alt.GradientStop(color='rgba(56, 189, 248, 0.0)', offset=1)],
                                                x1=1, x2=1, y1=1, y2=0
                                            )
                                        ).encode(x='fecha_dt:T', y='cantidad_facturas:Q')

                                        st.altair_chart(area + linea, use_container_width=True)
                                else:
                                    st.info("No se pudieron procesar las fechas para la gráfica.")
                            else:
                                st.info("Datos insuficientes para graficar la tendencia temporal en este rango.")
                    else:
                        st.info("No hay facturas ejecutadas para la fecha seleccionada.")
                except Exception as e:
                    st.warning(f"Esperando datos de fechas de ejecución válidas... ({e})")
                
            with v_prod_2:
                st.markdown("#### 📅 Ejecutado por Mes de Radicación")
                
                # 1. Extracción de Fechas Únicas para los filtros (Basado en la fecha de CIERRE y ESTADO)
                try:
                    # 🎯 REQUERIMIENTO: Solo estados Cerrado y Notificado
                    cond_estado = "UPPER(CAST(estado_tecnica AS VARCHAR)) IN ('CERRADO', 'NOTIFICADO')"
                    
                    # 🎯 Extraer fechas de cierre válidas para alimentar los filtros
                    query_fechas_v2 = f"SELECT DISTINCT fecha_cierre_auditoria_tecnica FROM facturas WHERE fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    df_f2 = conn.execute(query_fechas_v2).df()
                    df_f2['fecha_dt'] = pd.to_datetime(df_f2['fecha_cierre_auditoria_tecnica'], format='%d/%m/%Y', errors='coerce')
                    df_f2 = df_f2.dropna(subset=['fecha_dt'])
                    
                    # Filtros de fecha distribuidos en columnas
                    c_anio2, c_mes2, c_dia2, _ = st.columns([1.5, 1.5, 1.5, 5.5])
                    
                    anios_disp2 = sorted(df_f2['fecha_dt'].dt.year.astype(int).unique().tolist(), reverse=True)
                    with c_anio2:
                        anio_sel2 = st.selectbox("Año Cierre", ["Todos"] + anios_disp2, key="prod_2_anio")
                    
                    meses_disp2 = []
                    if anio_sel2 != "Todos":
                        meses_disp2 = sorted(df_f2[df_f2['fecha_dt'].dt.year == anio_sel2]['fecha_dt'].dt.month.astype(int).unique().tolist())
                    with c_mes2:
                        mes_sel2 = st.selectbox("Mes Cierre", ["Todos"] + meses_disp2, key="prod_2_mes", disabled=(anio_sel2 == "Todos"))
                    
                    dias_disp2 = []
                    if mes_sel2 != "Todos" and anio_sel2 != "Todos":
                        dias_disp2 = sorted(df_f2[(df_f2['fecha_dt'].dt.year == anio_sel2) & (df_f2['fecha_dt'].dt.month == mes_sel2)]['fecha_dt'].dt.day.astype(int).unique().tolist())
                    with c_dia2:
                        dia_sel2 = st.selectbox("Día Cierre", ["Todos"] + dias_disp2, key="prod_2_dia", disabled=(mes_sel2 == "Todos"))
                    
                    st.write("---")
                    
                    # 2. Construir condicional SQL para el filtro de fechas (Apunta a CIERRE)
                    where_p2 = f"fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    fecha_titulo2 = ""
                    
                    if anio_sel2 != "Todos":
                        where_p2 += f" AND fecha_cierre_auditoria_tecnica LIKE '%{anio_sel2}'"
                        fecha_titulo2 = str(anio_sel2)
                    if mes_sel2 != "Todos":
                        mes_str2 = f"{mes_sel2:02d}"
                        where_p2 += f" AND fecha_cierre_auditoria_tecnica LIKE '%/{mes_str2}/%'"
                        fecha_titulo2 = f"{mes_str2}/{anio_sel2}"
                    if dia_sel2 != "Todos":
                        dia_str2 = f"{dia_sel2:02d}"
                        where_p2 += f" AND fecha_cierre_auditoria_tecnica LIKE '{dia_str2}/%'"
                        fecha_titulo2 = f"{dia_str2}/{mes_str2}/{anio_sel2}"
                    
                    # 3. Ejecutar Query Principal (Agrupando por MES DE RADICACIÓN)
                    query_p2 = f"""
                        SELECT 
                            COALESCE(MONTH(TRY_STRPTIME(fecha_radicado, '%d/%m/%Y')), MONTH(TRY_CAST(fecha_radicado AS DATE))) as num_mes_rad,
                            COUNT(factura) as "Cant. Factura",
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as "Valor Factura",
                            SUM(TRY_CAST(total_glosas AS DOUBLE)) as "Total Glosa"
                        FROM facturas
                        WHERE {where_p2} AND fecha_radicado IS NOT NULL AND TRIM(CAST(fecha_radicado AS VARCHAR)) != ''
                        GROUP BY num_mes_rad
                        HAVING num_mes_rad IS NOT NULL
                        ORDER BY num_mes_rad DESC
                    """
                    
                    df_p2 = conn.execute(query_p2).df().fillna(0)
                    
                    if not df_p2.empty:
                        # Convertir el número del mes a sus primeras 3 letras minúsculas
                        meses_min = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                        df_p2['Mes de Radicación'] = df_p2['num_mes_rad'].map(meses_min)
                        
                        # 4. Cálculos Matemáticos y Fila de Totales
                        total_cant2 = df_p2['Cant. Factura'].sum()
                        total_vf2 = df_p2['Valor Factura'].sum()
                        total_tg2 = df_p2['Total Glosa'].sum()
                        
                        # Reestructurar orden de columnas
                        df_final2 = pd.DataFrame({
                            'Mes de Radicación': df_p2['Mes de Radicación'].tolist() + ['Total general'],
                            'Cant. Factura': df_p2['Cant. Factura'].tolist() + [total_cant2],
                            'Valor Factura': df_p2['Valor Factura'].tolist() + [total_vf2],
                            'Total Glosa': df_p2['Total Glosa'].tolist() + [total_tg2]
                        })
                        
                        # Porcentaje seguro contra división por cero
                        df_final2['%'] = (df_final2['Total Glosa'] / df_final2['Valor Factura']).fillna(0).replace([float('inf'), -float('inf')], 0)
                        
                        # 5. Formateo Visual
                        df_final2['Cant. Factura'] = df_final2['Cant. Factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final2['Valor Factura'] = df_final2['Valor Factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        df_final2['Total Glosa'] = df_final2['Total Glosa'].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        # Porcentaje con 1 decimal y coma
                        df_final2['%'] = df_final2['%'].apply(lambda x: "0,0%" if x == 0 else f"{x*100:.1f}%".replace('.', ','))
                        
                        # 6. Renderizado de Interfaz (Header oscuro con borde sutil)
                        tit_text2 = f"TOTAL EJECUTADO {fecha_titulo2} POR FECHA DE RADICACIÓN" if fecha_titulo2 else "TOTAL EJECUTADO GENERAL POR FECHA DE RADICACIÓN"
                        st.markdown(f"<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>{tit_text2.upper()}</div>", unsafe_allow_html=True)
                        
                        # Estilos: Fila Totales (gris oscuro) + Porcentaje en Rojo constante
                        def estilo_prod2(row):
                            styles = [''] * len(row)
                            es_total = (row.name == df_final2.index[-1])
                            for i, col in enumerate(df_final2.columns):
                                if es_total:
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                                    if col == '%': 
                                        styles[i] = 'font-weight: bold; color: #ef4444; background-color: rgba(255,255,255,0.05)' 
                                elif col == '%': 
                                    styles[i] = 'font-weight: bold; color: #ef4444;' 
                            return styles
                        
                        altura_dinamica2 = (len(df_final2) * 36) + 43
                        st.dataframe(df_final2.style.apply(estilo_prod2, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica2)
                    else:
                        st.info("No hay facturas ejecutadas para la fecha seleccionada con información de radicación.")
                except Exception as e:
                    st.warning(f"Esperando datos de fechas válidas... ({e})")
                
            with v_prod_3:
                st.markdown("#### 📄 Ejecutado por Tipo de Contrato")
                
                # 1. Extracción de Fechas Únicas para los filtros (Basado en la fecha de CIERRE y ESTADO)
                try:
                    # 🎯 REQUERIMIENTO: Solo estados Cerrado y Notificado
                    cond_estado = "UPPER(CAST(estado_tecnica AS VARCHAR)) IN ('CERRADO', 'NOTIFICADO')"
                    
                    # 🎯 Extraer fechas de cierre válidas para alimentar los filtros
                    query_fechas_v3 = f"SELECT DISTINCT fecha_cierre_auditoria_tecnica FROM facturas WHERE fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    df_f3 = conn.execute(query_fechas_v3).df()
                    df_f3['fecha_dt'] = pd.to_datetime(df_f3['fecha_cierre_auditoria_tecnica'], format='%d/%m/%Y', errors='coerce')
                    df_f3 = df_f3.dropna(subset=['fecha_dt'])
                    
                    # Filtros de fecha distribuidos en columnas
                    c_anio3, c_mes3, c_dia3, _ = st.columns([1.5, 1.5, 1.5, 5.5])
                    
                    anios_disp3 = sorted(df_f3['fecha_dt'].dt.year.astype(int).unique().tolist(), reverse=True)
                    with c_anio3:
                        anio_sel3 = st.selectbox("Año Cierre", ["Todos"] + anios_disp3, key="prod_3_anio")
                    
                    meses_disp3 = []
                    if anio_sel3 != "Todos":
                        meses_disp3 = sorted(df_f3[df_f3['fecha_dt'].dt.year == anio_sel3]['fecha_dt'].dt.month.astype(int).unique().tolist())
                    with c_mes3:
                        mes_sel3 = st.selectbox("Mes Cierre", ["Todos"] + meses_disp3, key="prod_3_mes", disabled=(anio_sel3 == "Todos"))
                    
                    dias_disp3 = []
                    if mes_sel3 != "Todos" and anio_sel3 != "Todos":
                        dias_disp3 = sorted(df_f3[(df_f3['fecha_dt'].dt.year == anio_sel3) & (df_f3['fecha_dt'].dt.month == mes_sel3)]['fecha_dt'].dt.day.astype(int).unique().tolist())
                    with c_dia3:
                        dia_sel3 = st.selectbox("Día Cierre", ["Todos"] + dias_disp3, key="prod_3_dia", disabled=(mes_sel3 == "Todos"))
                    
                    st.write("---")
                    
                    # 2. Construir condicional SQL para el filtro de fechas (Apunta a CIERRE)
                    where_p3 = f"fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    fecha_titulo3 = ""
                    
                    if anio_sel3 != "Todos":
                        where_p3 += f" AND fecha_cierre_auditoria_tecnica LIKE '%{anio_sel3}'"
                        fecha_titulo3 = str(anio_sel3)
                    if mes_sel3 != "Todos":
                        mes_str3 = f"{mes_sel3:02d}"
                        where_p3 += f" AND fecha_cierre_auditoria_tecnica LIKE '%/{mes_str3}/%'"
                        fecha_titulo3 = f"{mes_str3}/{anio_sel3}"
                    if dia_sel3 != "Todos":
                        dia_str3 = f"{dia_sel3:02d}"
                        where_p3 += f" AND fecha_cierre_auditoria_tecnica LIKE '{dia_str3}/%'"
                        fecha_titulo3 = f"{dia_str3}/{mes_str3}/{anio_sel3}"
                    
                    # 3. Ejecutar Query Principal (Agrupando por TIPO DE CONTRATO)
                    # Se inyecta un CASE para agrupar los nulos o vacíos como "Sin Contrato"
                    query_p3 = f"""
                        SELECT 
                            CASE WHEN tipo_contrato IS NULL OR TRIM(CAST(tipo_contrato AS VARCHAR)) = '' 
                                 THEN 'Sin Contrato' 
                                 ELSE CAST(tipo_contrato AS VARCHAR) END as "Tipo de Contrato",
                            COUNT(factura) as "Cant. Factura",
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as "Valor Factura",
                            SUM(TRY_CAST(total_glosas AS DOUBLE)) as "Total Glosa"
                        FROM facturas
                        WHERE {where_p3}
                        GROUP BY "Tipo de Contrato"
                        ORDER BY "Valor Factura" DESC
                    """
                    
                    df_p3 = conn.execute(query_p3).df().fillna(0)
                    
                    if not df_p3.empty:
                        # 4. Cálculos Matemáticos y Fila de Totales
                        total_cant3 = df_p3['Cant. Factura'].sum()
                        total_vf3 = df_p3['Valor Factura'].sum()
                        total_tg3 = df_p3['Total Glosa'].sum()
                        
                        df_final3 = pd.DataFrame({
                            'Tipo de Contrato': df_p3['Tipo de Contrato'].tolist() + ['Total general'],
                            'Cant. Factura': df_p3['Cant. Factura'].tolist() + [total_cant3],
                            'Valor Factura': df_p3['Valor Factura'].tolist() + [total_vf3],
                            'Total Glosa': df_p3['Total Glosa'].tolist() + [total_tg3]
                        })
                        
                        # Porcentaje seguro contra división por cero
                        df_final3['%'] = (df_final3['Total Glosa'] / df_final3['Valor Factura']).fillna(0).replace([float('inf'), -float('inf')], 0)
                        
                        # 5. Formateo Visual
                        df_final3['Cant. Factura'] = df_final3['Cant. Factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final3['Valor Factura'] = df_final3['Valor Factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        df_final3['Total Glosa'] = df_final3['Total Glosa'].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        # Porcentaje con 1 decimal y coma
                        df_final3['%'] = df_final3['%'].apply(lambda x: "0,0%" if x == 0 else f"{x*100:.1f}%".replace('.', ','))
                        
                        # 6. Renderizado de Interfaz (Header oscuro con borde sutil)
                        tit_text3 = f"TOTAL EJECUTADO {fecha_titulo3} POR TIPO DE CONTRATO" if fecha_titulo3 else "TOTAL EJECUTADO GENERAL POR TIPO DE CONTRATO"
                        st.markdown(f"<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>{tit_text3.upper()}</div>", unsafe_allow_html=True)
                        
                        # Estilos: Fila Totales (gris oscuro) + Porcentaje en Rojo constante
                        def estilo_prod3(row):
                            styles = [''] * len(row)
                            es_total = (row.name == df_final3.index[-1])
                            for i, col in enumerate(df_final3.columns):
                                if es_total:
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                                    if col == '%': 
                                        styles[i] = 'font-weight: bold; color: #ef4444; background-color: rgba(255,255,255,0.05)' 
                                elif col == '%': 
                                    styles[i] = 'font-weight: bold; color: #ef4444;' 
                            return styles
                        
                        altura_dinamica3 = (len(df_final3) * 36) + 43
                        st.dataframe(df_final3.style.apply(estilo_prod3, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica3)
                    else:
                        st.info("No hay facturas ejecutadas para la fecha seleccionada con esta información.")
                except Exception as e:
                    st.warning(f"Esperando datos de fechas válidas... ({e})")
                
            with v_prod_4:
                st.markdown("#### 📊 Ejecutado por Rango de Valores")
                
                # 1. Extracción de Fechas Únicas para los filtros (Basado en la fecha de CIERRE y ESTADO)
                try:
                    # 🎯 REQUERIMIENTO: Solo estados Cerrado y Notificado
                    cond_estado = "UPPER(CAST(estado_tecnica AS VARCHAR)) IN ('CERRADO', 'NOTIFICADO')"
                    
                    # 🎯 Extraer fechas de cierre válidas para alimentar los filtros
                    query_fechas_v4 = f"SELECT DISTINCT fecha_cierre_auditoria_tecnica FROM facturas WHERE fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    df_f4 = conn.execute(query_fechas_v4).df()
                    df_f4['fecha_dt'] = pd.to_datetime(df_f4['fecha_cierre_auditoria_tecnica'], format='%d/%m/%Y', errors='coerce')
                    df_f4 = df_f4.dropna(subset=['fecha_dt'])
                    
                    # Filtros de fecha distribuidos en columnas
                    c_anio4, c_mes4, c_dia4, _ = st.columns([1.5, 1.5, 1.5, 5.5])
                    
                    anios_disp4 = sorted(df_f4['fecha_dt'].dt.year.astype(int).unique().tolist(), reverse=True)
                    with c_anio4:
                        anio_sel4 = st.selectbox("Año Cierre", ["Todos"] + anios_disp4, key="prod_4_anio")
                    
                    meses_disp4 = []
                    if anio_sel4 != "Todos":
                        meses_disp4 = sorted(df_f4[df_f4['fecha_dt'].dt.year == anio_sel4]['fecha_dt'].dt.month.astype(int).unique().tolist())
                    with c_mes4:
                        mes_sel4 = st.selectbox("Mes Cierre", ["Todos"] + meses_disp4, key="prod_4_mes", disabled=(anio_sel4 == "Todos"))
                    
                    dias_disp4 = []
                    if mes_sel4 != "Todos" and anio_sel4 != "Todos":
                        dias_disp4 = sorted(df_f4[(df_f4['fecha_dt'].dt.year == anio_sel4) & (df_f4['fecha_dt'].dt.month == mes_sel4)]['fecha_dt'].dt.day.astype(int).unique().tolist())
                    with c_dia4:
                        dia_sel4 = st.selectbox("Día Cierre", ["Todos"] + dias_disp4, key="prod_4_dia", disabled=(mes_sel4 == "Todos"))
                    
                    st.write("---")
                    
                    # 2. Construir condicional SQL para el filtro de fechas (Apunta a CIERRE)
                    where_p4 = f"fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    fecha_titulo4 = ""
                    
                    if anio_sel4 != "Todos":
                        where_p4 += f" AND fecha_cierre_auditoria_tecnica LIKE '%{anio_sel4}'"
                        fecha_titulo4 = str(anio_sel4)
                    if mes_sel4 != "Todos":
                        mes_str4 = f"{mes_sel4:02d}"
                        where_p4 += f" AND fecha_cierre_auditoria_tecnica LIKE '%/{mes_str4}/%'"
                        fecha_titulo4 = f"{mes_str4}/{anio_sel4}"
                    if dia_sel4 != "Todos":
                        dia_str4 = f"{dia_sel4:02d}"
                        where_p4 += f" AND fecha_cierre_auditoria_tecnica LIKE '{dia_str4}/%'"
                        fecha_titulo4 = f"{dia_str4}/{mes_str4}/{anio_sel4}"
                    
                    # 3. Ejecutar Query Principal (Agrupando por RANGO DE FACTURA)
                    query_p4 = f"""
                        SELECT 
                            CASE WHEN rango_factura IS NULL OR TRIM(CAST(rango_factura AS VARCHAR)) = '' 
                                 THEN 'Sin Rango' 
                                 ELSE CAST(rango_factura AS VARCHAR) END as "Rango Valor de Facturas",
                            COUNT(factura) as "Cant. Factura",
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as "Valor Factura",
                            SUM(TRY_CAST(total_glosas AS DOUBLE)) as "Total Glosa"
                        FROM facturas
                        WHERE {where_p4}
                        GROUP BY "Rango Valor de Facturas"
                        ORDER BY "Valor Factura" DESC
                    """
                    
                    df_p4 = conn.execute(query_p4).df().fillna(0)
                    
                    if not df_p4.empty:
                        # 4. Cálculos Matemáticos y Fila de Totales
                        total_cant4 = df_p4['Cant. Factura'].sum()
                        total_vf4 = df_p4['Valor Factura'].sum()
                        total_tg4 = df_p4['Total Glosa'].sum()
                        
                        df_final4 = pd.DataFrame({
                            'Rango Valor de Facturas': df_p4['Rango Valor de Facturas'].tolist() + ['Total general'],
                            'Cant. Factura': df_p4['Cant. Factura'].tolist() + [total_cant4],
                            'Valor Factura': df_p4['Valor Factura'].tolist() + [total_vf4],
                            'Total Glosa': df_p4['Total Glosa'].tolist() + [total_tg4]
                        })
                        
                        # Porcentaje seguro contra división por cero
                        df_final4['%'] = (df_final4['Total Glosa'] / df_final4['Valor Factura']).fillna(0).replace([float('inf'), -float('inf')], 0)
                        
                        # 5. Formateo Visual
                        df_final4['Cant. Factura'] = df_final4['Cant. Factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final4['Valor Factura'] = df_final4['Valor Factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        df_final4['Total Glosa'] = df_final4['Total Glosa'].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        # Porcentaje con 1 decimal y coma
                        df_final4['%'] = df_final4['%'].apply(lambda x: "0,0%" if x == 0 else f"{x*100:.1f}%".replace('.', ','))
                        
                        # 6. Renderizado de Interfaz (Header oscuro con borde sutil)
                        tit_text4 = f"TOTAL EJECUTADO {fecha_titulo4} POR RANGO DE VALORES" if fecha_titulo4 else "TOTAL EJECUTADO GENERAL POR RANGO DE VALORES"
                        st.markdown(f"<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>{tit_text4.upper()}</div>", unsafe_allow_html=True)
                        
                        # Estilos: Fila Totales (gris oscuro) + Porcentaje en Rojo constante
                        def estilo_prod4(row):
                            styles = [''] * len(row)
                            es_total = (row.name == df_final4.index[-1])
                            for i, col in enumerate(df_final4.columns):
                                if es_total:
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                                    if col == '%': 
                                        styles[i] = 'font-weight: bold; color: #ef4444; background-color: rgba(255,255,255,0.05)' 
                                elif col == '%': 
                                    styles[i] = 'font-weight: bold; color: #ef4444;' 
                            return styles
                        
                        altura_dinamica4 = (len(df_final4) * 36) + 43
                        st.dataframe(df_final4.style.apply(estilo_prod4, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica4)
                    else:
                        st.info("No hay facturas ejecutadas para la fecha seleccionada con esta información.")
                except Exception as e:
                    st.warning(f"Esperando datos de fechas válidas... ({e})")
                
            with v_prod_5:
                st.markdown("#### 👥 Ejecutado por Perfil de Auditor")
                
                # 1. Extracción de Fechas Únicas para los filtros (Basado en la fecha de CIERRE y ESTADO)
                try:
                    # 🎯 REQUERIMIENTO: Solo estados Cerrado y Notificado
                    cond_estado = "UPPER(CAST(estado_tecnica AS VARCHAR)) IN ('CERRADO', 'NOTIFICADO')"
                    
                    # 🎯 Extraer fechas de cierre válidas para alimentar los filtros
                    query_fechas_v5 = f"SELECT DISTINCT fecha_cierre_auditoria_tecnica FROM facturas WHERE fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    df_f5 = conn.execute(query_fechas_v5).df()
                    df_f5['fecha_dt'] = pd.to_datetime(df_f5['fecha_cierre_auditoria_tecnica'], format='%d/%m/%Y', errors='coerce')
                    df_f5 = df_f5.dropna(subset=['fecha_dt'])
                    
                    # Filtros de fecha distribuidos en columnas
                    c_anio5, c_mes5, c_dia5, _ = st.columns([1.5, 1.5, 1.5, 5.5])
                    
                    anios_disp5 = sorted(df_f5['fecha_dt'].dt.year.astype(int).unique().tolist(), reverse=True)
                    with c_anio5:
                        anio_sel5 = st.selectbox("Año Cierre", ["Todos"] + anios_disp5, key="prod_5_anio")
                    
                    meses_disp5 = []
                    if anio_sel5 != "Todos":
                        meses_disp5 = sorted(df_f5[df_f5['fecha_dt'].dt.year == anio_sel5]['fecha_dt'].dt.month.astype(int).unique().tolist())
                    with c_mes5:
                        mes_sel5 = st.selectbox("Mes Cierre", ["Todos"] + meses_disp5, key="prod_5_mes", disabled=(anio_sel5 == "Todos"))
                    
                    dias_disp5 = []
                    if mes_sel5 != "Todos" and anio_sel5 != "Todos":
                        dias_disp5 = sorted(df_f5[(df_f5['fecha_dt'].dt.year == anio_sel5) & (df_f5['fecha_dt'].dt.month == mes_sel5)]['fecha_dt'].dt.day.astype(int).unique().tolist())
                    with c_dia5:
                        dia_sel5 = st.selectbox("Día Cierre", ["Todos"] + dias_disp5, key="prod_5_dia", disabled=(mes_sel5 == "Todos"))
                    
                    st.write("---")
                    
                    # 2. Construir condicional SQL para el filtro de fechas (Apunta a CIERRE)
                    where_p5 = f"fecha_cierre_auditoria_tecnica IS NOT NULL AND TRIM(CAST(fecha_cierre_auditoria_tecnica AS VARCHAR)) != '' AND {cond_estado}"
                    fecha_titulo5 = ""
                    
                    if anio_sel5 != "Todos":
                        where_p5 += f" AND fecha_cierre_auditoria_tecnica LIKE '%{anio_sel5}'"
                        fecha_titulo5 = str(anio_sel5)
                    if mes_sel5 != "Todos":
                        mes_str5 = f"{mes_sel5:02d}"
                        where_p5 += f" AND fecha_cierre_auditoria_tecnica LIKE '%/{mes_str5}/%'"
                        fecha_titulo5 = f"{mes_str5}/{anio_sel5}"
                    if dia_sel5 != "Todos":
                        dia_str5 = f"{dia_sel5:02d}"
                        where_p5 += f" AND fecha_cierre_auditoria_tecnica LIKE '{dia_str5}/%'"
                        fecha_titulo5 = f"{dia_str5}/{mes_str5}/{anio_sel5}"
                    
                    # 3. Ejecutar Query Principal (Agrupando por PERFIL AUDITOR)
                    query_p5 = f"""
                        SELECT 
                            CASE WHEN perfil_auditor IS NULL OR TRIM(CAST(perfil_auditor AS VARCHAR)) = '' 
                                 THEN 'Sin Perfil Asignado' 
                                 ELSE CAST(perfil_auditor AS VARCHAR) END as "Perfil",
                            COUNT(factura) as "Cant. Factura",
                            SUM(TRY_CAST(valor_factura AS DOUBLE)) as "Valor Factura",
                            SUM(TRY_CAST(total_glosas AS DOUBLE)) as "Total Glosa"
                        FROM facturas
                        WHERE {where_p5}
                        GROUP BY "Perfil"
                        ORDER BY "Valor Factura" DESC
                    """
                    
                    df_p5 = conn.execute(query_p5).df().fillna(0)
                    
                    if not df_p5.empty:
                        # 4. Cálculos Matemáticos y Fila de Totales
                        total_cant5 = df_p5['Cant. Factura'].sum()
                        total_vf5 = df_p5['Valor Factura'].sum()
                        total_tg5 = df_p5['Total Glosa'].sum()
                        
                        df_final5 = pd.DataFrame({
                            'Perfil': df_p5['Perfil'].tolist() + ['Total general'],
                            'Cant. Factura': df_p5['Cant. Factura'].tolist() + [total_cant5],
                            'Valor Factura': df_p5['Valor Factura'].tolist() + [total_vf5],
                            'Total Glosa': df_p5['Total Glosa'].tolist() + [total_tg5]
                        })
                        
                        # Porcentaje seguro contra división por cero
                        df_final5['%'] = (df_final5['Total Glosa'] / df_final5['Valor Factura']).fillna(0).replace([float('inf'), -float('inf')], 0)
                        
                        # 5. Formateo Visual
                        df_final5['Cant. Factura'] = df_final5['Cant. Factura'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
                        df_final5['Valor Factura'] = df_final5['Valor Factura'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        df_final5['Total Glosa'] = df_final5['Total Glosa'].apply(lambda x: "$ -" if x == 0 else f"$ {float(x):,.0f}".replace(',', '.'))
                        
                        # Porcentaje con 1 decimal y coma
                        df_final5['%'] = df_final5['%'].apply(lambda x: "0,0%" if x == 0 else f"{x*100:.1f}%".replace('.', ','))
                        
                        # 6. Renderizado de Interfaz (Header oscuro con borde sutil)
                        tit_text5 = f"TOTAL EJECUTADO {fecha_titulo5} POR PERFIL DE AUDITOR" if fecha_titulo5 else "TOTAL EJECUTADO GENERAL POR PERFIL DE AUDITOR"
                        st.markdown(f"<div style='text-align: center; color: #e2e8f0; font-weight: 800; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 2px solid #38bdf8;'>{tit_text5.upper()}</div>", unsafe_allow_html=True)
                        
                        # Estilos: Fila Totales (gris oscuro) + Porcentaje en Rojo constante
                        def estilo_prod5(row):
                            styles = [''] * len(row)
                            es_total = (row.name == df_final5.index[-1])
                            for i, col in enumerate(df_final5.columns):
                                if es_total:
                                    styles[i] = 'font-weight: bold; color: #f8fafc; background-color: rgba(255,255,255,0.05)'
                                    if col == '%': 
                                        styles[i] = 'font-weight: bold; color: #ef4444; background-color: rgba(255,255,255,0.05)' 
                                elif col == '%': 
                                    styles[i] = 'font-weight: bold; color: #ef4444;' 
                            return styles
                        
                        altura_dinamica5 = (len(df_final5) * 36) + 43
                        st.dataframe(df_final5.style.apply(estilo_prod5, axis=1), use_container_width=True, hide_index=True, height=altura_dinamica5)
                    else:
                        st.info("No hay facturas ejecutadas para la fecha seleccionada con esta información de perfil.")
                except Exception as e:
                    st.warning(f"Esperando datos de fechas válidas... ({e})")

# =========================================================================
    # PANTALLA 6: DETALLE DE GLOSAS
    # =========================================================================
    elif st.session_state.modulo_activo == "Detalle de Glosas":
        st.title("Detalle y Ranking de Glosas")

        # 1. Asegurar tabla independiente en DuckDB (Aislada de la principal)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tabla_detalle_glosas (
                factura VARCHAR,
                razon_social VARCHAR,
                nit VARCHAR,
                fecha_radica VARCHAR,
                total_glosa DOUBLE,
                codigo_glosa VARCHAR
            )
        """)
        
        df_glosas = conn.execute("SELECT * FROM tabla_detalle_glosas").df()

        # 2. SECCIÓN DE CARGA INDEPENDIENTE
        if df_glosas.empty:
            st.info("No hay datos de glosas cargados. Por favor sube tu archivo CSV de Detalles de Glosa.")
            with st.container(border=True):
                archivo_glosas = st.file_uploader("Cargar CSV de Glosas", type=['csv'], key="uploader_glosas")
                
                if archivo_glosas:
                    if st.button("🚀 Procesar Archivo de Glosas", use_container_width=True, type="primary"):
                        with st.spinner("Filtrando glosas ejecutadas y procesando rankings..."):
                            try:
                                # Lectura robusta del CSV con múltiples codificaciones
                                df_g = None
                                for encoding in ['utf-8-sig', 'latin-1', 'cp1252']:
                                    try:
                                        archivo_glosas.seek(0)
                                        df_g = pd.read_csv(archivo_glosas, sep=';', encoding=encoding, low_memory=False, dtype=str)
                                        if len(df_g.columns) >= 5: 
                                            break
                                    except Exception:
                                        pass
                                
                                if df_g is None or len(df_g.columns) < 5:
                                    for encoding in ['utf-8-sig', 'latin-1', 'cp1252']:
                                        try:
                                            archivo_glosas.seek(0)
                                            df_g = pd.read_csv(archivo_glosas, sep=',', encoding=encoding, low_memory=False, dtype=str)
                                            if len(df_g.columns) >= 5: 
                                                break
                                        except Exception:
                                            pass
                                            
                                if df_g is None:
                                    raise ValueError("Formato de archivo no soportado o ilegible.")
                                
                                # Normalización de columnas
                                df_g.columns = df_g.columns.astype(str).str.strip().str.lower().str.replace(' ', '_').str.replace('ï»¿', '').str.replace('\ufeff', '')
                                
                                # 🎯 REQUERIMIENTO 4: Filtro Estricto de Tipo de Glosa
                                if 'tipo_glosa' in df_g.columns:
                                    # Eliminamos las informativas explícitamente y nos aseguramos de dejar solo las ejecutadas
                                    df_g = df_g[~df_g['tipo_glosa'].astype(str).str.lower().str.contains('informativ', na=False)]
                                    df_g = df_g[df_g['tipo_glosa'].astype(str).str.lower().str.contains('ejecutad', na=False)]
                                
                                # Formatear la plata para sumar
                                if 'total_glosa' in df_g.columns:
                                    df_g['total_glosa'] = df_g['total_glosa'].astype(str).replace(r'[^\d.-]', '', regex=True)
                                    df_g['total_glosa'] = pd.to_numeric(df_g['total_glosa'], errors='coerce').fillna(0.0)
                                else:
                                    df_g['total_glosa'] = 0.0

                                # 🎯 REQUERIMIENTO 5: Mapeo de Códigos de Glosa (Primeras 2 letras)
                                if 'codigo_glosa' in df_g.columns:
                                    mapa_codigos = {
                                        'FA': 'FA - Facturación',
                                        'TA': 'TA - Tarifas',
                                        'SO': 'SO - SOPORTES',
                                        'AU': 'AU - AUTORIZACIONES',
                                        'CO': 'CO - COBERTURA',
                                        'CL': 'CL - CALIDAD',
                                        'SA': 'SA - SEGUIMIENTO A LOS ACUERDOS'
                                    }
                                    # Extraemos los 2 primeros caracteres, los ponemos en mayúscula y mapeamos
                                    prefijo = df_g['codigo_glosa'].astype(str).str.strip().str[:2].str.upper()
                                    df_g['codigo_glosa'] = prefijo.map(mapa_codigos).fillna(prefijo + ' - OTROS')
                                
                                # Garantizar que las columnas existan aunque el CSV falle
                                for col in ['factura', 'razon_social', 'nit', 'fecha_radica']:
                                    if col not in df_g.columns:
                                        df_g[col] = 'SIN DATO'
                                        
                                # 🎯 REQUERIMIENTO 3: Estructura Final Solicitada
                                df_final_g = df_g[['factura', 'razon_social', 'nit', 'fecha_radica', 'total_glosa', 'codigo_glosa']]
                                
                                conn.execute("INSERT INTO tabla_detalle_glosas SELECT * FROM df_final_g")
                                st.success("¡Archivo depurado y rankings generados exitosamente!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error crítico procesando el archivo: {e}")
            st.stop()

        # 3. INTERFAZ DE VISTAS Y RANKINGS
        c_tit, c_btn_vaciar = st.columns([8.5, 1.5])
        with c_btn_vaciar:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            with st.popover("🗑️ Vaciar Glosas", use_container_width=True):
                st.warning("Se eliminarán los datos de este módulo.")
                if st.button("Confirmar", type="primary", use_container_width=True):
                    conn.execute("DELETE FROM tabla_detalle_glosas")
                    st.rerun()

        st.write("---")
        
        # 🎯 REQUERIMIENTO 6: Identificamos los tipos de glosas para crear las pestañas
        tipos_existentes = conn.execute("SELECT DISTINCT codigo_glosa FROM tabla_detalle_glosas WHERE codigo_glosa IS NOT NULL AND codigo_glosa != '' ORDER BY codigo_glosa").df()['codigo_glosa'].tolist()
        
        if tipos_existentes:
            pestañas = st.tabs(["📊 TABLA MAESTRA"] + tipos_existentes)
            
            # Pestaña 0: La base completa estructurada
            with pestañas[0]:
                st.markdown("#### Estructura General (Glosas Ejecutadas)")
                df_view_gen = df_glosas.copy()
                df_view_gen['total_glosa'] = df_view_gen['total_glosa'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                df_view_gen.columns = ['Factura', 'Razón Social', 'NIT', 'Fecha Radica', 'Total Glosa', 'Código Glosa']
                st.dataframe(df_view_gen, use_container_width=True, hide_index=True, height=500)
            
            # Pestañas Dinámicas: Un Ranking por cada tipo de glosa detectado
            for i, tipo in enumerate(tipos_existentes):
                with pestañas[i+1]:
                    st.markdown(f"#### Tabla de Prestadores: {tipo}")
                    
                    query_rank = f"""
                        SELECT 
                            razon_social as "Razón Social",
                            nit as "NIT",
                            COUNT(factura) as "Cant. Facturas Glosadas",
                            SUM(total_glosa) as "Valor Total Glosado"
                        FROM tabla_detalle_glosas
                        WHERE codigo_glosa = '{tipo}'
                        GROUP BY razon_social, nit
                        ORDER BY "Valor Total Glosado" DESC
                    """
                    
                    df_rank = conn.execute(query_rank).df()
                    
                    if not df_rank.empty:
                        # Formateamos moneda visual
                        df_rank['Valor Total Glosado'] = df_rank['Valor Total Glosado'].apply(lambda x: f"$ {float(x):,.0f}".replace(',', '.'))
                        # Inyectamos el Top Rank #
                        df_rank.insert(0, 'TOP', range(1, len(df_rank) + 1))
                        
                        st.dataframe(df_rank, use_container_width=True, hide_index=True, height=500)
                    else:
                        st.info("Sin registros depurados para este tipo específico.")
        else:
            st.info("No se encontraron tipos de glosa válidos tras el filtro de depuración.")

except Exception as e:
    st.info("Sistema en espera. Asegúrese de tener datos cargados.")