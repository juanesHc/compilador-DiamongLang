#!/usr/bin/env bash
# ═════════════════════════════════════════════════════════════════
#  DiamondLang 💎 — Generador de reportes JSON para la presentación
#  Reemplaza a las capturas pedidas si no se pueden generar
#  imágenes desde la terminal.
#
#  Uso:
#     1. Levanta el server:   python server.py
#     2. Ejecuta:             bash capturas/generar_reportes.sh
#     3. Quedan tres .json:
#          - cap1_errores_multiples.json
#          - cap2_sugerencia_ia.json (requiere ANTHROPIC_API_KEY)
#          - cap3_arbol_con_nodo_error.json
# ═════════════════════════════════════════════════════════════════

set -euo pipefail

URL="http://localhost:5000/parsear"
DIR="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(dirname "$DIR")"

# ── 1. Errores múltiples (recursivo, sin IA) ──
CODIGO=$(jq -Rs . < "$RAIZ/ejemplos_errores/errores_multiples_simples.dml")
curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -d "{\"codigo\": $CODIGO, \"metodo\": \"recursivo\", \"usar_ia\": false}" \
  > "$DIR/cap1_errores_multiples.json"
echo "✓ cap1_errores_multiples.json"

# ── 2. Sugerencia IA (recursivo, con IA) ──
curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -d "{\"codigo\": $CODIGO, \"metodo\": \"recursivo\", \"usar_ia\": true}" \
  > "$DIR/cap2_sugerencia_ia.json"
echo "✓ cap2_sugerencia_ia.json (vacío o con local si no hay ANTHROPIC_API_KEY)"

# ── 3. Árbol con nodo ERROR (predictivo, sin IA) ──
CODIGO_ARB=$(jq -Rs . < "$RAIZ/ejemplos_errores/bucle_para_incompleto.dml")
curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -d "{\"codigo\": $CODIGO_ARB, \"metodo\": \"predictivo\", \"usar_ia\": false}" \
  > "$DIR/cap3_arbol_con_nodo_error.json"
echo "✓ cap3_arbol_con_nodo_error.json"

echo ""
echo "Hecho. Inspecciona los archivos con:"
echo "  jq '.errores | length, .errores[0]' $DIR/cap1_errores_multiples.json"
