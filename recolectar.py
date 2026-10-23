"""
Recolector de datos públicos de un perfil de Instagram + Análisis Psicológico Big Five.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- SDK DE GEMINI ---
from google import genai
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# ==========================================================
# CONFIGURACIÓN
# ==========================================================

class Config:
    USUARIO = "alondra_cgp"
    BASE_URL = "https://www.instagram.com/"
    URL_PERFIL = f"{BASE_URL}{USUARIO}/"

    LIMITE_PUBLICACIONES = 25
    LIMITE_NOMBRES = 50

    BRAVE_EXE = (
        r"C:\Program Files\BraveSoftware"
        r"\Brave-Browser\Application\brave.exe"
    )
    PERFIL_BRAVE_RAIZ = (
        r"C:\Users\joseg\AppData\Local"
        r"\BraveSoftware\Brave-Browser\User Data"
    )
    NOMBRE_PERFIL = "Default"
    RUTA_CHROMEDRIVER = r"C:\drivers\chromedriver.exe"

    CARPETA_SALIDA = Path("salida_instagram")
    CARPETA_IMAGENES = CARPETA_SALIDA / "imagenes"

    TIMEOUT_CORTO = 5
    TIMEOUT_MEDIO = 10
    TIMEOUT_LARGO = 20

    PAUSA_ENTRE_POSTS = 2
    TIMEOUT_DESCARGA = 20

    RUTAS_EXCLUIDAS = {
        "blog", "popular", "explore", "accounts", "direct", "reels",
        "stories", "about", "developer", "legal", "web", "p", "reel",
        "challenge", "emails", "press", "api", "privacy", "terms",
        "directory", "followers", "following"
    }

# ==========================================================
# UTILIDADES
# ==========================================================

def fecha_actual() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")

def extraer_cantidad(texto: str | None, etiqueta: str) -> int | None:
    if not texto:
        return None
    coincidencia = re.search(
        rf"([\d.,]+)\s*{re.escape(etiqueta)}", texto, re.IGNORECASE
    )
    if not coincidencia:
        return None
    return int(coincidencia.group(1).replace(".", "").replace(",", ""))

def extraer_nombre_visible(titulo: str | None) -> str | None:
    if not titulo:
        return None
    coincidencia = re.search(r"^(.*?)\s*\(@", titulo)
    return coincidencia.group(1).strip() if coincidencia else None

def es_nombre_usuario_valido(nombre: str) -> bool:
    return bool(nombre and re.fullmatch(r"[A-Za-z0-9._]{1,30}", nombre))

def extraer_fecha_alt(texto_alt: str | None) -> str | None:
    if not texto_alt:
        return None
    coincidencia = re.search(
        r"\bon\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        texto_alt,
        re.IGNORECASE
    )
    return coincidencia.group(1) if coincidencia else None

def url_imagen_valida(url: str | None) -> bool:
    if not url:
        return False
    return (
        url.startswith("http")
        and ("scontent" in url or "cdninstagram" in url or "fbcdn" in url)
    )

def limpiar_nombre_archivo(texto: str) -> str:
    texto = re.sub(r"[^\w\-.]", "_", texto)
    return texto[:120] or "publicacion"

# ==========================================================
# ANÁLISIS CON GEMINI (BIG FIVE)
# ==========================================================

def analizar_personalidad_big_five(textos_publicaciones: list[str], api_key: str) -> dict:
    """
    Envía todas las descripciones a Gemini para obtener un perfil
    de personalidad basado en el modelo de los 5 Grandes.
    Incluye reintentos con espera exponencial para manejar la saturación (Error 503).
    """
    if not textos_publicaciones:
        return {"error": "No hay textos para analizar."}

    print("\n🧠 Iniciando análisis psicológico con Gemini...")
    
    texto_unificado = "\n---\n".join(textos_publicaciones)
    
    prompt = f"""
    Actúa como un psicólogo experto en análisis de personalidad y comportamiento digital.
    A continuación, te proporcionaré una lista de descripciones (captions) de las publicaciones de Instagram de un usuario.
    
    Tu tarea es analizar el texto y determinar sus rasgos de personalidad según el modelo de los "Cinco Grandes" (Big Five):
    1. Apertura a la experiencia (Openness): Curiosidad, creatividad, amplitud de intereses.
    2. Responsabilidad (Conscientiousness): Organización, disciplina, orientación a metas.
    3. Extraversión (Extraversion): Sociabilidad, energía, asertividad.
    4. Amabilidad (Agreeableness): Empatía, cooperación, calidez.
    5. Neuroticismo (Neuroticism): Inestabilidad emocional, ansiedad, vulnerabilidad al estrés.

    Basándote ÚNICAMENTE en el lenguaje, los temas, las emociones expresadas y el estilo de comunicación en los siguientes textos, asigna un puntaje del 1 al 10 a cada rasgo (donde 1 es muy bajo y 10 es muy alto) y proporciona una breve justificación para cada uno.

    Textos a analizar:
    {texto_unificado}

    Devuelve la respuesta ESTRICTAMENTE en formato JSON válido, con la siguiente estructura (no incluyas markdown, solo el JSON puro):
    {{
      "apertura": {{"puntaje": 0, "justificacion": "..."}},
      "responsabilidad": {{"puntaje": 0, "justificacion": "..."}},
      "extraversion": {{"puntaje": 0, "justificacion": "..."}},
      "amabilidad": {{"puntaje": 0, "justificacion": "..."}},
      "neuroticismo": {{"puntaje": 0, "justificacion": "..."}},
      "resumen_perfil": "Un párrafo breve resumiendo el perfil psicológico de la persona basado en su actividad en redes."
    }}
    """

    try:
        client = genai.Client(api_key=api_key)
        
        # Modelo actualizado según la sugerencia del error 404
        modelo = 'gemini-3.5-flash-lite'
        
        # Intentar hasta 5 veces con espera exponencial
        max_intentos = 5
        for intento in range(1, max_intentos + 1):
            try:
                print(f"  Llamando a {modelo} (Intento {intento}/{max_intentos})...")
                respuesta = client.models.generate_content(
                    model=modelo,
                    contents=prompt
                )
                
                texto_respuesta = respuesta.text
                texto_limpio = re.sub(r"```json\s*|\s*```", "", texto_respuesta).strip()
                
                resultado_json = json.loads(texto_limpio)
                print("✅ Análisis de Gemini completado con éxito.")
                return resultado_json
                
            except Exception as e:
                error_str = str(e)
                # Si es un error 503 o 429, esperamos un tiempo exponencial y reintentamos
                if "503" in error_str or "429" in error_str:
                    tiempo_espera = 2 ** intento  # 2, 4, 8, 16, 32 segundos
                    print(f"  ⚠️ Servidor ocupado. Esperando {tiempo_espera} segundos...")
                    time.sleep(tiempo_espera)
                else:
                    # Si es un error 404 (modelo no encontrado) u otro, no tiene sentido reintentar
                    print(f"  ❌ Error permanente con {modelo}: {error_str}")
                    return {"error": f"Error de API: {error_str}"}
        
        # Si se agotan los intentos
        print("❌ Se agotaron los reintentos. El servidor de Google sigue saturado.")
        return {"error": "Servidor saturado tras múltiples reintentos."}
        
    except Exception as e:
        print(f"❌ Error general al conectar con Gemini: {e}")
        return {"error": str(e)}

# ==========================================================
# DRIVER
# ==========================================================

class DriverInstagram:
    def __init__(self, config: type[Config]):
        self.config = config
        self.driver = self._crear()

    def _crear(self) -> webdriver.Chrome:
        cfg = self.config
        if not os.path.isfile(cfg.BRAVE_EXE):
            raise FileNotFoundError(f"No se encontró Brave en:\n{cfg.BRAVE_EXE}")
        if not os.path.isdir(cfg.PERFIL_BRAVE_RAIZ):
            raise FileNotFoundError(f"No se encontró la carpeta de perfiles:\n{cfg.PERFIL_BRAVE_RAIZ}")

        opciones = Options()
        opciones.binary_location = cfg.BRAVE_EXE
        opciones.add_argument(f"--user-data-dir={cfg.PERFIL_BRAVE_RAIZ}")
        opciones.add_argument(f"--profile-directory={cfg.NOMBRE_PERFIL}")
        opciones.add_argument("--disable-blink-features=AutomationControlled")
        opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
        opciones.add_experimental_option("useAutomationExtension", False)

        if os.path.isfile(cfg.RUTA_CHROMEDRIVER):
            servicio = Service(executable_path=cfg.RUTA_CHROMEDRIVER)
            driver = webdriver.Chrome(service=servicio, options=opciones)
        else:
            driver = webdriver.Chrome(options=opciones)

        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['es-ES', 'es', 'en']
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                """
            }
        )
        return driver

    def cerrar(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    def __enter__(self):
        return self.driver

    def __exit__(self, *args):
        self.cerrar()

# ==========================================================
# HELPERS DE ESPERA
# ==========================================================

def esperar(segundos: float):
    time.sleep(segundos)

def esperar_elemento(driver, selector: str, timeout: int):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
    )

