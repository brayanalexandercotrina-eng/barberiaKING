# Barbería 1Barber

API REST para administrar citas de barbería con FastAPI. Esta adaptación de la guía conserva el caso de uso de 1Barber: usa PostgreSQL en Supabase para persistir las citas, Render para desplegar la API y Firebase Authentication para validar tokens de clientes. El bloque de cotizaciones de calculadoras cloud de la guía se omite.

## Funciones

- Consultar, crear, actualizar y eliminar citas desde `/api/v1/barberia`.
- Guardar datos con SQLAlchemy en PostgreSQL; para desarrollo local se usa `barberia.db` (SQLite).
- Verificar Firebase ID tokens en las rutas de citas cuando se configura la cuenta de servicio.
- Consultar Swagger en `/docs` y estado del servicio en `/health`.
- Construir una imagen Docker con el `Dockerfile` incluido.

Una base de datos nueva se inicializa con dos citas de demostración. No se vuelven a insertar cuando ya hay registros.

## Ejecutar localmente

Desde `backend-Barberia-crud`:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Abre `http://127.0.0.1:8000/docs`. Sin credenciales Firebase, la API permite llamadas locales para facilitar el desarrollo. Para conectar una base de datos, define `DATABASE_URL` antes de iniciar el servicio.

## Supabase (PostgreSQL)

1. Crea un proyecto PostgreSQL en Supabase y copia la URI de conexión directa desde **Connect → URI**.
2. Sustituye `[YOUR-PASSWORD]` localmente por la contraseña de la base. No publiques la URI ni la guardes en Git.
3. Configura la URI como `DATABASE_URL`. El backend normaliza los esquemas `postgres://` y `postgresql://` a psycopg y solicita SSL para hosts `supabase.co`.
4. Al iniciar, SQLAlchemy crea la tabla `citas_barberia` si aún no existe.

## Firebase Authentication

1. En Firebase Console, crea un proyecto para 1Barber y habilita **Authentication → Sign-in method → Email/Password**.
2. En **Project settings → Service accounts**, genera una clave privada para el backend. Guárdala de forma segura; no la subas al repositorio.
3. Define `FIREBASE_CREDENTIALS_JSON` con el contenido JSON de esa clave y `REQUIRE_FIREBASE_AUTH=true` en el entorno del servidor.
4. El cliente web o móvil inicia sesión en Firebase y envía el ID token en las solicitudes a las rutas de citas como `Authorization: Bearer <ID_TOKEN>`.

Si `REQUIRE_FIREBASE_AUTH=true` no tiene una credencial Firebase configurada, la API devuelve 503 en las rutas de citas. La ruta de salud y la documentación permanecen accesibles para supervisión y consulta.

## Despliegue en Render

1. Sube el repositorio a GitHub. Render debe usar como **Root Directory** `backend-Barberia-crud`.
2. Crea un **Web Service** conectado al repositorio. Elige el runtime Docker para usar el `Dockerfile` incluido (o Python con `pip install -r requirements.txt` y `uvicorn main:app --host 0.0.0.0 --port $PORT`).
3. En **Environment Variables**, define `DATABASE_URL` con la URI PostgreSQL de Supabase, `FIREBASE_CREDENTIALS_JSON` con el JSON de la cuenta de servicio y `REQUIRE_FIREBASE_AUTH=true`.
4. Usa `/health` como health check path. Al desplegar, abre `/docs` para explorar la API.

El filesystem de un servicio gratuito puede ser efímero; por eso el despliegue debe usar Supabase mediante `DATABASE_URL` y no depender del SQLite local.

## Rutas

| Método | Ruta | Uso |
| --- | --- | --- |
| GET | `/` | Mensaje de bienvenida y enlace a la documentación |
| GET | `/health` | Estado del servicio |
| GET | `/api/v1/barberia` | Listar citas |
| GET | `/api/v1/barberia/{cita_id}` | Consultar una cita |
| POST | `/api/v1/barberia` | Crear una cita |
| PUT | `/api/v1/barberia/{cita_id}` | Actualizar una cita |
| DELETE | `/api/v1/barberia/{cita_id}` | Eliminar una cita |

Ejemplo de cita:

```json
{
  "id": 3,
  "nombre_cliente": "Ana López",
  "servicio_solicitado": "Corte y barba",
  "precio_servicio": 30000,
  "atendido": false
}
```

## Publicar en GitHub y desplegar en Render

El repositorio remoto de este proyecto es `https://github.com/brayanalexandercotrina-eng/barberiaKING`. En GitHub, verifica que el backend esté bajo `backend-Barberia-crud` y que se hayan publicado `main.py`, `requirements.txt` y `Dockerfile`. No subas el entorno virtual, cachés, bases locales ni claves de Firebase.

### Ignorar archivos locales y generar dependencias

El `.gitignore` de la raíz ya excluye `venv`, `__pycache__`, archivos `.pyc`, bases SQLite y credenciales. Para regenerar la lista de dependencias desde el entorno virtual activo, abre una terminal en `backend-Barberia-crud` y ejecuta:

```powershell
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip freeze > requirements.txt
```

Antes de guardar el archivo, comprueba que incluya FastAPI, Uvicorn, SQLAlchemy, `psycopg` y `firebase-admin`, que necesita este backend.

Si Git ya rastreaba carpetas locales, retíralas del índice sin borrarlas del computador:

```powershell
git rm -r --cached --ignore-unmatch backend-Barberia-crud/venv backend-Barberia-crud/__pycache__
```

### Guardar y subir los cambios

Desde la raíz del repositorio, revisa los cambios y publica el commit en la rama conectada a GitHub:

```powershell
git status
git add .gitignore README.md backend-Barberia-crud/main.py backend-Barberia-crud/requirements.txt backend-Barberia-crud/Dockerfile
git commit -m "Preparar API de barbería para despliegue cloud"
git push origin main
```

### Crear el servicio gratuito en Render

1. Inicia sesión en Render con GitHub y elige **New + → Web Service**.
2. Selecciona el repositorio `barberiaKING` y conecta la rama `main`.
3. Configura **Root Directory** como `backend-Barberia-crud` y el runtime como **Docker**.
4. Añade `DATABASE_URL`, `FIREBASE_CREDENTIALS_JSON` y `REQUIRE_FIREBASE_AUTH=true` en **Environment Variables**. Usa los secretos de tus propios proyectos Supabase y Firebase; nunca los guardes en GitHub.
5. Configura `/health` como ruta de comprobación y crea el servicio. Al terminar el despliegue, confirma que `/docs` carga y que las rutas de citas piden un token Firebase.

Render debe conectarse a PostgreSQL en Supabase mediante `DATABASE_URL`; el SQLite local es solo para desarrollo porque el disco de un servicio gratuito puede ser efímero.
