import requests
import os
from supabase import create_client
from datetime import datetime

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
SUPERMERCADO_ID = 1  # Lider

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORIAS = [
    "aceite",
    "arroz",
    "leche",
    "pan",
    "azucar",
    "fideos",
    "detergente",
    "shampoo",
    "yogurt",
    "jugo",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

def buscar_productos(query):
    url = f"https://www.lider.cl/supermercado/product/search?query={query}&page=0&count=20"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        return data.get("products", [])
    except Exception as e:
        print(f"Error buscando {query}: {e}")
        return []

def guardar_precio(producto_raw):
    try:
        nombre = producto_raw.get("displayName", "").strip()
        marca = producto_raw.get("brand", {}).get("name", "") if producto_raw.get("brand") else ""
        imagen = producto_raw.get("images", [{}])[0].get("url", "")
        categoria = producto_raw.get("category", {}).get("name", "") if producto_raw.get("category") else ""
        precio_raw = producto_raw.get("price", {})
        precio = precio_raw.get("BasePriceSales") or precio_raw.get("BasePriceReference")

        if not nombre or not precio:
            return

        precio = int(precio)

        # Buscar si el producto ya existe
        existing = supabase.table("productos").select("id").eq("nombre", nombre).execute()

        if existing.data:
            producto_id = existing.data[0]["id"]
        else:
            nuevo = supabase.table("productos").insert({
                "nombre": nombre,
                "marca": marca,
                "categoria": categoria,
                "imagen_url": imagen,
            }).execute()
            producto_id = nuevo.data[0]["id"]

        # Buscar si ya existe precio para este producto en Lider
        precio_existing = supabase.table("precios").select("id").eq("producto_id", producto_id).eq("supermercado_id", SUPERMERCADO_ID).execute()

        if precio_existing.data:
            supabase.table("precios").update({
                "precio": precio,
                "ultima_verificacion": datetime.now().isoformat(),
                "estado": "confirmado"
            }).eq("id", precio_existing.data[0]["id"]).execute()
        else:
            supabase.table("precios").insert({
                "producto_id": producto_id,
                "supermercado_id": SUPERMERCADO_ID,
                "precio": precio,
            }).execute()

        print(f"✅ {nombre} — ${precio:,}")

    except Exception as e:
        print(f"Error guardando producto: {e}")

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
