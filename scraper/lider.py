import requests
import os
from supabase import create_client
from datetime import datetime

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
SUPERMERCADO_ID = 2  # Jumbo

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORIAS = ["aceite", "arroz", "leche", "pan", "azucar", "fideos", "detergente", "shampoo", "yogurt", "jugo"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-CL,es;q=0.9",
}

def buscar_productos(query):
    url = f"https://www.jumbo.cl/api/catalog_system/pub/products/search/{query}?O=OrderByScoreDESC&_from=0&_to=19"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {res.status_code} — query: {query}")
        print(f"Raw (200 chars): {res.text[:200]}")
        productos = res.json()
        print(f"Productos encontrados: {len(productos)}")
        return productos if isinstance(productos, list) else []
    except Exception as e:
        print(f"Error en {query}: {e}")
        return []

def guardar_precio(producto_raw):
    try:
        nombre = producto_raw.get("productName", "").strip()
        marca = producto_raw.get("brand", "")
        categoria = producto_raw.get("categories", [""])[0].replace("/", "").strip() if producto_raw.get("categories") else ""
        
        imagen = ""
        items = producto_raw.get("items", [])
        if items and items[0].get("images"):
            imagen = items[0]["images"][0].get("imageUrl", "")

        precio = None
        if items:
            sellers = items[0].get("sellers", [])
            if sellers:
                precio_raw = sellers[0].get("commertialOffer", {})
                precio = precio_raw.get("Price") or precio_raw.get("ListPrice")

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
    print(f"🛒 Iniciando scraper Jumbo — {datetime.now()}")
    for categoria in CATEGORIAS:
        print(f"\n🔍 Buscando: {categoria}")
        productos = buscar_productos(categoria)
        for p in productos:
            guardar_precio(p)
    print("\n✅ Scraper Jumbo finalizado")

if __name__ == "__main__":
    main()
