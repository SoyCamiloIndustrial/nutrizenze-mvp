# Despliegue de Vital Trace en Railway con subdominio de Namecheap

## Antes de empezar

- Esta versión guarda los datos **en memoria**. Cada despliegue o reinicio vuelve a los datos de demostración.
- Por la Ley 1581 de 2012, **no cargues datos reales de pacientes** hasta tener tres cosas: una base de datos cifrada, usuarios individuales y un registro de consentimiento. Mientras tanto, usa solo `DEMO_MODE=1`.
- Corre con un solo proceso (`--workers 1`) porque los datos y el bloqueo de intentos de login viven en memoria.

## 1. Railway

1. Entra a https://railway.com, haz clic en **New Project → Deploy from GitHub repo** y elige `SoyCamiloIndustrial/nutrizenze-mvp` (rama `main`).
2. Railway detecta Python por `requirements.txt` y `.python-version`, y arranca con el comando de `railway.json` (gunicorn). El health check apunta a `/api/health`.
3. En **Variables**, agrega:

   | Variable | Valor |
   |---|---|
   | `APP_ENV` | `production` |
   | `SECRET_KEY` | el resultado de `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `DEMO_MODE` | `1` |
   | `DEMO_PASSWORD` | una contraseña de 12 caracteres o más |

   Sin `SECRET_KEY`, o con una `DEMO_PASSWORD` corta, la app no arranca a propósito.
4. Ve a **Settings → Networking → Generate Domain** para tener una URL de prueba (`*.up.railway.app`). Abre esa URL y verifica que puedes entrar con `medico.demo` y la contraseña.

## 2. Subdominio en Namecheap

Ejemplo: `app.tudominio.com`.

1. En Railway, ve a **Settings → Networking → Custom Domain** y escribe `app.tudominio.com`. Railway te mostrará un **CNAME** de destino y, a veces, un registro **TXT** de verificación.
2. En Namecheap, entra a **Domain List → Manage** (en tu dominio) **→ Advanced DNS → Add New Record**:
   - Tipo **CNAME Record**, Host `app` (solo la parte del subdominio), Value el destino que mostró Railway, TTL `Automatic`.
   - Si Railway pidió un TXT, agrégalo copiando exactamente el Host y el Value que muestra.
3. Espera a que el DNS propague (de minutos a unas horas). Railway emite el certificado HTTPS automáticamente cuando valida el dominio.

## 3. Verificación

- `https://app.tudominio.com/api/health` responde `{"status": "healthy"}`.
- `https://app.tudominio.com/medico` sin sesión redirige a `/login`.
- Al entrar como `paciente.uno` solo se ve el resumen de ese paciente.

## Usuarios demo

| Usuario | Rol | Ve |
|---|---|---|
| `medico.demo` | Médico | Todos los pacientes, historial, alertas y la API |
| `paciente.uno` | Paciente | Solo el resumen de "Paciente Demo Uno" |
| `paciente.dos` | Paciente | Solo el resumen de "Paciente Demo Dos" |

Los tres usan la contraseña de `DEMO_PASSWORD`.
