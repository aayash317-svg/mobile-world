import os

os.makedirs("static/images/products", exist_ok=True)
os.makedirs("static/images/shop", exist_ok=True)

assets = {
    "phone_oneplus.svg": ("#0066FF", "OnePlus Nord CE 4", "50MP OIS • 100W SuperVOOC"),
    "phone_samsung.svg": ("#1428A0", "Galaxy M35 5G", "6000mAh • 120Hz Super AMOLED"),
    "phone_redmi.svg": ("#FF6900", "Redmi Note 13 5G", "108MP ProLight • 120Hz"),
    "phone_realme.svg": ("#FFC90E", "Realme Narzo 70 Turbo", "Dimensity 7300 Turbo 5G"),
    "charger.svg": ("#0D9488", "67W GaN Fast Charger", "Dual Port Type-C + USB-A"),
    "cable.svg": ("#6366F1", "100W Braided Cable", "Heavy Duty Nylon 1.5m"),
    "glass.svg": ("#0284C7", "9D Tempered Glass", "Full Curved 9H Screen Armor"),
    "case.svg": ("#475569", "Armor Kickstand Case", "Military Drop Tested Hybrid"),
    "service_screen.svg": ("#E11D48", "Screen Replacement", "OEM Display • 1 Hr Express"),
    "service_battery.svg": ("#059669", "Battery Replacement", "Certified OEM Cell • 6M Warranty"),
}

for filename, (color, title, subtitle) in assets.items():
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1E293B"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
  </defs>
  <rect width="400" height="400" rx="24" fill="url(#bg)"/>
  <circle cx="200" cy="160" r="90" fill="{color}" opacity="0.2"/>
  <rect x="135" y="80" width="130" height="180" rx="16" fill="#1E293B" stroke="{color}" stroke-width="4"/>
  <circle cx="200" cy="240" r="6" fill="{color}"/>
  <rect x="150" y="100" width="100" height="120" rx="6" fill="#0F172A" stroke="#334155" stroke-width="2"/>
  <text x="200" y="310" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="18" font-weight="bold" fill="#F8FAFC" text-anchor="middle">{title}</text>
  <text x="200" y="338" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" fill="#94A3B8" text-anchor="middle">{subtitle}</text>
</svg>"""
    with open(os.path.join("static/images/products", filename), "w", encoding="utf-8") as f:
        f.write(svg)

print("Created all vector image assets successfully.")
