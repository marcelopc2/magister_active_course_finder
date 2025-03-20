import streamlit as st
import requests
from decouple import config
import re
import unicodedata
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timezone  # Corregido

# Configuración de la API de Canvas
BASE_URL = config("URL")
API_TOKEN = config("TOKEN")
LINK_URL = config("LINK_URL")
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Crear una sesión de requests
session = requests.Session()
session.headers.update(HEADERS)

def clean_string(input_string: str) -> str:
    cleaned = input_string.strip().lower()
    cleaned = unicodedata.normalize('NFD', cleaned)
    cleaned = re.sub(r'[^\w\s.,!?-]', '', cleaned)
    cleaned = re.sub(r'[\u0300-\u036f]', '', cleaned)
    return cleaned

def canvas_request(session, method, endpoint, payload=None, paginated=False):
    if not BASE_URL:
        raise ValueError("BASE_URL no está configurada. Usa set_base_url() para establecerla.")

    url = f"{BASE_URL}{endpoint}"
    results = []
    
    try:
        while url:
            response = session.request(method.upper(), url, json=payload)
            if not response.ok:
                st.error(f"Error en la petición a {url} ({response.status_code}): {response.text}")
                return None

            data = response.json()
            if paginated:
                results.extend(data)
                url = response.links.get("next", {}).get("url")  # Siguiente página
            else:
                return data

        return results if paginated else None

    except requests.exceptions.RequestException as e:
        st.error(f"Excepción en la petición a {url}: {e}")
        return None

def get_course_status(start_date_str):
    """Determina el estado del curso basado en su fecha de inicio"""
    if not start_date_str:
        return "⏳ :orange[Sin fecha de inicio definida]"

    try:
        # Convertir string a fecha
        start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%SZ")
        
        # Convertir start_date a aware datetime (con zona horaria UTC)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        
        end_date = start_date + relativedelta(months=1)  # Sumar 1 mes
        
        today = datetime.now(timezone.utc)  # Fecha actual en UTC

        if start_date <= today <= end_date:
            return "✅ :green[Curso Activo]"
        elif today > end_date:
            return "🚫 :red[Curso Finalizado]"
        else:
            return "⏳ :orange[No ha comenzado]"
    except ValueError:
        return "❌ Error en formato de fecha"

def format_date(date_str):
    """Convierte la fecha al formato día-mes-año"""
    if not date_str:
        return "❌ Fecha no disponible"
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return date_obj.strftime("%d-%m-%Y")  # Formato día-mes-año
    except ValueError:
        return "❌ Error en formato de fecha"

account = 42

st.set_page_config(page_title="Buscador de cursos de Magisteres", page_icon="🔍", layout="wide")
st.title("Buscador de cursos de Magisteres 🔍")
st.info("Este buscador permite encontrar cursos de Magisteres en Canvas basandose en la fecha de inicio del curso y sumandole un mes para determinar si está activo o no (ej: inicio = 2/3/25 + 1 mes = termino 2/4/25). Ya que generalmente no se coloca la fecha de finalización en la configuracion. Asi que tener presente esto.")

# Mostrar checkbox antes del botón
show_active_only = st.checkbox("Solo activos")

# Botón para comenzar a cargar los cursos
if st.button('Buscar cursos!!'):
    account = canvas_request(session, "get", f"/accounts/{account}/sub_accounts", paginated=True)
    if account:
        for item in account:
            st.write(f"### 🔹 {item['name']} (ID: {item['id']})")
            subaccounts = canvas_request(session, "get", f"/accounts/{item['id']}/sub_accounts", paginated=True)
            if subaccounts:
                for subaccount in subaccounts:
                    if clean_string("magister") in clean_string(subaccount['name']):
                        st.write(f"##### 🔸 {subaccount['name']} (ID: {subaccount['id']})")
                        courses = canvas_request(session, "get", f"/accounts/{subaccount['id']}/courses", paginated=True)
                        if courses:
                            for course in courses:
                                # Filtrar blueprints
                                course_info = canvas_request(session, "get", f"/courses/{course['id']}")
                                if course_info.get("blueprint") == True:
                                    continue
                                if course_info:
                                    start_date = course_info.get("start_at")  # Obtener fecha de inicio
                                    status = get_course_status(start_date)  # Evaluar estado del curso
                                    formatted_date = format_date(start_date)  # Formatear la fecha

                                    # Si el checkbox está marcado, mostrar solo los cursos activos
                                    if show_active_only and status != "✅ Curso Activo":
                                        continue

                                    # Mostrar curso con su estado y fecha de inicio, y convertir el nombre en enlace
                                    course_link = f"[**{course['name']}**]({LINK_URL}/courses/{course['id']})"
                                    st.write(f"📚 {course_link} ({course['sis_course_id']}) - {status} - 🗓️ Fecha de inicio: {formatted_date}")

    else:
        st.error("Error en la petición")