def sesion_iniciada(driver) -> bool:
    try:
        if "/accounts/login" in driver.current_url.lower():
            return False
        if driver.find_elements(By.CSS_SELECTOR, 'input[name="username"]'):
            return False
        return True
    except Exception:
        return False

# ==========================================================
# RECOLECCIÓN: PERFIL
# ==========================================================

def obtener_meta(driver, selector: str) -> str | None:
    elementos = driver.find_elements(By.CSS_SELECTOR, selector)
    return elementos[0].get_attribute("content") if elementos else None

def extraer_candidatos_biografia(driver, usuario, nombre_visible):
    candidatos = []
    vistos = set()
    excluir = {
        usuario.lower(),
        (nombre_visible or "").lower(),
        "seguir", "mensaje", "contactar", "más", "más información"
    }
    elementos = driver.find_elements(By.CSS_SELECTOR, "header [dir='auto'], header span")
    for elemento in elementos:
        try:
            if not elemento.is_displayed():
                continue
            texto = elemento.text.strip()
            if not texto or texto.lower() in excluir or texto in vistos:
                continue
            if re.search(r"\b(seguidores|seguidos|publicaciones)\b", texto, re.IGNORECASE):
                continue
            vistos.add(texto)
            candidatos.append(texto)
        except Exception:
            continue
    return candidatos

