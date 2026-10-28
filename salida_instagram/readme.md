instagram_recolectar ejecuta brave.exe con --user-data-dir apuntando a la carpeta de perfiles y --profile-directory=Default. Además inyecta un script CDP que oculta navigator.webdriver y simula idiomas/plugins para reducir la huella de automatización.

recolectar_perfil() saca el nombre visible, biografía, imagen, y los contadores de seguidores/seguidos/publicaciones desde los del HTML.

recolectar_enlaces_publicaciones() hace scroll en el perfil y recoge hasta 25 URLs de posts/reels.

recolectar_publicaciones() entra a cada URL, espera a que cargue el

, y extraer_datos_publicacion() busca la imagen real del post (excluyendo la foto de perfil por contenedor y por tamaño).
DescargadorImagenes baja cada imagen a salida_instagram/imagenes/ con requests, y guarda la ruta local en el registro.

ModalSeguidores abre el modal haciendo clic en el enlace del contador, localiza el contenedor scrollable, hace scroll hasta 50 nombres, y extrae los href de perfil válidos. Cierra el modal con ESC.

Exportador escribe perfil.csv, publicaciones.csv, seguidores.csv, seguidos.csv y datos_instagram.json en salida_instagram/.

La razón del porque usar Brave como navegador son:

Es un navegador basado en chromium y que se conecta con Selenium
Se probó con navegadores Chrome, Tor y Edge, Tor fue descartado por la complejidad de su estructura, Edge por no poder conectar satisfactoriamente con Selenium y Chrome porque Instagram detectaba la cuenta como un bot.
Brave guarda la sesión de Instagram y sus credenciales en el perfil principal.
Algunos Errores y sus respectivas correcciones fueron:

Selenium abria directamente un perfil nuevo en el navegador, detectad como un bot por Instagram y mostrando el mensaje genérico "La información de inicio de sesión que ingresaste es incorrecta" corregido con las credenciales guardadas, lo que vendría a ser las cookies de inicio de sesión que funcionan como llave de ingreso para el scrapeo.
La versión de Chromium utilizada por Selenium fallaba al conectarse con Brave al estar desactualizada, se optó por descargar chromedriver-win64.zip de la versión 155.0.8059.39 se paso a 155.0.8059.80 para estar actualizada a la versión 1.97.57 de Brave.
Para conectar el perfil de Brave junto con Selenium y no abriera uno nuevo, se añadió dentro del código una ruta hacia el perfil de Usuario de Windows y otra hacia el perfil Default de Brave.

Adiciones Gemini APIKey:
- Se generó una APIKey de Gemini en el programa Google AI Studio.
- La APIKey se encuentra dentro del archivo .env, por motivos de seguridad este archivo ha sido omitido al ser subido en Github.
- se ha mejorado el json que imprime con los datos para que solo imprima en un solo archivo
- Se ha arreglado un bug en el cual el programa no procesaba correctamente la descripción, número de likes, comentarios y reposteos en la publicación.

Consideraciones:

El código fue realizado en Visual Studio Code versión 1.142.0
Chromium 155.0.8059.80
Brave 1.97.57 con Chromium 155.0.8059.80
Bibliografía:

ChatGPT (Formulación y estructuración del programa)
DeepSeek (Generación de código)
Gemini (Orden de ánalisis de los 5 grandes)

Libererías Necesarias:
selenium
requests
pandas
python-dotenv
google-genai

Se han incluido dos nuevos archivos; benford.py y seguidores.py

seguidores.py permite sacar la lista de seguidores hasta 5000, tardandose al rededor de una hora al sacarlo, se debe scrollear manualmente en la sección de seguidores/seguridos para conseguirse la información.

El archivo benford.py permite hacer una comparativa entre la ley de benfod y la ley de benford del número de seguidos y seguidores en un gráfico, tomando el primer dígito del número de seguidos  o seguidores para la comparativa.

El archivo main fue incluido la impresión en archivo json de la ley de Benfod.