"""
Módulo para la extracción y paginación de seguidores y seguidos.
"""
import time
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Importamos la función de Benford
from benford import generar_grafico_benford

class ExtractorSeguidores:
    def __init__(self, driver, cfg, limite_maximo=5000):
        self.driver = driver
        self.cfg = cfg
        self.limite_maximo = limite_maximo

    def _localizar_enlace(self, tipo):
        texto_buscado = "seguidores" if tipo == "followers" else "seguidos"
        try:
            for a in self.driver.find_elements(By.CSS_SELECTOR, "header a"):
                if texto_buscado in a.text.strip().lower():
                    return a
        except Exception:
            pass
        return None

    def _abrir_modal(self, tipo):
        self.driver.get(self.cfg.URL_PERFIL)
        time.sleep(5)
        
        enlace = self._localizar_enlace(tipo)
        if not enlace:
            print(f"  ⚠️ No se encontró el enlace para {tipo}.")
            return False
            
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", enlace)
            time.sleep(1)
            enlace.click()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", enlace)
            except Exception:
                print(f"  ❌ No se pudo hacer clic en {tipo}.")
                return False

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"]'))
            )
            time.sleep(3) 
            return True
        except Exception:
            print("  ❌ No apareció el modal.")
            return False

    def _obtener_contenedor_scroll(self):
        try:
            # Este es el div con overflow: hidden auto que encontraste
            contenedor = self.driver.find_element(
                By.CSS_SELECTOR, 'div[role="dialog"] div[style*="overflow"]'
            )
            return contenedor
        except Exception:
            dialogos = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"]')
            return dialogos[0] if dialogos else None

    def _paginacion_scroll(self, contenedor, tipo):
        print(f"  ⏳ Iniciando paginación (límite: {self.limite_maximo})...")
        
        intentos_sin_cambio = 0
        max_intentos_sin_cambio = 5
        ultimo_conteo = 0

        for iteracion in range(100):
            enlaces = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"] a[href]')
            conteo_actual = len(enlaces)
            
            if conteo_actual >= self.limite_maximo:
                print(f"  ✅ Límite de {self.limite_maximo} alcanzado.")
                break

            if conteo_actual == ultimo_conteo:
                intentos_sin_cambio += 1
                print(f"    ⚠️ Sin cambios ({intentos_sin_cambio}/{max_intentos_sin_cambio}).")
                if intentos_sin_cambio >= max_intentos_sin_cambio:
                    print("  🏁 No hay más elementos para cargar.")
                    break
            else:
                print(f"    [Iteración {iteracion+1}] Enlaces encontrados: {conteo_actual}")
                intentos_sin_cambio = 0

            ultimo_conteo = conteo_actual

            try:
                # Scroll usando JS sobre el div con overflow
                self.driver.execute_script("""
                    const dialog = document.querySelector('div[role="dialog"]');
                    const scrollable = dialog.querySelector('div[style*="overflow"]');
                    if (scrollable) {
                        scrollable.scrollTop = scrollable.scrollHeight;
                    }
                """)
                
                print("    ⏳ Esperando 15 segundos para cargar la siguiente página...")
                time.sleep(15) 
                
            except Exception as e:
                print(f"    ❌ Error en el scroll: {e}")
                break
        
        print("  🏁 Fin de la paginación.")

    def _extraer_nombres(self):
        nombres = set()
        enlaces = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"] a[href]')
        
        for enlace in enlaces:
            try:
                href = enlace.get_attribute("href")
                if not href: continue
                
                partes = urlparse(href).path.strip("/").split("/")
                if len(partes) != 1: continue
                
                nombre = partes[0]
                if nombre.lower() in self.cfg.RUTAS_EXCLUIDAS: continue
                if nombre.lower() == self.cfg.USUARIO.lower(): continue
                if not (nombre and len(nombre) <= 30): continue
                
                nombres.add(nombre)
            except Exception:
                continue
        return nombres

    def extraer(self, tipo):
        print(f"\n🔍 Extrayendo {tipo}...")
        
        if not self._abrir_modal(tipo):
            return [], "modal_no_abierto"

        contenedor = self._obtener_contenedor_scroll()
        if not contenedor:
            print("  ❌ No se encontró el contenedor de scroll.")
            return [], "contenedor_no_encontrado"

        self._paginacion_scroll(contenedor, tipo)
        
        print("  📥 Extrayendo nombres finales...")
        nombres = self._extraer_nombres()
        lista_final = sorted(nombres, key=str.lower)

        try:
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
        except Exception:
            pass

        estado = "completo" if len(lista_final) > 12 else "parcial"
        print(f"  ✅ Total extraídos: {len(lista_final)}")
        return lista_final, estado