def recolectar_perfil(driver, cfg: type[Config]) -> dict:
    print(f"\nConsultando perfil @{cfg.USUARIO}...")
    driver.get(cfg.URL_PERFIL)
    esperar(4)

    titulo = obtener_meta(driver, 'meta[property="og:title"]')
    descripcion = obtener_meta(driver, 'meta[property="og:description"]')
    imagen = obtener_meta(driver, 'meta[property="og:image"]')

    nombre_visible = extraer_nombre_visible(titulo)
    candidatos = extraer_candidatos_biografia(driver, cfg.USUARIO, nombre_visible)
    posibles = [t for t in candidatos if len(t) <= 500 and not t.startswith("@")]
    biografia = max(posibles, key=len) if posibles else None

    return {
        "usuario": cfg.USUARIO,
        "url": cfg.URL_PERFIL,
        "nombre_visible": nombre_visible,
        "titulo": titulo,
        "biografia": biografia,
        "candidatos_biografia": candidatos,
        "descripcion_meta": descripcion,
        "imagen_meta": imagen,
        "seguidores": extraer_cantidad(descripcion, "seguidores"),
        "seguidos": extraer_cantidad(descripcion, "seguidos"),
        "publicaciones_total": extraer_cantidad(descripcion, "publicaciones"),
        "fecha_recoleccion": fecha_actual()
    }

# ==========================================================
# RECOLECCIÓN: PUBLICACIONES
# ==========================================================

def recolectar_enlaces_publicaciones(driver, cfg: type[Config]) -> list[str]:
    driver.get(cfg.URL_PERFIL)
    esperar(4)
    for _ in range(4):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        esperar(2)

    enlaces = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"], a[href*="/reel/"]')
    urls = []
    vistos = set()
    for enlace in enlaces:
        if len(urls) >= cfg.LIMITE_PUBLICACIONES:
            break
        try:
            href = enlace.get_attribute("href")
            if not href or href in vistos:
                continue
            vistos.add(href)
            urls.append(href)
        except Exception:
            continue

    print(f"\nPublicaciones encontradas en el perfil: {len(urls)}")
    return urls

