"""
Módulo para el análisis gráfico de la Ley de Benford.
"""
import matplotlib.pyplot as plt
import os
from collections import Counter
from pathlib import Path

# Distribución esperada según Benford para el primer dígito (1 al 9)
ESPERADO_BENFORD = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]

def generar_grafico_benford(numeros: list[int], titulo: str, nombre_archivo: str, carpeta_salida: Path):
    """
    Genera una gráfica comparando la distribución observada con la Ley de Benford.
    """
    if not numeros:
        print(f"  ⚠️ No hay números para generar la gráfica: {titulo}")
        return

    # Extraer el primer dígito de cada número
    primeros_digitos = []
    for n in numeros:
        str_n = str(abs(n)).strip()
        if str_n and str_n[0] != '0':
            primeros_digitos.append(int(str_n[0]))

    conteo = Counter(primeros_digitos)
    total = len(primeros_digitos)
    
    if total == 0:
        print(f"  ⚠️ No se encontraron dígitos válidos para: {titulo}")
        return

    # Calcular porcentajes observados (para los dígitos 1 al 9)
    observados = [(conteo.get(i, 0) / total) * 100 for i in range(1, 10)]

    # Crear la gráfica
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Posiciones de las barras
    x = range(1, 10)
    ancho = 0.35

    # Barras de Benford (Azul)
    barras_benford = ax.bar([i - ancho/2 for i in x], ESPERADO_BENFORD, ancho, label='Ley de Benford (Esperado)', color='#2196F3', alpha=0.8)
    # Barras Observadas (Naranja)
    barras_obs = ax.bar([i + ancho/2 for i in x], observados, ancho, label='Observado', color='#FF9800', alpha=0.8)

    # Añadir los valores encima de las barras
    for barra in barras_benford:
        altura = barra.get_height()
        ax.annotate(f'{altura:.1f}%', xy=(barra.get_x() + barra.get_width() / 2, altura), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    
    for barra in barras_obs:
        altura = barra.get_height()
        ax.annotate(f'{altura:.1f}%', xy=(barra.get_x() + barra.get_width() / 2, altura), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)

    ax.set_xlabel('Primer Dígito')
    ax.set_ylabel('Porcentaje (%)')
    ax.set_title(f'Análisis de Benford: {titulo}\n(Total analizados: {total})')
    ax.set_xticks(x)
    ax.set_xticklabels(x)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Guardar
    ruta = carpeta_salida / nombre_archivo
    plt.tight_layout()
    plt.savefig(ruta, dpi=150)
    plt.close()
    print(f"  ✅ Gráfico guardado en: {ruta}")