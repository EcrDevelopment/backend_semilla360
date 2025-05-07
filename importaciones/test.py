import io
from datetime import datetime
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.colors import Color


def generar_reporte_pdf_con_data_bd(data):
    buffer = io.BytesIO()  # Crear un buffer en memoria

    # Crear el PDF
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    c.setTitle(" Reporte cálculo de flete")

    # Obtener las dimensiones de la página
    width, height = landscape(A4)

    # primera linea
    c.setFont("Helvetica", 10)
    current_y = height - 40
    c.drawString(40, current_y, f"{data['empresa']}")

    current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.setFont("Helvetica", 7)
    c.drawString(width - 130, current_y, f"{data['fecha_de_creacion']}")

    # segunda linea
    c.setFont("Helvetica-Bold", 10)
    texto = f"{data['producto']}"
    text_width = c.stringWidth(texto, "Helvetica", 12)
    # Calcular la posición X para centrar el texto
    x_position = (width - text_width) / 2 + 20
    # Dibujar el texto centrado
    current_y -= 20
    c.drawString(x_position, current_y, texto)

    # tercera linea
    current_y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, current_y, f"CARTA PORTE: {data['carta_porte']}")

    # CUARTA LINEA DATOS DEL DESPACHO
    ordenes_recojo = data['ordenes_despacho']
    ordenes_string = " / ".join([f"{row['orden_compra']['numero_oc']}({row['numero_recojo']})" for row in ordenes_recojo])
    textos = [
        f"N° DUA: {data['dua']}",
        f"Fec. Num.: {data['fecha_numeracion']}",
        f"Factura N°: {data['num_factura']}",
        f"OC: {ordenes_string}",
        f"CANT. {data['total_sacos_cargados']} sacos",
        f" {data['peso_neto_crt']} kg"
    ]
    # Fuente y tamaño
    font_name = "Helvetica"
    font_size = 8
    c.setFont(font_name, font_size)
    # Espacio entre columnas
    margin = 30
    # Posición inicial en Y (mantener fija)
    current_y -= 20
    y_position = current_y
    # Posición inicial en X
    x_position = 40
    # Dibujar todos los textos en una línea tomando en cuenta su tamaño para darle cierto espaciado
    for texto in textos:
        # Calcular el ancho de cada texto
        text_width = c.stringWidth(texto, font_name, font_size)

        # Dibujar el texto
        c.drawString(x_position, y_position, texto)

        # Actualizar la posición X para el siguiente texto
        x_position += text_width + margin

        # Si el texto excede el tamaño de la página en el eje X, detener la creación del contenido
        if x_position > width:
            break

    # QUINTA LINEA DONDE INICIA LA TABLA:
    current_y -= 20
    # Datos iniciales de la tabla #1 (Titulos y subtitulos)
    data_table = [
        # Línea de títulos
        ['FEC. INGRE.', 'EMPRESA DE TRANSP.', 'CARGA', '', '', '', 'DESCARGA', '', '', '', 'DESCUENTOS', '', '', '',
         ''],
        ['', '', 'N°', 'Placa S.', 'Sacos C.', 'Peso S.', 'Placa L.', 'Sacos D.', 'Peso L.', 'Merma', 'S. Falt.',
         'S. Rotos', 'S. Humed.', 'S. Mojad.', 'Estibaje'],
    ]
    styles = getSampleStyleSheet()
    parrafo = Paragraph(f"<para align=center spaceb=3><b>{data['transportista'].get('nombre_transportista')}</b></para>",
                        styles["BodyText"])
    for i, row in enumerate(data['detalle_despacho']):
        if i == 0:  # Primera fila (datos especiales)
            data_table.append([
                f"{data['fecha_numeracion']}",
                parrafo,
                str(i),
                row['placa_salida'],
                str(row['sacos_cargados']),
                str(row['peso_salida']),
                row['placa_llegada'],
                str(row['sacos_descargados']),
                str(row['peso_llegada']),
                str(row['merma']),
                str(row['sacos_faltantes']),
                str(row['sacos_rotos']),
                str(row['sacos_humedos']),
                str(row['sacos_mojados']),
                str(row['pago_estiba']),
            ])
        else:  # Para el resto de las filas
            data_table.append([
                "",  # Cadena vacía
                "",  # Cadena vacía
                str(i),
                row['placa_salida'],
                str(row['sacos_cargados']),
                str(row['peso_salida']),
                row['placa_llegada'],
                str(row['sacos_descargados']),
                str(row['peso_llegada']),
                str(row['merma']),
                str(row['sacos_faltantes']),
                str(row['sacos_rotos']),
                str(row['sacos_humedos']),
                str(row['sacos_mojados']),
                str(row['pago_estiba']),
            ])
    # Agregamos fila de totales
    data_table.append(
        ['', f"Flete x TM: $ {data['flete_pactado']:.2f}", f"{''}", 'TOTAL',
         f"{data['total_sacos_cargados']}", f"{data['suma_peso_salida_kg']}", 'TOTAL',
         f"{data['total_sacos_descargados']}", f"{data['suma_peso_llegada_kg']}",
         f"{data['merma_total']}", f"{data['total_sacos_faltantes']}",
         f"{data['total_sacos_rotos']}", f"{data['total_sacos_humedos']}",
         f"{data['total_sacos_mojados']}"])
    # Ancho de columnas
    col_widths = [60, 110, 20, 60, 40, 60, 60, 60, 40, 60, 30, 30, 30, 30, 70]
    # Crear la tabla
    table = Table(data_table, colWidths=col_widths, rowHeights=15)
    color_rosa = Color(red=250 / 255, green=210 / 255, blue=202 / 255)
    color_celeste = Color(red=176 / 255, green=225 / 255, blue=250 / 255)
    numero_filas = len(data_table)
    # Estilos para la tabla
    table_style = TableStyle([
        ('SPAN', (0, 0), (0, 1)),  # Fusionar "FEC. INGRE."
        ('SPAN', (1, 0), (1, 1)),  # Fusionar "EMPRESA DE TRANSP."
        ('SPAN', (2, 0), (5, 0)),  # Fusionar "CARGA"
        ('SPAN', (6, 0), (9, 0)),  # Fusionar "DESCARGA"
        ('SPAN', (10, 0), (14, 0)),  # Fusionar "DESCUENTOS"
        ('SPAN', (0, 2), (0, numero_filas - 1)),  # Fusionar "fecha"
        ('SPAN', (1, 2), (1, numero_filas - 2)),  # Fusionar "nombre empresa transporte"
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centrar todo
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centrar verticalmente
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Añadir cuadrícula
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Fondo gris para los títulos
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),  # Fondo gris claro para subtítulos
        ('BACKGROUND', (2, 0), (5, numero_filas), colors.yellowgreen),  # Color "CARGA"
        ('BACKGROUND', (6, 0), (9, numero_filas), color_celeste),  # Color "DESCARGA"
        ('BACKGROUND', (10, 0), (14, numero_filas), color_rosa),  # Fusionar "DESCUENTOS"
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Negrita en títulos
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),  # Negrita en subtítulos
        # ('FONTSIZE', (15, 0), (15, numero_filas - 1), 5),
    ])
    # Aplicar estilos a la tabla
    table.setStyle(table_style)
    # Calcular la altura total de la tabla
    table_height = len(data_table) * 15  # 20 es la altura de cada fila
    # Calcular la posición de la tabla en la página
    table.wrapOn(c, width, height)
    table.drawOn(c, 40, current_y - table_height)  # Ajustar la posición dependiendo de la cantidad de filas

    current_y = current_y - table_height - 20

    # Data para la tabla #2 (Detalles de pesos)
    second_data_table = [
        ["Faltante peso Sta. Cruz - Desaguadero:", f"{data['diferencia_de_peso']:.2f} Kg."],
        ["Merma permitida:", f"{data['configuracion_despacho'][0]['merma_permitida']:.2f} Kg."],  #POSIBLE ERROR
        ["Desc. diferencia de peso:", f"{data['diferencia_peso_por_cobrar']:.2f} Kg."],
        ["Desc. sacos falantes:", f"{data['descuento_peso_sacos_faltantes']:.2f} Kg."]
    ]
    second_col_widths = [110, 50]
    second_table = Table(second_data_table, colWidths=second_col_widths, rowHeights=14)
    second_table_style = TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Centrar
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centrar verticalmente
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Añadir cuadrícula
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Alinear la segunda columna a la derecha
    ])
    second_table.setStyle(second_table_style)
    second_table_height = len(second_data_table) * 14
    second_table.wrapOn(c, width, height)
    second_table.drawOn(c, 40, current_y - second_table_height)

    # Data para la tabla #3 (Resumen de descuentos)
    third_data_table = [
        ["FLETE", f"$ {data["flete_base"]:.2f}"],
        ["Dscto. por dif. de peso", f"$ {data["descuento_por_diferencia_peso"]:.2f}"],
        ["Dscto. por sacos faltantes", f"$ {data["descuento_sacos_faltantes"]:.2f}"],
        ["Dscto. por sacos rotos", f"$ {data["descuento_sacos_rotos"]:.2f}"],
        ["Dscto. por sacos humedos", f"$ {data["descuento_sacos_humedos"]:.2f}"],
        ["Dscto. por sacos mojados", f"$ {data["descuento_sacos_mojados"]:.2f}"],
        ["FLETE TOTAL", f"$ {data["total_luego_dsctos_sacos"]:.2f}"],
    ]
    # posicion en x para la tercera tabla:
    x_position_for_third_table = 260
    third_col_widths = [110, 40]
    third_table = Table(third_data_table, colWidths=third_col_widths, rowHeights=14)
    third_table_style = TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 6),  # Tamaño de fuente
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alinear toda la tabla a la izquierda
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centrar verticalmente
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Añadir cuadrícula
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Alinear la segunda columna a la derecha
    ])
    third_table.setStyle(third_table_style)
    third_table_height = len(third_data_table) * 14
    third_table.wrapOn(c, width, height)
    third_table.drawOn(c, x_position_for_third_table, current_y - third_table_height)

    # PARA VALIDACION DEL VALOR CRT
    peso_total_toneladas = data['peso_neto_crt'] / 1000
    flete_pactado = data["flete_pactado"]
    monto_flete = round((peso_total_toneladas * flete_pactado), 2)
    flete_base = data["flete_base"]
    estado_crt = ""
    if (flete_base <= monto_flete):
        estado_crt = "NO SOBREPASA VALOR CRT"
    else:
        estado_crt = "SOBREPASA VALOR CRT"
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x_position_for_third_table + 150 + 10, current_y - 8, estado_crt)

    # Primera LLave para descuento sacos RMH
    c.setLineWidth(0.5)
    first_x_position_for_key = x_position_for_third_table + 150 + 10
    first_key_y_position = current_y - (14 * 3)
    last_key_y_position = first_key_y_position - (14 * 3)
    middle_of_key = (first_key_y_position + last_key_y_position) / 2
    inclinacion = 2
    c.line(first_x_position_for_key, first_key_y_position - inclinacion, first_x_position_for_key,
           last_key_y_position + inclinacion)
    c.line(first_x_position_for_key, first_key_y_position - inclinacion, first_x_position_for_key - inclinacion,
           first_key_y_position)
    c.line(first_x_position_for_key - inclinacion, last_key_y_position, first_x_position_for_key,
           last_key_y_position + inclinacion)
    c.line(first_x_position_for_key, middle_of_key, first_x_position_for_key + inclinacion, middle_of_key)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(first_x_position_for_key + inclinacion + 4, middle_of_key,
                 f"$ {data['total_descuento_solo_sacos']:.2f}")

    # Segunda llave para descuento de sacos RMH
    c.setLineWidth(0.5)

    # Coordenadas para dibujar segunda la llave
    key_start_x = first_x_position_for_key + inclinacion + 4 + 40
    key_start_y = current_y - 14
    key_end_y = key_start_y - (14 * 5)
    key_middle_y = (key_start_y + key_end_y) / 2
    key_inclination = 2

    # Dibujar la llave
    c.line(key_start_x, key_start_y - key_inclination, key_start_x, key_end_y + key_inclination)
    c.line(key_start_x, key_start_y - key_inclination, key_start_x - key_inclination, key_start_y)
    c.line(key_start_x - key_inclination, key_end_y, key_start_x, key_end_y + key_inclination)
    c.line(key_start_x, key_middle_y, key_start_x + key_inclination, key_middle_y)

    # Texto del descuento
    c.setFont("Helvetica-Bold", 7)
    c.drawString(key_start_x + key_inclination + 4, key_middle_y,
                 f"$ {data['aux_descuento']:.2f}")

    # Lista de placas y estado de estiba:
    y_position_for_list = current_y - third_table_height - 10
    c.setFont("Helvetica", 6)
    for item in data["pago_estiba_list"]:
        # Crear texto en una línea
        c.drawString(x_position_for_third_table, y_position_for_list,
                     f"{item['placa']} {item['detalle']}")  # Placa y detalle
        c.drawString(x_position_for_third_table + 130, y_position_for_list,
                     f"$ {item['monto_descuento']:.2f}")  # Monto alineado a la derecha
        y_position_for_list -= 10  # Reducir la posición vertical para la próxima línea

    for item in data["otros_gastos"]:
        c.drawString(x_position_for_third_table, y_position_for_list, f"{item['descripcion']}")
        c.drawString(x_position_for_third_table + 130, y_position_for_list, f"$ {item['monto']:.2f}")
        y_position_for_list -= 10

    # Coordenadas para dibujar la tercera llave
    tirth_key_start_x = first_x_position_for_key
    tirth_key_start_y = current_y - third_table_height - 5
    tirth_key_end_y = y_position_for_list + 10
    tirth_key_middle_y = (tirth_key_start_y + tirth_key_end_y) / 2
    tirth_key_inclination = 2
    # Dibujar la tercera llave
    c.line(tirth_key_start_x, tirth_key_start_y - tirth_key_inclination, tirth_key_start_x,
           tirth_key_end_y + tirth_key_inclination)
    c.line(tirth_key_start_x, tirth_key_start_y - tirth_key_inclination, tirth_key_start_x - tirth_key_inclination,
           tirth_key_start_y)
    c.line(tirth_key_start_x - tirth_key_inclination, tirth_key_end_y, tirth_key_start_x,
           tirth_key_end_y + tirth_key_inclination)
    c.line(tirth_key_start_x, tirth_key_middle_y, tirth_key_start_x + tirth_key_inclination, tirth_key_middle_y)
    # Texto del descuento
    total_decuento = data['total_descuento_estiba'] + data['total_otros_gastos']
    c.setFont("Helvetica-Bold", 7)
    c.drawString(tirth_key_start_x + tirth_key_inclination + 4, tirth_key_middle_y - 2,
                 f"$ {total_decuento:.2f}")

    # Escribir linea de neto a pagar
    table_total_data = [
        ["TOTAL A PAGAR:", f"${data['total_a_pagar']:.2f}"]
    ]
    # Crear la tabla
    table_total = Table(table_total_data, colWidths=[110, 40])  # Anchos de columnas
    # Aplicar estilo a la tabla
    table_total.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.orange),  # Fondo naranja
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),  # Texto en color negro
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alineación izquierda primera columna
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),  # Fuente en negrita
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # Tamaño de la fuente
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Alineación derecha segunda columna
    ]))
    altura_tabla_total = len(table_total_data) * 14
    table_total.wrapOn(c, width, height)
    table_total.drawOn(c, x_position_for_third_table, y_position_for_list - altura_tabla_total - 20)

    # Data para la tabla #4 (resumen de descuentos)
    new_x_position = 260 + 150 + 150
    fourth_data_table = [
        ["FLETE", f"$ {data["flete_base"]:.2f}"],
        ["Dscto.", f"$ {data["total_dsct"]:.2f}"],
        ["Neto.", f"$ {data["total_a_pagar"]:.2f}"],
    ]
    fourth_col_widths = [30, 50]
    fourth_table = Table(fourth_data_table, colWidths=fourth_col_widths, rowHeights=14)
    fourth_table_style = TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 6),  # Tamaño de fuente
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alinear toda la tabla a la izquierda
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centrar verticalmente
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Añadir cuadrícula
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Alinear la segunda columna a la derecha
    ])
    fourth_table.setStyle(fourth_table_style)
    fourth_table_height = len(fourth_data_table) * 14
    fourth_table.wrapOn(c, width, height)
    fourth_table.drawOn(c, new_x_position, current_y - fourth_table_height - (14 * 3))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(new_x_position, current_y - fourth_table_height + 5, "RESUMEN")

    # Data para la tabla #5 (determinacion de costos)
    second_new_x_position = new_x_position + 120
    c.setFont("Helvetica-Bold", 6)
    c.drawString(second_new_x_position, current_y + 5, "Determinacion de costo x Kg.")
    fifth_data_table = [
        ["C.P", f"{data["precio_por_tonelada"]:.2f}"],
        ["F.B", f"$ {data["flete_pactado"]:.2f}"],
        ["G.N", f"{data["configuracion_despacho"][0]["gastos_nacionalizacion"]}"],
        ["MF CIA", f"{data["configuracion_despacho"][0]["margen_financiero"]}"],
        ["IGV 18%", f"{data["igv"]}"],#AQUI ME QUEDE
        ["PRECIO DES", f"{data["precio_bruto_final"]}"],
        ["COSTO TM", f"{data["precio_por_tonelada_final"]}"],
        ["COSTO Kg", f"{data["precio_por_kg_final"]}"],
    ]
    fifth_col_widths = [50, 40]
    fifth_table = Table(fifth_data_table, colWidths=fifth_col_widths, rowHeights=14)
    fifth_table_style = TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 6),  # Tamaño de fuente
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alinear toda la tabla a la izquierda
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centrar verticalmente
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Añadir cuadrícula
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Alinear la segunda columna a la derecha
    ])
    fifth_table.setStyle(fifth_table_style)
    fifth_table_height = len(fifth_data_table) * 14
    fifth_table.wrapOn(c, width, height)
    fifth_table.drawOn(c, second_new_x_position, current_y - fifth_table_height)

    # SALTO DE LINEA PARA ESPACIO DE DESCUENTOS
    current_y = current_y - second_table_height - 20

    x_start = 40  # Eje X constante
    line_height = 10  # Interlineado
    # Escribir título
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_start, current_y, "Descuentos:")
    current_y -= line_height + 5  # Reducir Y para el siguiente contenido
    # Cambiar la fuente para los detalles
    c.setFont("Helvetica", 7)
    # Condicionales y datos
    if data["descuento_por_diferencia_peso"] > 0:
        c.drawString(
            x_start,
            current_y,
            f"B/V 004-:        dscto. x dif. peso $ {data['descuento_por_diferencia_peso']:.2f}"
        )
        current_y -= line_height

    if data["descuento_sacos_faltantes"] > 0:
        c.drawString(
            x_start,
            current_y,
            f"B/V 004-:        dscto. x sacos falt. $ {data['descuento_sacos_faltantes']:.2f}"
        )
        current_y -= line_height

    if data["total_descuento_solo_sacos"] > 0:
        c.drawString(
            x_start,
            current_y,
            f"B/V 004-:        dscto. x sacos R,H,M. $ {data['total_descuento_solo_sacos']:.2f}"
        )
        current_y -= line_height

    if data["total_descuento_estiba"] > 0:
        c.drawString(
            x_start,
            current_y,
            f"B/V 004-:        dscto. x estibaje $ {data['total_descuento_estiba']:.2f}"
        )
        current_y -= line_height

    # Total
    c.setFont("Helvetica-Bold", 8)
    c.drawString(
        x_start,
        current_y - 5,
        f"TOTAL A DESCONTAR:   $ {data['total_dsct_sin_gastos_otros']:.2f}"
    )

    # Guardar el PDF en el buffer
    c.showPage()
    c.save()

    buffer.seek(0)  # Volver al inicio del buffer
    return buffer.getvalue()  # Devolver el PDF en binario