def extraer_fecha_publicacion(driver) -> str | None:
    try:
        time_elements = driver.find_elements(By.CSS_SELECTOR, "time")
        for t in time_elements:
            dt = t.get_attribute("datetime")
            if dt:
                return dt
    except Exception:
        pass
    return None

def extraer_datos_publicacion(driver, url: str, cfg: type[Config]) -> dict:
    driver.get(url)
    esperar(3)

    og_image = obtener_meta(driver, 'meta[property="og:image"]')
    og_desc = obtener_meta(driver, 'meta[property="og:description"]')
    
    url_imagen = og_image
    likes = None
    comentarios = None
    caption = None

    if og_desc:
        match_likes = re.search(r"([\d.,]+)\s*(?:likes|Me gusta)", og_desc, re.IGNORECASE)
        if match_likes:
            likes = int(match_likes.group(1).replace(".", "").replace(",", ""))

        match_comments = re.search(r"([\d.,]+)\s*(?:comments|comentarios)", og_desc, re.IGNORECASE)
        if match_comments:
            comentarios = int(match_comments.group(1).replace(".", "").replace(",", ""))

        match_caption = re.search(r':\s*"(.*)"', og_desc, re.DOTALL)
        if match_caption:
            caption = match_caption.group(1).strip()

    if not url_imagen:
        selectores = [
            'article img[src*="scontent"]',
            'main img[src*="scontent"]',
            'div[role="dialog"] img[src*="scontent"]'
        ]
        for selector in selectores:
            try:
                imagenes = driver.find_elements(By.CSS_SELECTOR, selector)
                for img in imagenes:
                    src = img.get_attribute("src")
                    if url_imagen_valida(src):
                        url_imagen = src
                        break
                if url_imagen:
                    break
            except Exception:
                continue

    fecha_dt = extraer_fecha_publicacion(driver)

    return {
        "url_publicacion": url,
        "url_imagen": url_imagen,
        "likes": likes,
        "comentarios": comentarios,
        "caption": caption,
        "fecha_publicacion_dt": fecha_dt,
        "fecha_recoleccion": fecha_actual()
    }

class DescargadorImagenes:
    def __init__(self, carpeta: Path, timeout: int = 20):
        self.carpeta = carpeta
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })

    def _nombre_desde_url(self, url: str, indice: int) -> str:
        try:
            ruta = urlparse(url).path
            base = os.path.basename(ruta).split("?")[0]
            if base and len(base) > 5:
                return f"{indice:03d}_{base}"
        except Exception:
            pass
        return f"{indice:03d}_imagen.jpg"

    def descargar(self, url: str, indice: int) -> str | None:
        if not url_imagen_valida(url):
            return None
        try:
            respuesta = self.session.get(url, timeout=self.timeout, stream=True)
            respuesta.raise_for_status()
            nombre = limpiar_nombre_archivo(self._nombre_desde_url(url, indice))
            ruta = self.carpeta / nombre
            with open(ruta, "wb") as archivo:
                for chunk in respuesta.iter_content(chunk_size=8192):
                    archivo.write(chunk)
            return str(ruta)
        except Exception as error:
            print(f"    Error al descargar: {error}")
            return None

def recolectar_publicaciones(driver, cfg: type[Config], descargador: DescargadorImagenes) -> list[dict]:
    urls = recolectar_enlaces_publicaciones(driver, cfg)
    if not urls:
        print("No se encontraron publicaciones.")
        return []

    publicaciones = []
    total = len(urls)

    for indice, url in enumerate(urls, start=1):
        print(f"\n[{indice}/{total}] Procesando publicación...")
        datos = extraer_datos_publicacion(driver, url, cfg)

        if datos["url_imagen"]:
            ruta_local = descargador.descargar(datos["url_imagen"], indice)
            datos["ruta_imagen_local"] = ruta_local
        else:
            datos["ruta_imagen_local"] = None

        datos["usuario"] = cfg.USUARIO
        publicaciones.append(datos)
        esperar(cfg.PAUSA_ENTRE_POSTS)

    print(f"\nPublicaciones procesadas: {len(publicaciones)}")
    return publicaciones

