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
        return "⏳ No ha comenzado (sin fecha definida)"

    try:
        # Convertir string a fecha
        start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%SZ")
        
        # Convertir start_date a aware datetime (con zona horaria UTC)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        
        end_date = start_date + relativedelta(months=1)  # Sumar 1 mes
        
        today = datetime.now(timezone.utc)  # Fecha actual en UTC

        if start_date <= today <= end_date:
            return "✅ Activo"
        elif today > end_date:
            return "🚫 Finalizado"
        else:
            return "⏳ No ha comenzado"
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

st.set_page_config(page_title="Buscador de Subcuentas Magister", page_icon="🔍")
st.title("🔍 Buscador de Subcuentas Magister en Canvas LMS")

# Tabla para mostrar los cursos
course_data = []

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
                            if 'blueprint' in clean_string(course['name']):
                                continue

                            course_info = canvas_request(session, "get", f"/courses/{course['id']}")
                            if course_info:
                                start_date = course_info.get("start_at")  # Obtener fecha de inicio
                                status = get_course_status(start_date)  # Evaluar estado del curso
                                formatted_date = format_date(start_date)  # Formatear la fecha
                                course_url = f"{BASE_URL}/courses/{course['id']}"  # Link al curso

                                # Añadir los datos del curso a la tabla
                                course_data.append([course['name'], status, formatted_date, course_url])

else:
    st.error("Error en la petición")

# Mostrar la tabla si hay cursos
if course_data:
    st.write("### Cursos de Magíster")
    st.table(course_data)  # Mostrar la tabla

else:
    st.write("No se encontraron cursos.")
