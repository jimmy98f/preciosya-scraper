import requests
import os
from supabase import create_client
from datetime import datetime

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
SUPERMERCADO_ID = 1

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORIAS = ["aceite", "arroz", "leche", "pan", "azucar", "fideos", "detergente", "shampoo", "yogurt", "jugo"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json",
    "Accept-Language": "es-CL,es;q=0.9",
    "Referer": "https://www.lider.cl/",
}

def buscar_productos(query):
    url = f"https://apps.lider.cl/catalogo/bff/products/search?query={query}&start=0&count=20"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {res.status_code} — query: {query}")
        print(f"Raw (200 chars): {res.text[:200]}")
        data = res.json()
        productos = data.get("data", {}).get("products", []) or data.get("products", [])
        print(f"Productos encontrados: {len(productos)}")
        return productos
    except Exception as e:
        print(f"Error en {query}: {e}")
        return []

def guardar_precio(producto_raw):
    try:
        nombre = (producto_raw.get("displayName") or producto_raw.get("name") or "").strip()
        marca = producto_raw.get("brand", "") or ""
        imagen = ""
        imagenes = producto_raw.get("images", [])
        if imagenes:
            imagen = imagenes[0].get("url", "") if isinstance(imagenes[0], dict) else str(imagenes[0])
        categoria = producto_raw.get("category", "") or ""

        precio = None
        precio_raw = producto_raw.get("price", {}) or {}
        if isinstance(precio_raw, dict):
            precio = precio_raw.get("BasePriceSales") or precio_raw.get("BasePriceReference") or precio_raw.get("price")
        elif isinstance(precio_raw, (int, float)):
            precio = precio_raw

        if not precio:
            precio = producto_raw.get("price") or producto_raw.get("precio")

        if not nombre or not precio:
            return

        precio = int(float(precio))

        existing = supabase.table("productos").select("id").eq("nombre", nombre).execute()
        if existing.data:
            producto_id = existing.data[0]["id"]
        else:
            nuevo = supabase.table("productos").insert({
                "nombre": nombre,
                "marca": str(marca),
                "categoria": str(categoria),
                "imagen_url": str(imagen),
            }).execute()
            producto_id = nuevo.data[0]["id"]

        precio_existing = supabase.table("precios").select("id").eq("producto_id", producto_id).eq("supermercado_id", SUPERMERCADO_ID).execute()
        if precio_existing.data:
            supabase.table("precios").update({
                "precio": precio,
                "ultima_verificacion": datetime.now().isoformat(),
            }).eq("id", precio_existing.data[0]["id"]).execute()
        else:
            supabase.table("precios").insert({
                "producto_id": producto_id,
                "supermercado_id": SUPERMERCADO_ID,
                "precio": precio,
            }).execute()

        print(f"✅ {nombre} — ${precio:,}")

    except Exception as e:
        print(f"Error guardando: {e} — data: {str(producto_raw)[:100]}")

def main():
    print(f"🛒 Iniciando scraper Lider — {datetime.now()}")
    for categoria in CATEGORIAS:
        print(f"\n🔍 Buscando: {categoria}")
        productos = buscar_productos(categoria)
        for p in productos:
            guardar_precio(p)
    print("\n✅ Scraper Lider finalizado")

if __name__ == "__main__":
    main()