# ==========================================================
# RECOLECCIÓN: SEGUIDORES / SEGUIDOS
# ==========================================================

class ModalSeguidores:
    def __init__(self, driver, cfg: type[Config]):
        self.driver = driver
        self.cfg = cfg

    def _localizar_enlace(self, texto_buscado: str):
        try:
            for a in self.driver.find_elements(By.CSS_SELECTOR, "header a"):
                try:
                    if texto_buscado in a.text.strip().lower():
                        return a
                except Exception:
                    continue
        except Exception:
            pass
        try:
            return self.driver.find_element(By.XPATH, f"//a[.//span[contains(text(), '{texto_buscado}')]]")
        except Exception:
            return None

    def _abrir(self, tipo: str):
        texto_buscado = "seguidores" if tipo == "followers" else "seguidos"
        self.driver.get(self.cfg.URL_PERFIL)
        esperar(5)
        enlace = self._localizar_enlace(texto_buscado)
        if not enlace:
            return None
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", enlace)
            esperar(1)
            enlace.click()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", enlace)
            except Exception:
                return None
        try:
            esperar_elemento(self.driver, 'div[role="dialog"]', self.cfg.TIMEOUT_MEDIO)
        except Exception:
            return None
        esperar(3)
        return self._contenedor_scroll()

    def _contenedor_scroll(self):
        candidatos = [
            'div[role="dialog"] ._aano', 'div[role="dialog"] .isgrP',
            'div[role="dialog"] div[style*="overflow-y"]', 'div[role="dialog"] div[style*="overflow"]',
            'div[role="dialog"] ul',
        ]
        for selector in candidatos:
            encontrados = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if encontrados:
                return encontrados[0]
        dialogos = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"]')
        return dialogos[0] if dialogos else None

    def _scroll(self, contenedor, max_intentos=25):
        ultimo_alto = 0
        sin_cambio = 0
        for _ in range(max_intentos):
            nombres_actuales = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"] a[href]')
            if len(nombres_actuales) >= self.cfg.LIMITE_NOMBRES:
                break
            try:
                alto = self.driver.execute_script("return arguments[0].scrollHeight;", contenedor)
            except Exception:
                break
            if alto == ultimo_alto:
                sin_cambio += 1
                if sin_cambio >= 3:
                    break
            else:
                sin_cambio = 0
            ultimo_alto = alto
            try:
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", contenedor)
            except Exception:
                break
            esperar(2)

    def _extraer_nombres(self) -> set[str]:
        nombres = set()
        enlaces = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"] a[href]')
        for enlace in enlaces:
            if len(nombres) >= self.cfg.LIMITE_NOMBRES:
                break
            try:
                href = enlace.get_attribute("href")
                if not href: continue
                partes = urlparse(href).path.strip("/").split("/")
                if len(partes) != 1: continue
                nombre = partes[0]
                if nombre.lower() in self.cfg.RUTAS_EXCLUIDAS: continue
                if nombre.lower() == self.cfg.USUARIO.lower(): continue
                if not es_nombre_usuario_valido(nombre): continue
                nombres.add(nombre)
            except Exception:
                continue
        return nombres

    def _cerrar(self):
        try:
            webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            esperar(1)
        except Exception:
            pass

    def recolectar(self, tipo: str):
        print(f"\nConsultando lista de {tipo}...")
        contenedor = self._abrir(tipo)
        if contenedor is None:
            return [], "modal_no_abierto"
        self._scroll(contenedor)
        nombres = self._extraer_nombres()
        self._cerrar()
        lista = sorted(nombres, key=str.lower)
        estado = "nombres_visibles_parciales" if lista else "lista_no_visible"
        print("Nombres encontrados:", len(lista))
        return lista, estado

# ==========================================================
# FLUJO PRINCIPAL
# ==========================================================

def asegurar_sesion(driver, cfg: type[Config]):
    driver.get(cfg.BASE_URL)
    esperar(3)
    if sesion_iniciada(driver):
        print(f"\nSesión activa detectada en '{cfg.NOMBRE_PERFIL}'.")
        return True
    print(f"\nNo se detectó sesión activa en '{cfg.NOMBRE_PERFIL}'.")
    print("Inicia sesión manualmente en la ventana de Brave (usa tu CUENTA SECUNDARIA).")
    input("Cuando veas tu feed, pulsa ENTER...")
    driver.get(cfg.BASE_URL)
    esperar(3)
    return sesion_iniciada(driver)

def ejecutar():
    cfg = Config
    cfg.CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    descargador = DescargadorImagenes(cfg.CARPETA_IMAGENES, timeout=cfg.TIMEOUT_DESCARGA)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n⚠️ ADVERTENCIA: No se encontró la variable GEMINI_API_KEY en tu archivo .env.")
        print("El script continuará, pero no se realizará el análisis psicológico.\n")

    with DriverInstagram(cfg) as driver:
        if not asegurar_sesion(driver, cfg):
            print("Aún no hay sesión. Abortando.")
            return

        perfil = recolectar_perfil(driver, cfg)
        publicaciones = recolectar_publicaciones(driver, cfg, descargador)

        modal = ModalSeguidores(driver, cfg)
        seguidores, estado_seguidores = modal.recolectar("followers")
        seguidos, estado_seguidos = modal.recolectar("following")

        perfil["estado_lista_seguidores"] = estado_seguidores
        perfil["estado_lista_seguidos"] = estado_seguidos

        datos_seguidores = [{"usuario_seguidor": n, "perfil_consultado": cfg.USUARIO} for n in seguidores]
        datos_seguidos = [{"usuario_seguido": n, "perfil_consultado": cfg.USUARIO} for n in seguidos]

        captions = [p["caption"] for p in publicaciones if p.get("caption")]
        
        analisis_gemini = {}
        if captions and api_key:
            analisis_gemini = analizar_personalidad_big_five(captions, api_key)
        else:
            if not captions:
                print("\n⚠️ No se encontraron descripciones para analizar.")
                analisis_gemini = {"error": "No hay textos válidos."}
            elif not api_key:
                analisis_gemini = {"error": "Falta la API Key."}

        resultado_consolidado = {
            "perfil": perfil,
            "publicaciones": publicaciones,
            "seguidores": datos_seguidores,
            "seguidos": datos_seguidos,
            "analisis_big_five": analisis_gemini,
            "fecha_ejecucion": fecha_actual()
        }

        archivo_json = cfg.CARPETA_SALIDA / "datos_instagram_completo.json"
        with open(archivo_json, "w", encoding="utf-8") as f:
            json.dump(resultado_consolidado, f, ensure_ascii=False, indent=2)

        print(f"\nArchivo JSON consolidado creado en: {archivo_json}")

        print("\n========== RESUMEN ==========")
        print("Usuario:", cfg.USUARIO)
        print("Publicaciones procesadas:", len(publicaciones))
        print("Seguidores capturados:", len(seguidores))
        print("Seguidos capturados:", len(seguidos))
        
        if "error" not in analisis_gemini and analisis_gemini:
            print("\n--- PERFIL PSICOLÓGICO (Big Five) ---")
            print(f"Apertura: {analisis_gemini.get('apertura', {}).get('puntaje')}/10")
            print(f"Responsabilidad: {analisis_gemini.get('responsabilidad', {}).get('puntaje')}/10")
            print(f"Extraversión: {analisis_gemini.get('extraversion', {}).get('puntaje')}/10")
            print(f"Amabilidad: {analisis_gemini.get('amabilidad', {}).get('puntaje')}/10")
            print(f"Neuroticismo: {analisis_gemini.get('neuroticismo', {}).get('puntaje')}/10")
            print(f"Resumen: {analisis_gemini.get('resumen_perfil')}")

        input("\nPulsa ENTER para cerrar el navegador...")

if __name__ == "__main__":
    ejecutar()